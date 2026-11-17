/*
 * LotusKey (ibus-LotusKey) - Native IBus Engine
 * Author: Victor Pham
 * High-performance Vietnamese Input Method Engine for Linux (Wayland & X11)
 * Powered by pure C-ABI Bridge (LotusKey Core)
 */

#include <ibus.h>
#include <gio/gio.h>
#include <glib-unix.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <limits.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/prctl.h>
#include <time.h>
#include <stdarg.h>
#include <signal.h>
#include "lotuskey.h"
#include "lotus_charset.h"

#define IBUS_TYPE_LOTUS_ENGINE (ibus_lotus_engine_get_type())
#ifndef IBUS_ATTR_UNDERLINE_NONE
#define IBUS_ATTR_UNDERLINE_NONE 0
#endif

enum {
    TOGGLE_BOTH = 0,        /* Ctrl+Shift AND Alt+Z */
    TOGGLE_CTRL_SHIFT = 1,   /* Ctrl+Shift only */
    TOGGLE_ALT_Z = 2,        /* Alt+Z only */
    TOGGLE_SHIFT_SPACE = 3,  /* Shift+Space */
    TOGGLE_NONE = 4          /* No shortcut */
};

enum {
    IM_TELEX = 0,
    IM_VNI = 1,
    IM_TELEX_VNI = 2
};

typedef struct _IBusLotusEngine IBusLotusEngine;
typedef struct _IBusLotusEngineClass IBusLotusEngineClass;

struct _IBusLotusEngine {
    IBusEngine parent;
    gpointer _abi_guard[4];
    lotuskey_session_t session;
    gboolean enabled;
    gboolean is_vni;
    gint input_method;      /* 0: Telex, 1: VNI, 2: Telex+VNI */
    gboolean smart_bilingual;
    gboolean sen_flex;
    gboolean modern_orthography;
    gboolean quick_telex;
    gboolean relaxed_coda;
    gboolean preedit_underline;
    gboolean is_password_field;
    gboolean replayed_after_backspace;
    gboolean grave_menu_enabled;
    gboolean w2u;
    gboolean bracket_transform;
    gboolean macro_enabled;
    gboolean macro_in_off_mode;
    gboolean auto_capitalize_macro;
    gboolean per_app_remember;
    gboolean auto_disable_url_bar;
    gboolean compact_mode;
    gboolean autostart;
    gchar *output_mode;
    gchar *im_framework;
    gchar *ui_lang;
    gchar *icon_style;      /* "flag", "badge", "lotus", "symbolic" */
    gchar *flag_variant;    /* "us", "uk" */
    gchar *restore_key;     /* "esc", "shift_backspace", "none" */
    gchar *theme;           /* "auto", "dark", "light" */
    gint charset;
    gint toggle_mode;
    guint client_caps;
    gchar prev_surrounding[512];
    gchar raw_typed[512];
    size_t raw_typed_len;
    gchar last_bracket_key;
    gboolean ctrl_pressed;
    gboolean shift_pressed;
    gboolean other_key_in_chord;
    guint grave_timer_id;
    time_t config_mtime;
    IBusPropList *prop_list;
    IBusProperty *status_prop;
};

struct _IBusLotusEngineClass {
    IBusEngineClass parent_class;
    gpointer padding[8];
};

GType ibus_lotus_engine_get_type(void);
G_DEFINE_TYPE(IBusLotusEngine, ibus_lotus_engine, IBUS_TYPE_ENGINE)

static GList *active_engines = NULL;
static GFileMonitor *g_config_monitor = NULL;
static GFileMonitor *g_macro_monitor = NULL;
static LotusMacroTable g_macro_table = { .count = 0 };
static guint32 g_notify_replace_id = 0;

static void ibus_lotus_load_user_config(IBusLotusEngine *vl_engine);
static void ibus_lotus_build_prop_list(IBusLotusEngine *vl_engine);
static void ibus_lotus_spawn_tool(const char *tool_name);
static void ibus_lotus_spawn_tool_arg(const char *tool_name, const char *arg1);
static void ibus_lotus_sni_notify_update(void);

static void ibus_lotus_append_raw_typed(IBusLotusEngine *vl_engine, char c) {
    if (c != 0 && vl_engine->raw_typed_len + 1 < sizeof(vl_engine->raw_typed)) {
        vl_engine->raw_typed[vl_engine->raw_typed_len++] = c;
        vl_engine->raw_typed[vl_engine->raw_typed_len] = '\0';
    }
}

static void ibus_lotus_pop_raw_typed(IBusLotusEngine *vl_engine) {
    if (vl_engine->raw_typed_len > 0) {
        vl_engine->raw_typed[--vl_engine->raw_typed_len] = '\0';
    }
}

static gchar *ibus_lotus_get_config_dir(void) {
    const gchar *cfg_root = g_get_user_config_dir();
    if (!cfg_root) {
        return NULL;
    }
    return g_build_filename(cfg_root, "LotusKey", NULL);
}

static void ibus_lotus_reload_macros(void) {
    gchar *dir_path = ibus_lotus_get_config_dir();
    if (!dir_path) return;
    gchar *macro_path = g_build_filename(dir_path, "macros.conf", NULL);
    lotus_macro_table_load(&g_macro_table, macro_path);
    g_free(macro_path);
    g_free(dir_path);
}

static void ibus_lotus_reload_all_engines(void) {
    ibus_lotus_reload_macros();
    for (GList *l = active_engines; l != NULL; l = l->next) {
        IBusLotusEngine *vl = (IBusLotusEngine *)l->data;
        ibus_lotus_load_user_config(vl);
        ibus_lotus_build_prop_list(vl);
        ibus_engine_register_properties((IBusEngine *)vl, vl->prop_list);
        if (vl->status_prop) {
            ibus_engine_update_property((IBusEngine *)vl, vl->status_prop);
        }
    }
    ibus_lotus_sni_notify_update();
}

static gboolean on_sigusr1_unix_signal(gpointer user_data) {
    (void)user_data;
    ibus_lotus_reload_all_engines();
    return G_SOURCE_CONTINUE;
}

static void on_config_file_changed(GFileMonitor *monitor, GFile *file, GFile *other_file,
                                   GFileMonitorEvent event_type, gpointer user_data) {
    (void)monitor;
    (void)file;
    (void)other_file;
    (void)user_data;
    if (event_type == G_FILE_MONITOR_EVENT_CHANGED ||
        event_type == G_FILE_MONITOR_EVENT_CREATED ||
        event_type == G_FILE_MONITOR_EVENT_CHANGES_DONE_HINT) {
        ibus_lotus_reload_all_engines();
    }
}

static void ibus_lotus_send_notification(const char *summary, const char *body, const char *icon) {
    GDBusConnection *conn = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, NULL);
    if (!conn) return;

    GVariantBuilder actions_builder;
    g_variant_builder_init(&actions_builder, G_VARIANT_TYPE("as"));

    GVariantBuilder hints_builder;
    g_variant_builder_init(&hints_builder, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&hints_builder, "{sv}",
                          "x-canonical-private-synchronous",
                          g_variant_new_string("lotus-toggle"));

    g_dbus_connection_call(
        conn,
        "org.freedesktop.Notifications",
        "/org/freedesktop/Notifications",
        "org.freedesktop.Notifications",
        "Notify",
        g_variant_new("(susssasa{sv}i)",
                      "LotusKey",
                      g_notify_replace_id,
                      icon ? icon : "",
                      summary ? summary : "LotusKey",
                      body ? body : "",
                      &actions_builder,
                      &hints_builder,
                      1200),
        G_VARIANT_TYPE("(u)"),
        G_DBUS_CALL_FLAGS_NONE,
        500,
        NULL,
        NULL,
        NULL
    );
    g_object_unref(conn);
}

static void ibus_lotus_clear_preedit(IBusEngine *engine) {
    IBusText *empty = ibus_text_new_from_static_string("");
    ibus_engine_update_preedit_text_with_mode(
        engine,
        empty,
        0,
        FALSE,
        IBUS_ENGINE_PREEDIT_CLEAR
    );
    ibus_engine_hide_preedit_text(engine);
}

static void ibus_lotus_cancel_grave_timer(IBusLotusEngine *vl_engine) {
    if (vl_engine->grave_timer_id != 0) {
        g_source_remove(vl_engine->grave_timer_id);
        vl_engine->grave_timer_id = 0;
    }
}

static void ibus_lotus_engine_reset_internal(IBusLotusEngine *vl_engine) {
    vl_engine->replayed_after_backspace = FALSE;
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    vl_engine->last_bracket_key = 0;
    vl_engine->prev_surrounding[0] = '\0';
    vl_engine->raw_typed[0] = '\0';
    vl_engine->raw_typed_len = 0;
    ibus_lotus_cancel_grave_timer(vl_engine);
    if (vl_engine->session) {
        lotuskey_reset_session(vl_engine->session);
    }
    ibus_lotus_clear_preedit((IBusEngine *)vl_engine);
}

static gboolean ibus_lotus_use_preedit_mode(IBusLotusEngine *vl_engine) {
    if (!vl_engine->output_mode || g_strcmp0(vl_engine->output_mode, "preedit") == 0) {
        return TRUE;
    }
    if (g_strcmp0(vl_engine->output_mode, "surrounding") == 0) {
        if (!(vl_engine->client_caps & IBUS_CAP_SURROUNDING_TEXT)) {
            return TRUE; /* Auto-fallback to preedit for Electron/Chromium */
        }
        return FALSE;
    }
    return FALSE;
}

static size_t ibus_lotus_utf8_char_len(unsigned char b) {
    if ((b & 0x80) == 0) return 1;
    if ((b & 0xE0) == 0xC0) return 2;
    if ((b & 0xF0) == 0xE0) return 3;
    if ((b & 0xF8) == 0xF0) return 4;
    return 1;
}

static size_t ibus_lotus_utf8_codepoint_count(const char *utf8_str) {
    if (!utf8_str) return 0;
    size_t count = 0;
    for (const unsigned char *p = (const unsigned char *)utf8_str; *p; p++) {
        if ((*p & 0xC0) != 0x80) {
            count++;
        }
    }
    return count;
}

static void ibus_lotus_sync_direct_output(IBusLotusEngine *vl_engine, const char *target_utf8) {
    IBusEngine *engine = (IBusEngine *)vl_engine;
    char converted[1024];
    lotus_convert_charset(target_utf8 ? target_utf8 : "", vl_engine->charset, converted, sizeof(converted));

    const char *prev = vl_engine->prev_surrounding;
    size_t common_bytes = 0;
    while (prev[common_bytes] != '\0' && converted[common_bytes] != '\0' &&
           prev[common_bytes] == converted[common_bytes]) {
        common_bytes++;
    }
    /* Align common_bytes back to UTF-8 codepoint boundary */
    while (common_bytes > 0 && ((unsigned char)converted[common_bytes] & 0xC0) == 0x80) {
        common_bytes--;
    }

    size_t del_chars = ibus_lotus_utf8_codepoint_count(prev + common_bytes);
    const char *append_str = converted + common_bytes;

    if (g_strcmp0(vl_engine->output_mode, "forward") == 0) {
        for (size_t i = 0; i < del_chars; i++) {
            ibus_engine_forward_key_event(engine, IBUS_KEY_BackSpace, 14, 0);
            ibus_engine_forward_key_event(engine, IBUS_KEY_BackSpace, 14, IBUS_RELEASE_MASK);
        }
    } else if (del_chars > 0) {
        ibus_engine_delete_surrounding_text(engine, -(gint)del_chars, (guint)del_chars);
    }

    if (append_str[0] != '\0') {
        IBusText *commit_text = ibus_text_new_from_string(append_str);
        ibus_engine_commit_text(engine, commit_text);
    }

    snprintf(vl_engine->prev_surrounding, sizeof(vl_engine->prev_surrounding), "%s", converted);
}

static void ibus_lotus_commit_composing(IBusLotusEngine *vl_engine, const char *trailing_ascii) {
    IBusEngine *engine = (IBusEngine *)vl_engine;
    char word_utf8[1024];
    word_utf8[0] = '\0';

    if (vl_engine->session && lotuskey_is_composing(vl_engine->session)) {
        const char *raw_before = (vl_engine->raw_typed_len > 0)
            ? vl_engine->raw_typed
            : lotuskey_get_raw_text(vl_engine->session);
        char raw_copy[512];
        snprintf(raw_copy, sizeof(raw_copy), "%s", raw_before ? raw_before : "");

        if (trailing_ascii && trailing_ascii[0] != '\0' && trailing_ascii[1] == '\0') {
            uint32_t cp = (uint32_t)(unsigned char)trailing_ascii[0];
            lotuskey_feed_char(vl_engine->session, cp);
        } else {
            lotuskey_commit_word(vl_engine->session);
        }
        const char *committed = lotuskey_get_last_text(vl_engine->session);
        if (committed && committed[0] != '\0') {
            snprintf(word_utf8, sizeof(word_utf8), "%s", committed);
        }

        /* Check Macro Table expansion (Gõ tắt) */
        if (vl_engine->macro_enabled && g_macro_table.count > 0) {
            char expanded[512];
            int auto_cap = vl_engine->auto_capitalize_macro ? 1 : 0;
            if (lotus_macro_lookup_ex(&g_macro_table, word_utf8, auto_cap, expanded, sizeof(expanded)) ||
                (raw_copy[0] != '\0' && lotus_macro_lookup_ex(&g_macro_table, raw_copy, auto_cap, expanded, sizeof(expanded)))) {
                snprintf(word_utf8, sizeof(word_utf8), "%s", expanded);
            }
        }
    }

    if (!ibus_lotus_use_preedit_mode(vl_engine)) {
        /* In direct mode (surrounding / forward), sync any final changes + trailing_ascii */
        char final_full[1024];
        snprintf(final_full, sizeof(final_full), "%s%s",
                 word_utf8,
                 (trailing_ascii && trailing_ascii[0] != '\0') ? trailing_ascii : "");
        if (final_full[0] != '\0') {
            ibus_lotus_sync_direct_output(vl_engine, final_full);
        }
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }

    char converted[1024];
    lotus_convert_charset(word_utf8, vl_engine->charset, converted, sizeof(converted));

    if (trailing_ascii && trailing_ascii[0] != '\0') {
        size_t len = strlen(converted);
        if (len < sizeof(converted) - 1) {
            snprintf(converted + len, sizeof(converted) - len, "%s", trailing_ascii);
        }
    }

    if (converted[0] != '\0') {
        IBusText *commit_text = ibus_text_new_from_string(converted);
        ibus_engine_commit_text(engine, commit_text);
    }

    ibus_lotus_engine_reset_internal(vl_engine);
}

static void ibus_lotus_update_preedit(IBusLotusEngine *vl_engine) {
    IBusEngine *engine = (IBusEngine *)vl_engine;
    if (vl_engine->session && lotuskey_is_composing(vl_engine->session)) {
        const char *composing = lotuskey_get_composing_text(vl_engine->session);
        if (composing && composing[0] != '\0') {
            if (!ibus_lotus_use_preedit_mode(vl_engine)) {
                ibus_lotus_sync_direct_output(vl_engine, composing);
                return;
            }
            char converted[1024];
            /* For preedit display, keep readable UTF-8 if TCVN3/VNI-Win, or convert if Combining */
            if (vl_engine->charset == LOTUS_CHARSET_COMBINING_CFG || vl_engine->charset == LOTUS_CHARSET_COMBINING_ENUM) {
                lotus_convert_charset(composing, vl_engine->charset, converted, sizeof(converted));
            } else {
                snprintf(converted, sizeof(converted), "%s", composing);
            }
            IBusText *text = ibus_text_new_from_string(converted);
            guint char_len = ibus_text_get_length(text);
            guint ul_mode = vl_engine->preedit_underline ? IBUS_ATTR_UNDERLINE_SINGLE : IBUS_ATTR_UNDERLINE_NONE;
            ibus_text_append_attribute(text, IBUS_ATTR_TYPE_UNDERLINE, ul_mode, 0, (gint)char_len);
            ibus_engine_update_preedit_text_with_mode(
                engine,
                text,
                char_len,
                TRUE,
                IBUS_ENGINE_PREEDIT_COMMIT
            );
            return;
        }
    }
    if (!ibus_lotus_use_preedit_mode(vl_engine) && vl_engine->prev_surrounding[0] != '\0') {
        ibus_lotus_sync_direct_output(vl_engine, "");
    }
    ibus_lotus_clear_preedit(engine);
}

static void ibus_lotus_load_user_config(IBusLotusEngine *vl_engine) {
    if (!vl_engine->session) {
        return;
    }
    gchar *dir_path = ibus_lotus_get_config_dir();
    if (!dir_path) {
        return;
    }
    gchar *path = g_build_filename(dir_path, "config.env", NULL);
    g_free(dir_path);

    struct stat st;
    if (stat(path, &st) == 0) {
        vl_engine->config_mtime = st.st_mtime;
    }

    FILE *fp = fopen(path, "r");
    g_free(path);
    if (!fp) {
        return;
    }

    char line[256];
    gboolean has_input_method_override = FALSE;
    gint config_im = IM_TELEX;

    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "ENABLED=", 8) == 0) {
            vl_engine->enabled = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "INPUT_METHOD=", 13) == 0) {
            has_input_method_override = TRUE;
            if (strstr(line, "telex_vni") != NULL || strstr(line, "TELEX_VNI") != NULL) {
                config_im = IM_TELEX_VNI;
            } else if (strstr(line, "vni") != NULL || strstr(line, "VNI") != NULL) {
                config_im = IM_VNI;
            } else {
                config_im = IM_TELEX;
            }
        } else if (strncmp(line, "GRAMMAR_PROFILE=", 16) == 0) {
            vl_engine->sen_flex = (strstr(line, "classic") == NULL);
        } else if (strncmp(line, "SMART_BILINGUAL=", 16) == 0) {
            vl_engine->smart_bilingual = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "MODERN_ORTHOGRAPHY=", 19) == 0) {
            vl_engine->modern_orthography = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "QUICK_TELEX=", 12) == 0) {
            vl_engine->quick_telex = (strstr(line, "true") != NULL || strstr(line, "1") != NULL);
        } else if (strncmp(line, "PREEDIT_UNDERLINE=", 18) == 0) {
            vl_engine->preedit_underline = (strstr(line, "true") != NULL || strstr(line, "1") != NULL);
        } else if (strncmp(line, "MODE_MENU_KEY=", 14) == 0) {
            vl_engine->grave_menu_enabled = (strstr(line, "grave") != NULL);
        } else if (strncmp(line, "TOGGLE_KEY=", 11) == 0) {
            if (strstr(line, "Both") || strstr(line, "both")) {
                vl_engine->toggle_mode = TOGGLE_BOTH;
            } else if (strstr(line, "Shift") && (strstr(line, "Control") || strstr(line, "Ctrl"))) {
                vl_engine->toggle_mode = TOGGLE_CTRL_SHIFT;
            } else if (strstr(line, "Alt") || strstr(line, "alt")) {
                vl_engine->toggle_mode = TOGGLE_ALT_Z;
            } else if (strstr(line, "Space") || strstr(line, "space")) {
                vl_engine->toggle_mode = TOGGLE_SHIFT_SPACE;
            } else if (strstr(line, "None") || strstr(line, "none")) {
                vl_engine->toggle_mode = TOGGLE_NONE;
            } else {
                vl_engine->toggle_mode = TOGGLE_BOTH;
            }
        } else if (strncmp(line, "W2U=", 4) == 0) {
            vl_engine->w2u = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "BRACKET_TRANSFORM=", 18) == 0) {
            vl_engine->bracket_transform = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "MACRO_ENABLED=", 14) == 0) {
            vl_engine->macro_enabled = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "MACRO_IN_OFF_MODE=", 18) == 0) {
            vl_engine->macro_in_off_mode = (strstr(line, "true") != NULL || strstr(line, "1") != NULL);
        } else if (strncmp(line, "AUTO_CAPITALIZE_MACRO=", 22) == 0) {
            vl_engine->auto_capitalize_macro = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "PER_APP_REMEMBER=", 17) == 0) {
            vl_engine->per_app_remember = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "AUTO_DISABLE_URL_BAR=", 21) == 0) {
            vl_engine->auto_disable_url_bar = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "COMPACT_MODE=", 13) == 0) {
            vl_engine->compact_mode = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "OUTPUT_MODE=", 12) == 0) {
            if (vl_engine->output_mode) g_free(vl_engine->output_mode);
            if (strstr(line, "surrounding")) vl_engine->output_mode = g_strdup("surrounding");
            else if (strstr(line, "forward")) vl_engine->output_mode = g_strdup("forward");
            else vl_engine->output_mode = g_strdup("preedit");
        } else if (strncmp(line, "IM_FRAMEWORK=", 13) == 0) {
            if (vl_engine->im_framework) g_free(vl_engine->im_framework);
            if (strstr(line, "fcitx5")) vl_engine->im_framework = g_strdup("fcitx5");
            else if (strstr(line, "uinput")) vl_engine->im_framework = g_strdup("uinput");
            else if (strstr(line, "ibus")) vl_engine->im_framework = g_strdup("ibus");
            else if (strstr(line, "fcitx")) vl_engine->im_framework = g_strdup("fcitx");
            else vl_engine->im_framework = g_strdup("auto");
        } else if (strncmp(line, "CHARSET=", 8) == 0) {
            const char *val_p = line + 8;
            while (*val_p == '"' || *val_p == '\'' || *val_p == ' ') val_p++;
            vl_engine->charset = atoi(val_p);
        } else if (strncmp(line, "AUTOSTART=", 10) == 0) {
            vl_engine->autostart = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "UI_LANG=", 8) == 0) {
            if (vl_engine->ui_lang) g_free(vl_engine->ui_lang);
            if (strstr(line, "en") != NULL || strstr(line, "EN") != NULL) {
                vl_engine->ui_lang = g_strdup("en");
            } else {
                vl_engine->ui_lang = g_strdup("vi");
            }
        } else if (strncmp(line, "ICON_STYLE=", 11) == 0) {
            if (vl_engine->icon_style) g_free(vl_engine->icon_style);
            if (strstr(line, "badge")) vl_engine->icon_style = g_strdup("badge");
            else if (strstr(line, "lotus")) vl_engine->icon_style = g_strdup("lotus");
            else if (strstr(line, "symbolic")) vl_engine->icon_style = g_strdup("symbolic");
            else vl_engine->icon_style = g_strdup("flag");
        } else if (strncmp(line, "FLAG_VARIANT=", 13) == 0) {
            if (vl_engine->flag_variant) g_free(vl_engine->flag_variant);
            if (strstr(line, "uk") || strstr(line, "UK")) vl_engine->flag_variant = g_strdup("uk");
            else vl_engine->flag_variant = g_strdup("us");
        } else if (strncmp(line, "RESTORE_KEY=", 12) == 0) {
            if (vl_engine->restore_key) g_free(vl_engine->restore_key);
            if (strstr(line, "shift_backspace")) vl_engine->restore_key = g_strdup("shift_backspace");
            else if (strstr(line, "none") || strstr(line, "None")) vl_engine->restore_key = g_strdup("none");
            else vl_engine->restore_key = g_strdup("esc");
        } else if (strncmp(line, "THEME=", 6) == 0) {
            if (vl_engine->theme) g_free(vl_engine->theme);
            if (strstr(line, "dark")) vl_engine->theme = g_strdup("dark");
            else if (strstr(line, "light")) vl_engine->theme = g_strdup("light");
            else vl_engine->theme = g_strdup("auto");
        }
    }
    fclose(fp);

    const gchar *engine_name = ibus_engine_get_name((IBusEngine *)vl_engine);
    if (has_input_method_override) {
        vl_engine->input_method = config_im;
        vl_engine->is_vni = (config_im == IM_VNI);
    } else if (engine_name && strstr(engine_name, "vni") != NULL) {
        vl_engine->input_method = IM_VNI;
        vl_engine->is_vni = TRUE;
    }

    lotuskey_set_input_method(
        vl_engine->session,
        vl_engine->is_vni ? LOTUSKEY_INPUT_VNI : LOTUSKEY_INPUT_TELEX
    );
    lotuskey_set_grammar_profile(
        vl_engine->session,
        vl_engine->sen_flex ? LOTUSKEY_GRAMMAR_SEN_FLEX : LOTUSKEY_GRAMMAR_CLASSIC
    );
    lotuskey_set_smart_bilingual(vl_engine->session, vl_engine->smart_bilingual);
    lotuskey_set_modern_orthography(vl_engine->session, vl_engine->modern_orthography);
    lotuskey_set_quick_telex(vl_engine->session, vl_engine->quick_telex);
}

static void ibus_lotus_save_user_config(IBusLotusEngine *vl_engine) {
    gchar *dir_path = ibus_lotus_get_config_dir();
    if (!dir_path) {
        return;
    }
    g_mkdir_with_parents(dir_path, 0700);
    chmod(dir_path, 0700);
    gchar *path = g_build_filename(dir_path, "config.env", NULL);

    FILE *fp = fopen(path, "w");
    if (!fp) {
        g_free(path);
        g_free(dir_path);
        return;
    }
    const char *tm_str = "Both";
    if (vl_engine->toggle_mode == TOGGLE_CTRL_SHIFT) tm_str = "Control+Shift";
    else if (vl_engine->toggle_mode == TOGGLE_ALT_Z) tm_str = "Alt+Z";
    else if (vl_engine->toggle_mode == TOGGLE_SHIFT_SPACE) tm_str = "Shift+Space";
    else if (vl_engine->toggle_mode == TOGGLE_NONE) tm_str = "None";

    const char *im_str = "telex";
    if (vl_engine->input_method == IM_VNI) im_str = "vni";
    else if (vl_engine->input_method == IM_TELEX_VNI) im_str = "telex_vni";

    const char *lang_str = (vl_engine->ui_lang && strcmp(vl_engine->ui_lang, "en") == 0) ? "en" : "vi";
    const char *icon_style_str = vl_engine->icon_style ? vl_engine->icon_style : "flag";
    const char *flag_var_str = vl_engine->flag_variant ? vl_engine->flag_variant : "us";
    const char *restore_key_str = vl_engine->restore_key ? vl_engine->restore_key : "esc";
    const char *theme_str = vl_engine->theme ? vl_engine->theme : "auto";

    fprintf(fp, "ENABLED=\"%s\"\n", vl_engine->enabled ? "true" : "false");
    fprintf(fp, "INPUT_METHOD=\"%s\"\n", im_str);
    fprintf(fp, "GRAMMAR_PROFILE=\"%s\"\n", vl_engine->sen_flex ? "sen_flex" : "classic");
    fprintf(fp, "SMART_BILINGUAL=\"%s\"\n", vl_engine->smart_bilingual ? "true" : "false");
    fprintf(fp, "MODERN_ORTHOGRAPHY=\"%s\"\n", vl_engine->modern_orthography ? "true" : "false");
    fprintf(fp, "QUICK_TELEX=\"%s\"\n", vl_engine->quick_telex ? "true" : "false");
    fprintf(fp, "PREEDIT_UNDERLINE=\"%s\"\n", vl_engine->preedit_underline ? "true" : "false");
    fprintf(fp, "MODE_MENU_KEY=\"%s\"\n", vl_engine->grave_menu_enabled ? "grave" : "None");
    fprintf(fp, "TOGGLE_KEY=\"%s\"\n", tm_str);
    fprintf(fp, "W2U=\"%s\"\n", vl_engine->w2u ? "true" : "false");
    fprintf(fp, "BRACKET_TRANSFORM=\"%s\"\n", vl_engine->bracket_transform ? "true" : "false");
    fprintf(fp, "MACRO_ENABLED=\"%s\"\n", vl_engine->macro_enabled ? "true" : "false");
    fprintf(fp, "MACRO_IN_OFF_MODE=\"%s\"\n", vl_engine->macro_in_off_mode ? "true" : "false");
    fprintf(fp, "AUTO_CAPITALIZE_MACRO=\"%s\"\n", vl_engine->auto_capitalize_macro ? "true" : "false");
    fprintf(fp, "PER_APP_REMEMBER=\"%s\"\n", vl_engine->per_app_remember ? "true" : "false");
    fprintf(fp, "AUTO_DISABLE_URL_BAR=\"%s\"\n", vl_engine->auto_disable_url_bar ? "true" : "false");
    fprintf(fp, "COMPACT_MODE=\"%s\"\n", vl_engine->compact_mode ? "true" : "false");
    fprintf(fp, "OUTPUT_MODE=\"%s\"\n", vl_engine->output_mode ? vl_engine->output_mode : "preedit");
    fprintf(fp, "IM_FRAMEWORK=\"%s\"\n", vl_engine->im_framework ? vl_engine->im_framework : "auto");
    fprintf(fp, "CHARSET=\"%d\"\n", vl_engine->charset);
    fprintf(fp, "AUTOSTART=\"%s\"\n", vl_engine->autostart ? "true" : "false");
    fprintf(fp, "UI_LANG=\"%s\"\n", lang_str);
    fprintf(fp, "ICON_STYLE=\"%s\"\n", icon_style_str);
    fprintf(fp, "FLAG_VARIANT=\"%s\"\n", flag_var_str);
    fprintf(fp, "RESTORE_KEY=\"%s\"\n", restore_key_str);
    fprintf(fp, "THEME=\"%s\"\n", theme_str);
    fclose(fp);
    chmod(path, 0600);

    struct stat st;
    if (stat(path, &st) == 0) {
        vl_engine->config_mtime = st.st_mtime;
    }
    g_free(path);

    /* Synchronize config.json while preserving excluded_apps if already configured */
    gchar *path_json = g_build_filename(dir_path, "config.json", NULL);
    gchar *preserved_excluded_apps = NULL;
    gchar *existing_json = NULL;
    if (g_file_get_contents(path_json, &existing_json, NULL, NULL) && existing_json) {
        const char *ex_key = strstr(existing_json, "\"excluded_apps\"");
        if (ex_key) {
            const char *br_open = strchr(ex_key, '[');
            const char *br_close = br_open ? strchr(br_open, ']') : NULL;
            if (br_open && br_close && br_close > br_open) {
                preserved_excluded_apps = g_strndup(br_open, (gsize)(br_close - br_open + 1));
            }
        }
        g_free(existing_json);
    }

    FILE *fp_json = fopen(path_json, "w");
    if (fp_json) {
        fprintf(fp_json, "{\n");
        fprintf(fp_json, "    \"enabled\": %s,\n", vl_engine->enabled ? "true" : "false");
        fprintf(fp_json, "    \"input_method\": %d,\n", vl_engine->input_method);
        fprintf(fp_json, "    \"output_mode\": \"%s\",\n", vl_engine->output_mode ? vl_engine->output_mode : "preedit");
        fprintf(fp_json, "    \"im_framework\": \"%s\",\n", vl_engine->im_framework ? vl_engine->im_framework : "auto");
        fprintf(fp_json, "    \"charset\": %d,\n", vl_engine->charset);
        fprintf(fp_json, "    \"free_tone_marking\": %s,\n", vl_engine->sen_flex ? "true" : "false");
        fprintf(fp_json, "    \"modern_tone_style\": %s,\n", vl_engine->modern_orthography ? "true" : "false");
        fprintf(fp_json, "    \"auto_correct\": %s,\n", vl_engine->smart_bilingual ? "true" : "false");
        fprintf(fp_json, "    \"w2u\": %s,\n", vl_engine->w2u ? "true" : "false");
        fprintf(fp_json, "    \"bracket_transform\": %s,\n", vl_engine->bracket_transform ? "true" : "false");
        fprintf(fp_json, "    \"macro_enabled\": %s,\n", vl_engine->macro_enabled ? "true" : "false");
        fprintf(fp_json, "    \"macro_in_off_mode\": %s,\n", vl_engine->macro_in_off_mode ? "true" : "false");
        fprintf(fp_json, "    \"auto_capitalize_macro\": %s,\n", vl_engine->auto_capitalize_macro ? "true" : "false");
        fprintf(fp_json, "    \"per_app_remember\": %s,\n", vl_engine->per_app_remember ? "true" : "false");
        fprintf(fp_json, "    \"auto_disable_url_bar\": %s,\n", vl_engine->auto_disable_url_bar ? "true" : "false");
        fprintf(fp_json, "    \"compact_mode\": %s,\n", vl_engine->compact_mode ? "true" : "false");
        fprintf(fp_json, "    \"toggle_key\": \"%s\",\n", tm_str);
        fprintf(fp_json, "    \"mode_menu_key\": \"%s\",\n", vl_engine->grave_menu_enabled ? "grave" : "None");
        fprintf(fp_json, "    \"quick_telex\": %s,\n", vl_engine->quick_telex ? "true" : "false");
        fprintf(fp_json, "    \"preedit_underline\": %s,\n", vl_engine->preedit_underline ? "true" : "false");
        fprintf(fp_json, "    \"autostart\": %s,\n", vl_engine->autostart ? "true" : "false");
        fprintf(fp_json, "    \"ui_lang\": \"%s\",\n", lang_str);
        fprintf(fp_json, "    \"icon_style\": \"%s\",\n", icon_style_str);
        fprintf(fp_json, "    \"flag_variant\": \"%s\",\n", flag_var_str);
        fprintf(fp_json, "    \"restore_key\": \"%s\",\n", restore_key_str);
        fprintf(fp_json, "    \"theme\": \"%s\",\n", theme_str);
        fprintf(fp_json, "    \"excluded_apps\": %s\n",
                preserved_excluded_apps ? preserved_excluded_apps : "[\"kitty\", \"Alacritty\", \"wezterm\", \"foot\", \"gnome-terminal-server\", \"konsole\"]");
        fprintf(fp_json, "}\n");
        fclose(fp_json);
        chmod(path_json, 0600);
    }
    if (preserved_excluded_apps) g_free(preserved_excluded_apps);
    g_free(path_json);
    g_free(dir_path);
}

static const char *ibus_lotus_resolve_icon_filename(IBusLotusEngine *vl_engine) {
    const char *style = vl_engine->icon_style ? vl_engine->icon_style : "flag";
    const char *flag_var = vl_engine->flag_variant ? vl_engine->flag_variant : "us";

    if (strcmp(style, "badge") == 0) {
        return vl_engine->enabled ? "lotuskey-badge-vn.svg" : "lotuskey-badge-en.svg";
    }
    if (strcmp(style, "lotus") == 0) {
        return vl_engine->enabled ? "lotuskey.svg" : "lotuskey-off.svg";
    }
    if (strcmp(style, "symbolic") == 0) {
        return vl_engine->enabled ? "lotuskey-symbolic.svg" : "lotuskey-off-symbolic.svg";
    }
    /* Default: flat national flag ("flag") */
    if (vl_engine->enabled) {
        return "lotuskey-flag-vn.svg";
    }
    return (strcmp(flag_var, "uk") == 0) ? "lotuskey-flag-uk.svg" : "lotuskey-flag-us.svg";
}

static const char *ibus_lotus_resolve_status_symbol(IBusLotusEngine *vl_engine) {
    const char *style = vl_engine->icon_style ? vl_engine->icon_style : "flag";
    const char *flag_var = vl_engine->flag_variant ? vl_engine->flag_variant : "us";

    if (strcmp(style, "badge") == 0) {
        return vl_engine->enabled ? "V" : "E";
    }
    if (strcmp(style, "symbolic") == 0 || strcmp(style, "lotus") == 0) {
        return vl_engine->enabled ? "VN" : "EN";
    }
    if (vl_engine->enabled) {
        return "VN";
    }
    return (strcmp(flag_var, "uk") == 0) ? "UK" : "US";
}

static gchar *ibus_lotus_resolve_status_icon_path(IBusLotusEngine *vl_engine) {
    const char *fname = ibus_lotus_resolve_icon_filename(vl_engine);
    const gchar *home = g_get_home_dir();
    if (home) {
        gchar *user_p = g_build_filename(home, ".local", "share", "icons", "hicolor", "scalable", "apps", fname, NULL);
        if (g_file_test(user_p, G_FILE_TEST_EXISTS)) {
            return user_p;
        }
        g_free(user_p);
    }

    gchar *sys_p = g_build_filename("/usr/share/icons/hicolor/scalable/apps", fname, NULL);
    if (g_file_test(sys_p, G_FILE_TEST_EXISTS)) {
        return sys_p;
    }
    g_free(sys_p);

    char self_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", self_path, sizeof(self_path) - 1);
    if (len > 0) {
        self_path[len] = '\0';
        gchar *bin_dir = g_path_get_dirname(self_path);
        gchar *root_dir = g_path_get_dirname(bin_dir);
        gchar *prefix_dir = g_path_get_dirname(root_dir);
        gchar *asset_p = g_build_filename(root_dir, "assets", fname, NULL);
        gchar *prefix_icon_p = g_build_filename(prefix_dir, "share", "icons", "hicolor", "scalable", "apps", fname, NULL);
        gchar *prefix_asset_p = g_build_filename(prefix_dir, "share", "lotuskey", "assets", fname, NULL);
        g_free(bin_dir);
        g_free(root_dir);
        g_free(prefix_dir);
        if (g_file_test(asset_p, G_FILE_TEST_EXISTS)) {
            g_free(prefix_icon_p);
            g_free(prefix_asset_p);
            return asset_p;
        }
        g_free(asset_p);
        if (g_file_test(prefix_icon_p, G_FILE_TEST_EXISTS)) {
            g_free(prefix_asset_p);
            return prefix_icon_p;
        }
        g_free(prefix_icon_p);
        if (g_file_test(prefix_asset_p, G_FILE_TEST_EXISTS)) {
            return prefix_asset_p;
        }
        g_free(prefix_asset_p);
    }

    return g_strdup("input-keyboard");
}

static void ibus_lotus_build_prop_list(IBusLotusEngine *vl_engine) {
    if (vl_engine->status_prop) {
        g_object_unref(vl_engine->status_prop);
        vl_engine->status_prop = NULL;
    }
    if (vl_engine->prop_list) {
        g_object_unref(vl_engine->prop_list);
    }
    vl_engine->prop_list = ibus_prop_list_new();
    g_object_ref_sink(vl_engine->prop_list);

    IBusProperty *prop;
    IBusText *label;
    IBusText *symbol_text;
    gboolean is_en = (vl_engine->ui_lang && strcmp(vl_engine->ui_lang, "en") == 0);

    const char *im_label = "Telex";
    if (vl_engine->input_method == IM_VNI) im_label = "VNI";
    else if (vl_engine->input_method == IM_TELEX_VNI) im_label = "Telex+VNI";

    const char *symbol_str = ibus_lotus_resolve_status_symbol(vl_engine);
    gchar *icon_path = ibus_lotus_resolve_status_icon_path(vl_engine);

    const char *mode_label = is_en
        ? (vl_engine->enabled ? "Vietnamese (ON)" : "English (OFF)")
        : (vl_engine->enabled ? "Tiếng Việt (BẬT)" : "Tiếng Anh (TẮT)");

    char status_str[128];
    snprintf(status_str, sizeof(status_str), "[%s] LotusKey: %s (%s)", symbol_str, mode_label, im_label);

    /* 1. Primary "InputMode" property (Required by GNOME Shell Top Bar & IBus Panel) */
    label = ibus_text_new_from_string(status_str);
    symbol_text = ibus_text_new_from_string(symbol_str);
    prop = ibus_property_new("InputMode", PROP_TYPE_NORMAL, label, icon_path, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_property_set_symbol(prop, symbol_text);
    vl_engine->status_prop = g_object_ref(prop);
    ibus_prop_list_append(vl_engine->prop_list, prop);
    g_free(icon_path);

    /* 2. Submenu: Input Method (Telex / VNI / Telex+VNI) */
    IBusPropList *im_sub = ibus_prop_list_new();
    ibus_prop_list_append(im_sub, ibus_property_new(
        "im-telex", PROP_TYPE_RADIO, ibus_text_new_from_static_string("Telex"), NULL, NULL,
        TRUE, TRUE, (vl_engine->input_method == IM_TELEX) ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(im_sub, ibus_property_new(
        "im-vni", PROP_TYPE_RADIO, ibus_text_new_from_static_string("VNI"), NULL, NULL,
        TRUE, TRUE, (vl_engine->input_method == IM_VNI) ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(im_sub, ibus_property_new(
        "im-telex-vni", PROP_TYPE_RADIO, ibus_text_new_from_static_string("Telex + VNI"), NULL, NULL,
        TRUE, TRUE, (vl_engine->input_method == IM_TELEX_VNI) ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));

    char im_menu_title[64];
    snprintf(im_menu_title, sizeof(im_menu_title), "%s: %s",
             is_en ? "Input Method" : "Kiểu gõ", im_label);
    prop = ibus_property_new("menu-input-method", PROP_TYPE_MENU,
                             ibus_text_new_from_string(im_menu_title), NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, im_sub);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    /* 3. Submenu: Charset (Unicode NFC / Combining NFD / TCVN3 / VNI Windows) */
    IBusPropList *cs_sub = ibus_prop_list_new();
    gboolean is_cs_comb = (vl_engine->charset == LOTUS_CHARSET_COMBINING_CFG || vl_engine->charset == LOTUS_CHARSET_COMBINING_ENUM);
    gboolean is_cs_tcvn = (vl_engine->charset == LOTUS_CHARSET_TCVN3_CFG || vl_engine->charset == LOTUS_CHARSET_TCVN3_ENUM);
    gboolean is_cs_vni  = (vl_engine->charset == LOTUS_CHARSET_VNI_WIN_CFG || vl_engine->charset == LOTUS_CHARSET_VNI_WIN_ENUM);
    gboolean is_cs_uni  = (!is_cs_comb && !is_cs_tcvn && !is_cs_vni);

    ibus_prop_list_append(cs_sub, ibus_property_new(
        "cs-unicode", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Unicode (Precomposed NFC)" : "Unicode dựng sẵn (NFC)"), NULL, NULL,
        TRUE, TRUE, is_cs_uni ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(cs_sub, ibus_property_new(
        "cs-combining", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Unicode (Combining NFD)" : "Unicode tổ hợp (NFD)"), NULL, NULL,
        TRUE, TRUE, is_cs_comb ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(cs_sub, ibus_property_new(
        "cs-tcvn3", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string("TCVN3 (ABC)"), NULL, NULL,
        TRUE, TRUE, is_cs_tcvn ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(cs_sub, ibus_property_new(
        "cs-vni-win", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string("VNI Windows"), NULL, NULL,
        TRUE, TRUE, is_cs_vni ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));

    const char *cs_short = is_en
        ? (is_cs_comb ? "Combining" : (is_cs_tcvn ? "TCVN3" : (is_cs_vni ? "VNI Win" : "Unicode")))
        : (is_cs_comb ? "Tổ hợp" : (is_cs_tcvn ? "TCVN3" : (is_cs_vni ? "VNI Win" : "Unicode")));
    char cs_menu_title[64];
    snprintf(cs_menu_title, sizeof(cs_menu_title), "%s: %s",
             is_en ? "Charset" : "Bảng mã", cs_short);
    prop = ibus_property_new("menu-charset", PROP_TYPE_MENU,
                             ibus_text_new_from_string(cs_menu_title), NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, cs_sub);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    /* 4. Submenu: Typing Options (smart-bilingual, modern-orthography, sen-flex, macro-enabled, w2u) */
    IBusPropList *opt_sub = ibus_prop_list_new();
    ibus_prop_list_append(opt_sub, ibus_property_new(
        "smart-bilingual", PROP_TYPE_TOGGLE,
        ibus_text_new_from_static_string(is_en ? "Auto-restore English words" : "Tự khôi phục từ tiếng Anh"), NULL, NULL,
        TRUE, TRUE, vl_engine->smart_bilingual ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(opt_sub, ibus_property_new(
        "modern-orthography", PROP_TYPE_TOGGLE,
        ibus_text_new_from_static_string(is_en ? "Modern tone placement (oà, uý)" : "Đặt dấu kiểu mới (oà, uý)"), NULL, NULL,
        TRUE, TRUE, vl_engine->modern_orthography ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(opt_sub, ibus_property_new(
        "sen-flex", PROP_TYPE_TOGGLE,
        ibus_text_new_from_static_string(is_en ? "Free tone marking (SEN Flex)" : "Bỏ dấu tự do (SEN Flex)"), NULL, NULL,
        TRUE, TRUE, vl_engine->sen_flex ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(opt_sub, ibus_property_new(
        "macro-enabled", PROP_TYPE_TOGGLE,
        ibus_text_new_from_static_string(is_en ? "Enable Macros (Shortcuts)" : "Bật gõ tắt (Macro)"), NULL, NULL,
        TRUE, TRUE, vl_engine->macro_enabled ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(opt_sub, ibus_property_new(
        "w2u", PROP_TYPE_TOGGLE,
        ibus_text_new_from_static_string(is_en ? "Convert initial W to Ư" : "Đổi W thành Ư ở đầu từ"), NULL, NULL,
        TRUE, TRUE, vl_engine->w2u ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));

    prop = ibus_property_new("menu-typing-options", PROP_TYPE_MENU,
                             ibus_text_new_from_static_string(is_en ? "Typing Options" : "Tùy chọn gõ"), NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, opt_sub);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    /* 5. Submenu: Output Mode (Pre-edit / Surrounding / Forward) */
    IBusPropList *out_sub = ibus_prop_list_new();
    const char *curr_out = vl_engine->output_mode ? vl_engine->output_mode : "preedit";
    gboolean is_out_surr = (strcmp(curr_out, "surrounding") == 0);
    gboolean is_out_fwd  = (strcmp(curr_out, "forward") == 0);
    gboolean is_out_pre  = (!is_out_surr && !is_out_fwd);

    ibus_prop_list_append(out_sub, ibus_property_new(
        "out-preedit", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Pre-edit (Recommended)" : "Pre-edit (Mặc định)"), NULL, NULL,
        TRUE, TRUE, is_out_pre ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(out_sub, ibus_property_new(
        "out-surrounding", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string("Surrounding Text"), NULL, NULL,
        TRUE, TRUE, is_out_surr ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(out_sub, ibus_property_new(
        "out-forward", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string("Forward Backspace"), NULL, NULL,
        TRUE, TRUE, is_out_fwd ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));

    const char *out_short = is_out_surr ? "Surrounding" : (is_out_fwd ? "Forward" : "Pre-edit");
    char out_menu_title[64];
    snprintf(out_menu_title, sizeof(out_menu_title), "%s: %s",
             is_en ? "Output Mode" : "Chế độ xuất chữ", out_short);
    prop = ibus_property_new("menu-output-mode", PROP_TYPE_MENU,
                             ibus_text_new_from_string(out_menu_title), NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, out_sub);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    /* 6. Submenu: Tray Icon Style (Flat Flag VN/US, Flat Flag VN/UK, Badge V/E, Lotus, Symbolic) */
    IBusPropList *ic_sub = ibus_prop_list_new();
    const char *curr_ic = vl_engine->icon_style ? vl_engine->icon_style : "flag";
    const char *curr_fv = vl_engine->flag_variant ? vl_engine->flag_variant : "us";
    gboolean ic_flag_us = (strcmp(curr_ic, "flag") == 0 && strcmp(curr_fv, "uk") != 0);
    gboolean ic_flag_uk = (strcmp(curr_ic, "flag") == 0 && strcmp(curr_fv, "uk") == 0);
    gboolean ic_badge   = (strcmp(curr_ic, "badge") == 0);
    gboolean ic_lotus   = (strcmp(curr_ic, "lotus") == 0);
    gboolean ic_symb    = (strcmp(curr_ic, "symbolic") == 0);

    ibus_prop_list_append(ic_sub, ibus_property_new(
        "icon-flag-us", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Flat Flag VN / US" : "Cờ phẳng VN / US"), NULL, NULL,
        TRUE, TRUE, ic_flag_us ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(ic_sub, ibus_property_new(
        "icon-flag-uk", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Flat Flag VN / UK" : "Cờ phẳng VN / UK"), NULL, NULL,
        TRUE, TRUE, ic_flag_uk ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(ic_sub, ibus_property_new(
        "icon-badge", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "V / E Badge (UniKey)" : "Chữ V / E (UniKey)"), NULL, NULL,
        TRUE, TRUE, ic_badge ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(ic_sub, ibus_property_new(
        "icon-lotus", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Lotus Flower" : "Hoa sen LotusKey"), NULL, NULL,
        TRUE, TRUE, ic_lotus ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));
    ibus_prop_list_append(ic_sub, ibus_property_new(
        "icon-symbolic", PROP_TYPE_RADIO,
        ibus_text_new_from_static_string(is_en ? "Monochrome Symbolic" : "Đơn sắc (Symbolic)"), NULL, NULL,
        TRUE, TRUE, ic_symb ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED, NULL));

    const char *ic_short = is_en
        ? (ic_flag_uk ? "Flag VN/UK" : (ic_badge ? "V/E Badge" : (ic_lotus ? "Lotus" : (ic_symb ? "Symbolic" : "Flag VN/US"))))
        : (ic_flag_uk ? "Cờ VN/UK" : (ic_badge ? "Chữ V/E" : (ic_lotus ? "Hoa sen" : (ic_symb ? "Đơn sắc" : "Cờ VN/US"))));
    char ic_menu_title[64];
    snprintf(ic_menu_title, sizeof(ic_menu_title), "%s: %s",
             is_en ? "Icon Style" : "Biểu tượng", ic_short);
    prop = ibus_property_new("menu-icon-style", PROP_TYPE_MENU,
                             ibus_text_new_from_string(ic_menu_title), NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, ic_sub);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    /* 7. Action Items: Clipboard Converter, Quick Menu, Settings */
    label = ibus_text_new_from_static_string(is_en ? "Clipboard Charset Converter..." : "Chuyển mã Clipboard...");
    prop = ibus_property_new("lotus-clipboard-convert", PROP_TYPE_NORMAL, label, "edit-paste", NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    label = ibus_text_new_from_static_string(is_en ? "Quick Menu (` key)..." : "Menu nhanh (Phím `)...");
    prop = ibus_property_new("lotus-quick-menu", PROP_TYPE_NORMAL, label, NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    label = ibus_text_new_from_static_string(is_en ? "LotusKey Settings..." : "Cài đặt LotusKey...");
    prop = ibus_property_new("lotus-setup", PROP_TYPE_NORMAL, label, "preferences-system", NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);
}

static void ibus_lotus_toggle_vietnamese(IBusLotusEngine *vl_engine) {
    active_engines = g_list_remove(active_engines, vl_engine);
    active_engines = g_list_prepend(active_engines, vl_engine);
    vl_engine->enabled = !vl_engine->enabled;
    if (!vl_engine->enabled && lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    }
    ibus_lotus_save_user_config(vl_engine);
    ibus_lotus_reload_all_engines();

    gchar *icon_to_use = ibus_lotus_resolve_status_icon_path(vl_engine);
    gboolean is_en = (vl_engine->ui_lang && strcmp(vl_engine->ui_lang, "en") == 0);
    if (vl_engine->enabled) {
        ibus_lotus_send_notification(
            "LotusKey",
            is_en ? "Vietnamese input enabled" : "Đã bật gõ tiếng Việt",
            icon_to_use
        );
    } else {
        ibus_lotus_send_notification(
            "LotusKey",
            is_en ? "English mode (direct input)" : "Chế độ tiếng Anh (tắt bộ gõ)",
            icon_to_use
        );
    }
    g_free(icon_to_use);
}

typedef struct {
    const char *lower_utf8;
    const char *upper_utf8;
    char lower_base;
    char upper_base;
    uint8_t mod;
    uint8_t tone;
} LotusUtf8CharMap;

static const LotusUtf8CharMap kVnUtf8Map[] = {
    { "đ", "Đ", 'd', 'D', 1, 0 },
    { "à", "À", 'a', 'A', 0, 1 }, { "á", "Á", 'a', 'A', 0, 2 }, { "ả", "Ả", 'a', 'A', 0, 3 }, { "ã", "Ã", 'a', 'A', 0, 4 }, { "ạ", "Ạ", 'a', 'A', 0, 5 },
    { "ă", "Ă", 'a', 'A', 3, 0 }, { "ằ", "Ằ", 'a', 'A', 3, 1 }, { "ắ", "Ắ", 'a', 'A', 3, 2 }, { "ẳ", "Ẳ", 'a', 'A', 3, 3 }, { "ẵ", "Ẵ", 'a', 'A', 3, 4 }, { "ặ", "Ặ", 'a', 'A', 3, 5 },
    { "â", "Â", 'a', 'A', 2, 0 }, { "ầ", "Ầ", 'a', 'A', 2, 1 }, { "ấ", "Ấ", 'a', 'A', 2, 2 }, { "ẩ", "Ẩ", 'a', 'A', 2, 3 }, { "ẫ", "Ẫ", 'a', 'A', 2, 4 }, { "ậ", "Ậ", 'a', 'A', 2, 5 },
    { "è", "È", 'e', 'E', 0, 1 }, { "é", "É", 'e', 'E', 0, 2 }, { "ẻ", "Ẻ", 'e', 'E', 0, 3 }, { "ẽ", "Ẽ", 'e', 'E', 0, 4 }, { "ẹ", "Ẹ", 'e', 'E', 0, 5 },
    { "ê", "Ê", 'e', 'E', 2, 0 }, { "ề", "Ề", 'e', 'E', 2, 1 }, { "ế", "Ế", 'e', 'E', 2, 2 }, { "ể", "Ể", 'e', 'E', 2, 3 }, { "ễ", "Ễ", 'e', 'E', 2, 4 }, { "ệ", "Ệ", 'e', 'E', 2, 5 },
    { "ì", "Ì", 'i', 'I', 0, 1 }, { "í", "Í", 'i', 'I', 0, 2 }, { "ỉ", "Ỉ", 'i', 'I', 0, 3 }, { "ĩ", "Ĩ", 'i', 'I', 0, 4 }, { "ị", "Ị", 'i', 'I', 0, 5 },
    { "ò", "Ò", 'o', 'O', 0, 1 }, { "ó", "Ó", 'o', 'O', 0, 2 }, { "ỏ", "Ỏ", 'o', 'O', 0, 3 }, { "õ", "Õ", 'o', 'O', 0, 4 }, { "ọ", "Ọ", 'o', 'O', 0, 5 },
    { "ô", "Ô", 'o', 'O', 2, 0 }, { "ồ", "Ồ", 'o', 'O', 2, 1 }, { "ố", "Ố", 'o', 'O', 2, 2 }, { "ổ", "Ổ", 'o', 'O', 2, 3 }, { "ỗ", "Ỗ", 'o', 'O', 2, 4 }, { "ộ", "Ộ", 'o', 'O', 2, 5 },
    { "ơ", "Ơ", 'o', 'O', 4, 0 }, { "ờ", "Ờ", 'o', 'O', 4, 1 }, { "ớ", "Ớ", 'o', 'O', 4, 2 }, { "ở", "Ở", 'o', 'O', 4, 3 }, { "ỡ", "Ỡ", 'o', 'O', 4, 4 }, { "ợ", "Ợ", 'o', 'O', 4, 5 },
    { "ù", "Ù", 'u', 'U', 0, 1 }, { "ú", "Ú", 'u', 'U', 0, 2 }, { "ủ", "Ủ", 'u', 'U', 0, 3 }, { "ũ", "Ũ", 'u', 'U', 0, 4 }, { "ụ", "Ụ", 'u', 'U', 0, 5 },
    { "ư", "Ư", 'u', 'U', 4, 0 }, { "ừ", "Ừ", 'u', 'U', 4, 1 }, { "ứ", "Ứ", 'u', 'U', 4, 2 }, { "ử", "Ử", 'u', 'U', 4, 3 }, { "ữ", "Ữ", 'u', 'U', 4, 4 }, { "ự", "Ự", 'u', 'U', 4, 5 },
    { "ỳ", "Ỳ", 'y', 'Y', 0, 1 }, { "ý", "Ý", 'y', 'Y', 0, 2 }, { "ỷ", "Ỷ", 'y', 'Y', 0, 3 }, { "ỹ", "Ỹ", 'y', 'Y', 0, 4 }, { "ỵ", "Ỵ", 'y', 'Y', 0, 5 },
};

static void ibus_lotus_raw_keys_for_utf8(const char *utf8_str, gboolean is_vni, char *out, size_t out_cap) {
    size_t len = 0;
    char tone_char = 0;
    const char *p = utf8_str;
    while (*p && len + 4 < out_cap) {
        size_t clen = ibus_lotus_utf8_char_len((unsigned char)*p);
        if (clen == 1) {
            out[len++] = *p;
            p++;
            continue;
        }
        gboolean matched = FALSE;
        for (size_t i = 0; i < sizeof(kVnUtf8Map) / sizeof(kVnUtf8Map[0]); i++) {
            gboolean is_lower = (strlen(kVnUtf8Map[i].lower_utf8) == clen && strncmp(p, kVnUtf8Map[i].lower_utf8, clen) == 0);
            gboolean is_upper = !is_lower && (strlen(kVnUtf8Map[i].upper_utf8) == clen && strncmp(p, kVnUtf8Map[i].upper_utf8, clen) == 0);
            if (is_lower || is_upper) {
                char base = is_upper ? kVnUtf8Map[i].upper_base : kVnUtf8Map[i].lower_base;
                out[len++] = base;
                switch (kVnUtf8Map[i].mod) {
                    case 1:
                        out[len++] = is_vni ? '9' : (is_upper ? 'D' : 'd');
                        break;
                    case 2:
                        out[len++] = is_vni ? '6' : kVnUtf8Map[i].lower_base;
                        break;
                    case 3:
                        out[len++] = is_vni ? '8' : 'w';
                        break;
                    case 4:
                        if ((base == 'o' || base == 'O') && len >= 3 &&
                            (out[len - 3] == 'u' || out[len - 3] == 'U') &&
                            (out[len - 2] == 'w' || out[len - 2] == '7')) {
                            out[len - 2] = base;
                            out[len - 1] = is_vni ? '7' : 'w';
                        } else {
                            out[len++] = is_vni ? '7' : 'w';
                        }
                        break;
                    default:
                        break;
                }
                if (kVnUtf8Map[i].tone > 0 && kVnUtf8Map[i].tone <= 5) {
                    tone_char = is_vni ? "021345"[kVnUtf8Map[i].tone] : "0fsrxj"[kVnUtf8Map[i].tone];
                }
                matched = TRUE;
                break;
            }
        }
        if (!matched) {
            for (size_t k = 0; k < clen && p[k] && len + 1 < out_cap; k++) {
                out[len++] = p[k];
            }
        }
        p += clen;
    }
    if (tone_char != 0 && len + 1 < out_cap) {
        out[len++] = tone_char;
    }
    out[len] = '\0';
}

static inline char vl_tolower(char c) {
    return (c >= 'A' && c <= 'Z') ? (char)(c + ('a' - 'A')) : c;
}

static uint8_t ibus_lotus_telex_tone_for_key(char lower_key) {
    switch (lower_key) {
        case 'f': return 1;
        case 's': return 2;
        case 'r': return 3;
        case 'x': return 4;
        case 'j': return 5;
        default: return 0;
    }
}

static gboolean ibus_lotus_has_non_ascii(const char *utf8_str) {
    if (!utf8_str) return FALSE;
    for (const unsigned char *p = (const unsigned char *)utf8_str; *p; p++) {
        if (*p >= 0x80) return TRUE;
    }
    return FALSE;
}

static uint8_t ibus_lotus_active_tone_of_utf8(const char *utf8_str) {
    if (!utf8_str) return 0;
    const char *p = utf8_str;
    while (*p) {
        size_t clen = ibus_lotus_utf8_char_len((unsigned char)*p);
        if (clen > 1) {
            for (size_t i = 0; i < sizeof(kVnUtf8Map) / sizeof(kVnUtf8Map[0]); i++) {
                if ((strlen(kVnUtf8Map[i].lower_utf8) == clen && strncmp(p, kVnUtf8Map[i].lower_utf8, clen) == 0) ||
                    (strlen(kVnUtf8Map[i].upper_utf8) == clen && strncmp(p, kVnUtf8Map[i].upper_utf8, clen) == 0)) {
                    if (kVnUtf8Map[i].tone > 0) {
                        return kVnUtf8Map[i].tone;
                    }
                }
            }
        }
        p += clen;
    }
    return 0;
}

static void ibus_lotus_replay_raw_keys(IBusLotusEngine *vl_engine, const char *raw_keys) {
    lotuskey_reset_session(vl_engine->session);
    for (size_t i = 0; raw_keys[i] != '\0'; i++) {
        lotuskey_feed_char(vl_engine->session, (uint32_t)(unsigned char)raw_keys[i]);
    }
}

static void ibus_lotus_backspace_composing(IBusLotusEngine *vl_engine) {
    vl_engine->last_bracket_key = 0;
    ibus_lotus_pop_raw_typed(vl_engine);
    const char *composing = lotuskey_get_composing_text(vl_engine->session);
    if (!composing || composing[0] == '\0') {
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }
    size_t len = strlen(composing);
    if (len >= 512) {
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }
    const size_t before_cp = ibus_lotus_utf8_codepoint_count(composing);
    char prefix[512];
    memcpy(prefix, composing, len + 1);
    size_t cut = len;
    while (cut > 0 && ((unsigned char)prefix[cut - 1] & 0xC0) == 0x80) {
        cut--;
    }
    if (cut > 0) {
        cut--;
    }
    prefix[cut] = '\0';

    lotuskey_feed_backspace(vl_engine->session);
    if (!lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }
    const char *after = lotuskey_get_composing_text(vl_engine->session);
    if (after && after[0] != '\0' && ibus_lotus_utf8_codepoint_count(after) < before_cp) {
        vl_engine->replayed_after_backspace = FALSE;
        ibus_lotus_update_preedit(vl_engine);
        return;
    }

    if (cut == 0) {
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }
    char raw_keys[1024];
    ibus_lotus_raw_keys_for_utf8(prefix, vl_engine->is_vni, raw_keys, sizeof(raw_keys));
    lotuskey_reset_session(vl_engine->session);
    for (size_t i = 0; raw_keys[i] != '\0'; i++) {
        lotuskey_feed_char(vl_engine->session, (uint32_t)(unsigned char)raw_keys[i]);
    }
    vl_engine->replayed_after_backspace = TRUE;
    if (!lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_engine_reset_internal(vl_engine);
    } else {
        ibus_lotus_update_preedit(vl_engine);
    }
}

static gboolean ibus_lotus_grave_timeout_cb(gpointer user_data) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)user_data;
    vl_engine->grave_timer_id = 0;
    ibus_lotus_spawn_tool("lotuskey-menu");
    return G_SOURCE_REMOVE;
}

/* Translate VNI digit key ('0'..'9') to Telex equivalent when in Telex+VNI hybrid mode */
static char ibus_lotus_translate_vni_digit_for_hybrid(IBusLotusEngine *vl_engine, guint keyval) {
    switch (keyval) {
        case '1': return 's';
        case '2': return 'f';
        case '3': return 'r';
        case '4': return 'x';
        case '5': return 'j';
        case '7':
        case '8': return 'w';
        case '9': return 'd';
        case '0': return 'z';
        case '6': {
            const char *comp = lotuskey_get_composing_text(vl_engine->session);
            if (comp) {
                /* Find the last vowel a/e/o in composing text to apply circumflex */
                char chosen = 0;
                for (const char *p = comp; *p; ) {
                    size_t clen = ibus_lotus_utf8_char_len((unsigned char)*p);
                    if (clen == 1) {
                        char lower = vl_tolower(*p);
                        if (lower == 'a' || lower == 'e' || lower == 'o') {
                            chosen = lower;
                        }
                    } else {
                        for (size_t i = 0; i < sizeof(kVnUtf8Map) / sizeof(kVnUtf8Map[0]); i++) {
                            if ((strlen(kVnUtf8Map[i].lower_utf8) == clen && strncmp(p, kVnUtf8Map[i].lower_utf8, clen) == 0) ||
                                (strlen(kVnUtf8Map[i].upper_utf8) == clen && strncmp(p, kVnUtf8Map[i].upper_utf8, clen) == 0)) {
                                char b = kVnUtf8Map[i].lower_base;
                                if (b == 'a' || b == 'e' || b == 'o') chosen = b;
                                break;
                            }
                        }
                    }
                    p += clen;
                }
                if (chosen != 0) return chosen;
            }
            return 0;
        }
        default:
            return 0;
    }
}

static void ibus_lotus_engine_init(IBusLotusEngine *vl_engine) {
    vl_engine->session = lotuskey_create_session();
    vl_engine->enabled = TRUE;
    vl_engine->is_vni = FALSE;
    vl_engine->input_method = IM_TELEX;
    vl_engine->smart_bilingual = TRUE;
    vl_engine->sen_flex = TRUE;
    vl_engine->modern_orthography = TRUE;
    vl_engine->quick_telex = FALSE;
    vl_engine->relaxed_coda = FALSE;
    vl_engine->preedit_underline = FALSE;
    vl_engine->is_password_field = FALSE;
    vl_engine->replayed_after_backspace = FALSE;
    vl_engine->grave_menu_enabled = TRUE;
    vl_engine->w2u = TRUE;
    vl_engine->bracket_transform = TRUE;
    vl_engine->macro_enabled = TRUE;
    vl_engine->macro_in_off_mode = FALSE;
    vl_engine->auto_capitalize_macro = TRUE;
    vl_engine->per_app_remember = TRUE;
    vl_engine->auto_disable_url_bar = TRUE;
    vl_engine->compact_mode = TRUE;
    vl_engine->autostart = TRUE;
    vl_engine->output_mode = g_strdup("preedit");
    vl_engine->im_framework = g_strdup("auto");
    vl_engine->ui_lang = g_strdup("vi");
    vl_engine->icon_style = g_strdup("flag");
    vl_engine->flag_variant = g_strdup("us");
    vl_engine->restore_key = g_strdup("esc");
    vl_engine->theme = g_strdup("auto");
    vl_engine->charset = 0;
    vl_engine->toggle_mode = TOGGLE_BOTH;
    vl_engine->client_caps = 0;
    vl_engine->prev_surrounding[0] = '\0';
    vl_engine->raw_typed[0] = '\0';
    vl_engine->raw_typed_len = 0;
    vl_engine->last_bracket_key = 0;
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    vl_engine->grave_timer_id = 0;
    vl_engine->prop_list = NULL;
    vl_engine->status_prop = NULL;

    active_engines = g_list_append(active_engines, vl_engine);

    lotuskey_set_input_method(vl_engine->session, LOTUSKEY_INPUT_TELEX);
    ibus_lotus_load_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
}

static void ibus_lotus_engine_finalize(GObject *object) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)object;
    active_engines = g_list_remove(active_engines, vl_engine);
    ibus_lotus_cancel_grave_timer(vl_engine);
    if (vl_engine->output_mode) {
        g_free(vl_engine->output_mode);
        vl_engine->output_mode = NULL;
    }
    if (vl_engine->im_framework) {
        g_free(vl_engine->im_framework);
        vl_engine->im_framework = NULL;
    }
    if (vl_engine->ui_lang) {
        g_free(vl_engine->ui_lang);
        vl_engine->ui_lang = NULL;
    }
    if (vl_engine->icon_style) {
        g_free(vl_engine->icon_style);
        vl_engine->icon_style = NULL;
    }
    if (vl_engine->flag_variant) {
        g_free(vl_engine->flag_variant);
        vl_engine->flag_variant = NULL;
    }
    if (vl_engine->restore_key) {
        g_free(vl_engine->restore_key);
        vl_engine->restore_key = NULL;
    }
    if (vl_engine->theme) {
        g_free(vl_engine->theme);
        vl_engine->theme = NULL;
    }
    if (vl_engine->status_prop) {
        g_object_unref(vl_engine->status_prop);
        vl_engine->status_prop = NULL;
    }
    if (vl_engine->prop_list) {
        g_object_unref(vl_engine->prop_list);
        vl_engine->prop_list = NULL;
    }
    if (vl_engine->session) {
        lotuskey_destroy_session(vl_engine->session);
        vl_engine->session = NULL;
    }
    G_OBJECT_CLASS(ibus_lotus_engine_parent_class)->finalize(object);
}

static void ibus_lotus_engine_reset(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    ibus_lotus_engine_reset_internal(vl_engine);
    if (vl_engine->session) {
        lotuskey_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->reset(engine);
}

static void ibus_lotus_engine_enable(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    active_engines = g_list_remove(active_engines, vl_engine);
    active_engines = g_list_prepend(active_engines, vl_engine);
    const gchar *engine_name = ibus_engine_get_name(engine);
    if (engine_name && strstr(engine_name, "vni") != NULL) {
        vl_engine->is_vni = TRUE;
        vl_engine->input_method = IM_VNI;
        lotuskey_set_input_method(vl_engine->session, LOTUSKEY_INPUT_VNI);
    } else {
        vl_engine->is_vni = FALSE;
        vl_engine->input_method = IM_TELEX;
        lotuskey_set_input_method(vl_engine->session, LOTUSKEY_INPUT_TELEX);
    }
    ibus_lotus_load_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
    ibus_engine_register_properties(engine, vl_engine->prop_list);
    if (vl_engine->status_prop) {
        ibus_engine_update_property(engine, vl_engine->status_prop);
    }
    ibus_lotus_sni_notify_update();
    ibus_lotus_engine_reset_internal(vl_engine);
    if (vl_engine->session) {
        lotuskey_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->enable(engine);
}

static void ibus_lotus_engine_disable(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->is_password_field = FALSE;
    if (lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    } else {
        ibus_lotus_engine_reset_internal(vl_engine);
    }
    if (vl_engine->session) {
        lotuskey_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->disable(engine);
}

static void ibus_lotus_engine_focus_in(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    active_engines = g_list_remove(active_engines, vl_engine);
    active_engines = g_list_prepend(active_engines, vl_engine);
    ibus_lotus_load_user_config(vl_engine);
    guint purpose = IBUS_INPUT_PURPOSE_FREE_FORM;
    guint hints = IBUS_INPUT_HINT_NONE;
    ibus_engine_get_content_type(engine, &purpose, &hints);
    vl_engine->is_password_field = (purpose == IBUS_INPUT_PURPOSE_PASSWORD) ||
                                   (purpose == IBUS_INPUT_PURPOSE_PIN) ||
                                   (vl_engine->auto_disable_url_bar && purpose == IBUS_INPUT_PURPOSE_URL);
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    ibus_lotus_build_prop_list(vl_engine);
    ibus_engine_register_properties(engine, vl_engine->prop_list);
    if (vl_engine->status_prop) {
        ibus_engine_update_property(engine, vl_engine->status_prop);
    }
    ibus_lotus_sni_notify_update();
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->focus_in(engine);
}

static void ibus_lotus_engine_focus_out(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->is_password_field = FALSE;
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    ibus_lotus_cancel_grave_timer(vl_engine);
    if (lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    } else {
        ibus_lotus_engine_reset_internal(vl_engine);
    }
    if (vl_engine->session) {
        lotuskey_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->focus_out(engine);
}

static void ibus_lotus_engine_set_capabilities(IBusEngine *engine, guint caps) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->client_caps = caps;
    if (IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->set_capabilities) {
        IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->set_capabilities(engine, caps);
    }
}

static void ibus_lotus_engine_set_content_type(IBusEngine *engine, guint purpose, guint hints) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->is_password_field = (purpose == IBUS_INPUT_PURPOSE_PASSWORD) ||
                                   (purpose == IBUS_INPUT_PURPOSE_PIN) ||
                                   (vl_engine->auto_disable_url_bar && purpose == IBUS_INPUT_PURPOSE_URL);
    if (vl_engine->is_password_field && lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_engine_reset_internal(vl_engine);
    }
    if (IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->set_content_type) {
        IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->set_content_type(engine, purpose, hints);
    }
}

static gboolean ibus_lotus_try_spawn_verified_arg(const char *candidate, const char *arg1) {
    struct stat st;
    if (stat(candidate, &st) != 0) return FALSE;
    if (!S_ISREG(st.st_mode)) return FALSE;
    if (st.st_uid != getuid() && st.st_uid != 0 &&
        !g_str_has_prefix(candidate, "/nix/store/") &&
        !g_str_has_prefix(candidate, "/app/")) {
        return FALSE;
    }
    if (!g_file_test(candidate, G_FILE_TEST_IS_EXECUTABLE)) return FALSE;
    gchar *argv[] = { (gchar *)candidate, (gchar *)arg1, NULL };
    return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, NULL);
}

static void ibus_lotus_spawn_tool_arg(const char *tool_name, const char *arg1) {
    char self_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", self_path, sizeof(self_path) - 1);
    if (len > 0) {
        self_path[len] = '\0';
        gchar *bin_dir = g_path_get_dirname(self_path);
        gchar *sibling = g_build_filename(bin_dir, tool_name, NULL);
        if (ibus_lotus_try_spawn_verified_arg(sibling, arg1)) {
            g_free(sibling);
            g_free(bin_dir);
            return;
        }
        g_free(sibling);

        /* Also check ../../bin/<tool> and ../bin/<tool> relative to /proc/self/exe
         * (e.g. when engine is at $PREFIX/lib/lotuskey/ibus-engine-lotuskey on NixOS / Flatpak / /usr/local) */
        gchar *parent_dir = g_path_get_dirname(bin_dir);
        gchar *prefix_dir = g_path_get_dirname(parent_dir);
        gchar *prefix_bin = g_build_filename(prefix_dir, "bin", tool_name, NULL);
        gchar *parent_bin = g_build_filename(parent_dir, "bin", tool_name, NULL);
        g_free(bin_dir);
        g_free(parent_dir);
        g_free(prefix_dir);

        if (ibus_lotus_try_spawn_verified_arg(prefix_bin, arg1)) {
            g_free(prefix_bin);
            g_free(parent_bin);
            return;
        }
        g_free(prefix_bin);

        if (ibus_lotus_try_spawn_verified_arg(parent_bin, arg1)) {
            g_free(parent_bin);
            return;
        }
        g_free(parent_bin);
    }

    const gchar *home = g_get_home_dir();
    if (home) {
        gchar *local_bin = g_build_filename(home, ".local", "bin", tool_name, NULL);
        if (ibus_lotus_try_spawn_verified_arg(local_bin, arg1)) {
            g_free(local_bin);
            return;
        }
        g_free(local_bin);
    }

    gchar *usr_local_bin = g_build_filename("/usr/local/bin", tool_name, NULL);
    if (ibus_lotus_try_spawn_verified_arg(usr_local_bin, arg1)) {
        g_free(usr_local_bin);
        return;
    }
    g_free(usr_local_bin);

    gchar *usr_bin = g_build_filename("/usr/bin", tool_name, NULL);
    if (ibus_lotus_try_spawn_verified_arg(usr_bin, arg1)) {
        g_free(usr_bin);
        return;
    }
    g_free(usr_bin);

    gchar *path_bin = g_find_program_in_path(tool_name);
    if (path_bin) {
        ibus_lotus_try_spawn_verified_arg(path_bin, arg1);
        g_free(path_bin);
    }
}

static void ibus_lotus_spawn_tool(const char *tool_name) {
    ibus_lotus_spawn_tool_arg(tool_name, NULL);
}

static void ibus_lotus_engine_property_activate(IBusEngine *engine, const gchar *prop_name, guint prop_state) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    if (!prop_name || g_str_has_prefix(prop_name, "menu-")) {
        return;
    }
    if (g_strcmp0(prop_name, "lotus-setup") == 0) {
        ibus_lotus_spawn_tool("lotuskey-setup");
        return;
    } else if (g_strcmp0(prop_name, "lotus-clipboard-convert") == 0) {
        ibus_lotus_spawn_tool_arg("lotuskey-setup", "--converter");
        return;
    } else if (g_strcmp0(prop_name, "lotus-quick-menu") == 0) {
        ibus_lotus_spawn_tool("lotuskey-menu");
        return;
    } else if (g_strcmp0(prop_name, "InputMode") == 0 || g_strcmp0(prop_name, "lotus-status") == 0) {
        ibus_lotus_toggle_vietnamese(vl_engine);
        return;
    }

    /* For radio items, only act when selected (PROP_STATE_CHECKED) */
    if (g_str_has_prefix(prop_name, "im-") ||
        g_str_has_prefix(prop_name, "cs-") ||
        g_str_has_prefix(prop_name, "out-") ||
        g_str_has_prefix(prop_name, "icon-")) {
        if (prop_state != PROP_STATE_CHECKED) {
            return;
        }
        if (g_strcmp0(prop_name, "im-telex") == 0) {
            vl_engine->input_method = IM_TELEX;
            vl_engine->is_vni = FALSE;
            lotuskey_set_input_method(vl_engine->session, LOTUSKEY_INPUT_TELEX);
        } else if (g_strcmp0(prop_name, "im-vni") == 0) {
            vl_engine->input_method = IM_VNI;
            vl_engine->is_vni = TRUE;
            lotuskey_set_input_method(vl_engine->session, LOTUSKEY_INPUT_VNI);
        } else if (g_strcmp0(prop_name, "im-telex-vni") == 0) {
            vl_engine->input_method = IM_TELEX_VNI;
            vl_engine->is_vni = FALSE;
            lotuskey_set_input_method(vl_engine->session, LOTUSKEY_INPUT_TELEX);
        } else if (g_strcmp0(prop_name, "cs-unicode") == 0) {
            vl_engine->charset = LOTUS_CHARSET_UNICODE;
        } else if (g_strcmp0(prop_name, "cs-combining") == 0) {
            vl_engine->charset = LOTUS_CHARSET_COMBINING_CFG;
        } else if (g_strcmp0(prop_name, "cs-tcvn3") == 0) {
            vl_engine->charset = LOTUS_CHARSET_TCVN3_CFG;
        } else if (g_strcmp0(prop_name, "cs-vni-win") == 0) {
            vl_engine->charset = LOTUS_CHARSET_VNI_WIN_CFG;
        } else if (g_strcmp0(prop_name, "out-preedit") == 0) {
            g_free(vl_engine->output_mode);
            vl_engine->output_mode = g_strdup("preedit");
        } else if (g_strcmp0(prop_name, "out-surrounding") == 0) {
            g_free(vl_engine->output_mode);
            vl_engine->output_mode = g_strdup("surrounding");
        } else if (g_strcmp0(prop_name, "out-forward") == 0) {
            g_free(vl_engine->output_mode);
            vl_engine->output_mode = g_strdup("forward");
        } else if (g_strcmp0(prop_name, "icon-flag-us") == 0) {
            g_free(vl_engine->icon_style);
            g_free(vl_engine->flag_variant);
            vl_engine->icon_style = g_strdup("flag");
            vl_engine->flag_variant = g_strdup("us");
        } else if (g_strcmp0(prop_name, "icon-flag-uk") == 0) {
            g_free(vl_engine->icon_style);
            g_free(vl_engine->flag_variant);
            vl_engine->icon_style = g_strdup("flag");
            vl_engine->flag_variant = g_strdup("uk");
        } else if (g_strcmp0(prop_name, "icon-badge") == 0) {
            g_free(vl_engine->icon_style);
            vl_engine->icon_style = g_strdup("badge");
        } else if (g_strcmp0(prop_name, "icon-lotus") == 0) {
            g_free(vl_engine->icon_style);
            vl_engine->icon_style = g_strdup("lotus");
        } else if (g_strcmp0(prop_name, "icon-symbolic") == 0) {
            g_free(vl_engine->icon_style);
            vl_engine->icon_style = g_strdup("symbolic");
        }
    } else if (g_strcmp0(prop_name, "smart-bilingual") == 0) {
        vl_engine->smart_bilingual = (prop_state == PROP_STATE_CHECKED);
        lotuskey_set_smart_bilingual(vl_engine->session, vl_engine->smart_bilingual);
    } else if (g_strcmp0(prop_name, "modern-orthography") == 0) {
        vl_engine->modern_orthography = (prop_state == PROP_STATE_CHECKED);
        lotuskey_set_modern_orthography(vl_engine->session, vl_engine->modern_orthography);
    } else if (g_strcmp0(prop_name, "sen-flex") == 0) {
        vl_engine->sen_flex = (prop_state == PROP_STATE_CHECKED);
        lotuskey_set_grammar_profile(
            vl_engine->session,
            vl_engine->sen_flex ? LOTUSKEY_GRAMMAR_SEN_FLEX : LOTUSKEY_GRAMMAR_CLASSIC
        );
    } else if (g_strcmp0(prop_name, "macro-enabled") == 0) {
        vl_engine->macro_enabled = (prop_state == PROP_STATE_CHECKED);
    } else if (g_strcmp0(prop_name, "w2u") == 0) {
        vl_engine->w2u = (prop_state == PROP_STATE_CHECKED);
    }

    active_engines = g_list_remove(active_engines, vl_engine);
    active_engines = g_list_prepend(active_engines, vl_engine);
    ibus_lotus_save_user_config(vl_engine);
    ibus_lotus_reload_all_engines();
}

static void ibus_lotus_restore_raw_word(IBusLotusEngine *vl_engine) {
    IBusEngine *engine = (IBusEngine *)vl_engine;
    const char *raw = (vl_engine->raw_typed_len > 0)
        ? vl_engine->raw_typed
        : lotuskey_get_raw_text(vl_engine->session);
    char raw_buf[512];
    snprintf(raw_buf, sizeof(raw_buf), "%s", raw ? raw : "");

    if (!ibus_lotus_use_preedit_mode(vl_engine)) {
        if (raw_buf[0] != '\0') {
            ibus_lotus_sync_direct_output(vl_engine, raw_buf);
        }
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }

    ibus_lotus_clear_preedit(engine);
    if (raw_buf[0] != '\0') {
        IBusText *commit_text = ibus_text_new_from_string(raw_buf);
        ibus_engine_commit_text(engine, commit_text);
    }
    ibus_lotus_engine_reset_internal(vl_engine);
}

static gboolean ibus_lotus_engine_process_key_event(IBusEngine *engine, guint keyval, guint keycode, guint state) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    (void)keycode;

    gboolean is_release = (state & IBUS_RELEASE_MASK) != 0;

    /* Handle key release events (used for Ctrl+Shift chord detection) */
    if (is_release) {
        if (keyval == IBUS_KEY_Control_L || keyval == IBUS_KEY_Control_R ||
            keyval == IBUS_KEY_Shift_L || keyval == IBUS_KEY_Shift_R) {

            if (vl_engine->ctrl_pressed && vl_engine->shift_pressed && !vl_engine->other_key_in_chord) {
                if (vl_engine->toggle_mode == TOGGLE_CTRL_SHIFT || vl_engine->toggle_mode == TOGGLE_BOTH) {
                    ibus_lotus_toggle_vietnamese(vl_engine);
                }
            }

            if (keyval == IBUS_KEY_Control_L || keyval == IBUS_KEY_Control_R) {
                vl_engine->ctrl_pressed = FALSE;
            }
            if (keyval == IBUS_KEY_Shift_L || keyval == IBUS_KEY_Shift_R) {
                vl_engine->shift_pressed = FALSE;
            }
            if (!vl_engine->ctrl_pressed && !vl_engine->shift_pressed) {
                vl_engine->other_key_in_chord = FALSE;
            }
        }
        return FALSE;
    }

    /* Key Press Events: Update modifier trackers */
    if (keyval == IBUS_KEY_Control_L || keyval == IBUS_KEY_Control_R) {
        vl_engine->ctrl_pressed = TRUE;
        return FALSE;
    }
    if (keyval == IBUS_KEY_Shift_L || keyval == IBUS_KEY_Shift_R) {
        vl_engine->shift_pressed = TRUE;
        return FALSE;
    }

    if (vl_engine->ctrl_pressed || vl_engine->shift_pressed) {
        vl_engine->other_key_in_chord = TRUE;
    }

    /* If a pending grave (`) timer was waiting and user pressed another key:
     * Flush the buffered grave (`) immediately so typing `code` in Markdown/Terminal works seamlessly! */
    if (vl_engine->grave_timer_id != 0 && keyval != '`') {
        ibus_lotus_cancel_grave_timer(vl_engine);
        IBusText *grave_text = ibus_text_new_from_static_string("`");
        ibus_engine_commit_text(engine, grave_text);
    }

    /* Password / PIN / URL protection */
    if (vl_engine->is_password_field) {
        if (lotuskey_is_composing(vl_engine->session)) {
            ibus_lotus_engine_reset_internal(vl_engine);
        }
        return FALSE;
    }

    /* Pure modifier keys: CapsLock, ShiftLock, Level3 */
    if (keyval == IBUS_KEY_Caps_Lock || keyval == IBUS_KEY_Shift_Lock ||
        keyval == IBUS_KEY_ISO_Level3_Shift) {
        return FALSE;
    }

    /* Hotkey Alt + Z: Toggle VN/EN */
    if ((state & IBUS_MOD1_MASK) && (keyval == 'z' || keyval == 'Z')) {
        if (vl_engine->toggle_mode == TOGGLE_ALT_Z || vl_engine->toggle_mode == TOGGLE_BOTH) {
            ibus_lotus_toggle_vietnamese(vl_engine);
            return TRUE;
        }
    }

    /* Hotkey Shift + Space: Toggle VN/EN */
    if ((state & IBUS_SHIFT_MASK) && (keyval == IBUS_KEY_space || keyval == ' ')) {
        if (vl_engine->toggle_mode == TOGGLE_SHIFT_SPACE) {
            ibus_lotus_toggle_vietnamese(vl_engine);
            return TRUE;
        }
    }

    /* Pass through system hotkeys (Ctrl, Alt, Super/Win) */
    if (state & (IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_SUPER_MASK)) {
        if (lotuskey_is_composing(vl_engine->session)) {
            ibus_lotus_commit_composing(vl_engine, NULL);
        }
        return FALSE;
    }

    /* Word Restore Key: Esc or Shift+Backspace restores composing Vietnamese syllable to raw ASCII */
    if (lotuskey_is_composing(vl_engine->session) && vl_engine->restore_key) {
        if (g_strcmp0(vl_engine->restore_key, "esc") == 0 &&
            (keyval == IBUS_KEY_Escape || keyval == 0x1b)) {
            ibus_lotus_restore_raw_word(vl_engine);
            return TRUE;
        }
        if (g_strcmp0(vl_engine->restore_key, "shift_backspace") == 0 &&
            keyval == IBUS_KEY_BackSpace && (state & IBUS_SHIFT_MASK)) {
            ibus_lotus_restore_raw_word(vl_engine);
            return TRUE;
        }
    }

    /* Navigation & action keys: commit active word first */
    if (keyval == IBUS_KEY_Return || keyval == IBUS_KEY_KP_Enter || keyval == IBUS_KEY_Linefeed ||
        keyval == IBUS_KEY_Tab || keyval == IBUS_KEY_ISO_Left_Tab || keyval == IBUS_KEY_KP_Tab ||
        keyval == IBUS_KEY_Delete || keyval == IBUS_KEY_KP_Delete ||
        keyval == IBUS_KEY_Escape ||
        keyval == '\r' || keyval == '\n' || keyval == '\t' || keyval == 0x1b ||
        (keyval >= IBUS_KEY_Home && keyval <= IBUS_KEY_Insert) ||
        (keyval >= IBUS_KEY_KP_Home && keyval <= IBUS_KEY_KP_Delete)) {
        if (lotuskey_is_composing(vl_engine->session)) {
            ibus_lotus_commit_composing(vl_engine, NULL);
        }
        if (vl_engine->session) {
            lotuskey_append_context(vl_engine->session, "");
        }
        return FALSE;
    }

    /* Handle BackSpace */
    if (keyval == IBUS_KEY_BackSpace) {
        if (lotuskey_is_composing(vl_engine->session)) {
            ibus_lotus_backspace_composing(vl_engine);
            return TRUE;
        }
        if (!vl_engine->enabled && vl_engine->raw_typed_len > 0) {
            ibus_lotus_pop_raw_typed(vl_engine);
        }
        lotuskey_reset_session(vl_engine->session);
        return FALSE;
    }

    /* Handle Grave Key ` to open Quick Menu (with 220ms debounce so double-tap `` types ` without losing focus) */
    if (keyval == '`' && vl_engine->grave_menu_enabled && !lotuskey_is_composing(vl_engine->session)) {
        if (vl_engine->grave_timer_id != 0) {
            /* Second press within 220ms: cancel menu launch and pass literal ` to app */
            ibus_lotus_cancel_grave_timer(vl_engine);
            return FALSE;
        }
        vl_engine->grave_timer_id = g_timeout_add(220, ibus_lotus_grave_timeout_cb, vl_engine);
        return TRUE;
    }

    /* If Vietnamese is disabled, support optional macro expansion in OFF mode or pass through */
    if (!vl_engine->enabled) {
        if (vl_engine->macro_enabled && vl_engine->macro_in_off_mode && g_macro_table.count > 0) {
            if ((keyval >= 'a' && keyval <= 'z') || (keyval >= 'A' && keyval <= 'Z') || (keyval >= '0' && keyval <= '9')) {
                ibus_lotus_append_raw_typed(vl_engine, (char)keyval);
                return FALSE;
            }
            if (keyval == ' ' && vl_engine->raw_typed_len > 0) {
                char expanded[512];
                int auto_cap = vl_engine->auto_capitalize_macro ? 1 : 0;
                if (lotus_macro_lookup_ex(&g_macro_table, vl_engine->raw_typed, auto_cap, expanded, sizeof(expanded))) {
                    size_t del_n = vl_engine->raw_typed_len;
                    vl_engine->raw_typed[0] = '\0';
                    vl_engine->raw_typed_len = 0;
                    if (vl_engine->client_caps & IBUS_CAP_SURROUNDING_TEXT) {
                        ibus_engine_delete_surrounding_text(engine, -(gint)del_n, (guint)del_n);
                    } else {
                        for (size_t i = 0; i < del_n; i++) {
                            ibus_engine_forward_key_event(engine, IBUS_KEY_BackSpace, 14, 0);
                            ibus_engine_forward_key_event(engine, IBUS_KEY_BackSpace, 14, IBUS_RELEASE_MASK);
                        }
                    }
                    char converted[1024];
                    lotus_convert_charset(expanded, vl_engine->charset, converted, sizeof(converted));
                    char out_space[1028];
                    snprintf(out_space, sizeof(out_space), "%s ", converted);
                    IBusText *commit_text = ibus_text_new_from_string(out_space);
                    ibus_engine_commit_text(engine, commit_text);
                    return TRUE;
                }
            }
            vl_engine->raw_typed[0] = '\0';
            vl_engine->raw_typed_len = 0;
        }
        return FALSE;
    }

    /* Handle Bracket transforms '[' -> 'ơ', ']' -> 'ư', '{' -> 'Ơ', '}' -> 'Ư'
     * Feeds 'ow' / 'uw' directly into the active syllable so h[n -> hơn, t]s -> tứ, [[ -> [ */
    if (vl_engine->bracket_transform && !vl_engine->is_vni &&
        (keyval == '[' || keyval == ']' || keyval == '{' || keyval == '}')) {
        if (vl_engine->last_bracket_key == (char)keyval && lotuskey_is_composing(vl_engine->session)) {
            /* Double bracket (e.g. [[ or ]]): revert the ơ/ư and commit literal bracket */
            vl_engine->last_bracket_key = 0;
            ibus_lotus_backspace_composing(vl_engine);
            char trail[2] = { (char)keyval, '\0' };
            ibus_lotus_commit_composing(vl_engine, trail);
            return TRUE;
        }
        vl_engine->last_bracket_key = (char)keyval;
        ibus_lotus_append_raw_typed(vl_engine, (char)keyval);
        char base_vowel = (keyval == '[' || keyval == ']') ? ((keyval == '[') ? 'o' : 'u')
                                                           : ((keyval == '{') ? 'O' : 'U');
        char horn_key = (keyval == '[' || keyval == ']') ? 'w' : 'W';
        lotuskey_feed_char(vl_engine->session, (uint32_t)base_vowel);
        lotuskey_feed_char(vl_engine->session, (uint32_t)horn_key);
        ibus_lotus_update_preedit(vl_engine);
        return TRUE;
    }
    vl_engine->last_bracket_key = 0;

    /* Handle W2U option: If w2u is disabled, typing 'w' or 'W' at start of word should NOT turn into 'ư'/'Ư',
     * while keeping 'w' inside the composing buffer so English words like "water"/"window" stay intact! */
    if (!vl_engine->w2u && !vl_engine->is_vni && (keyval == 'w' || keyval == 'W') && !lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_append_raw_typed(vl_engine, (char)keyval);
        lotuskey_feed_char(vl_engine->session, keyval);
        lotuskey_feed_char(vl_engine->session, keyval);
        ibus_lotus_update_preedit(vl_engine);
        return TRUE;
    }

    /* Handle printable ASCII characters (32..126) */
    if (keyval >= 32 && keyval < 127) {
        char orig_ascii = (char)keyval;
        gboolean is_alpha = (keyval >= 'a' && keyval <= 'z') || (keyval >= 'A' && keyval <= 'Z');
        gboolean is_digit = (keyval >= '0' && keyval <= '9');

        /* Hybrid Telex + VNI support: translate digit keys when composing */
        if (vl_engine->input_method == IM_TELEX_VNI && is_digit && lotuskey_is_composing(vl_engine->session)) {
            char mapped_telex = ibus_lotus_translate_vni_digit_for_hybrid(vl_engine, keyval);
            if (mapped_telex != 0) {
                keyval = (guint)mapped_telex;
                is_alpha = TRUE;
                is_digit = FALSE;
            }
        }

        gboolean is_word_char = is_alpha || (vl_engine->is_vni && is_digit && lotuskey_is_composing(vl_engine->session));

        if (!is_word_char) {
            if (lotuskey_is_composing(vl_engine->session)) {
                if (keyval == '(' || keyval == '[' || keyval == '{') {
                    lotuskey_feed_char(vl_engine->session, keyval);
                    const char *committed = lotuskey_get_last_text(vl_engine->session);
                    char converted[1024];
                    lotus_convert_charset(committed ? committed : "", vl_engine->charset, converted, sizeof(converted));
                    char buf[1028];
                    snprintf(buf, sizeof(buf), "%s%c", converted, (char)keyval);
                    IBusText *commit_text = ibus_text_new_from_string(buf);
                    ibus_engine_commit_text(engine, commit_text);
                    ibus_lotus_engine_reset_internal(vl_engine);
                    return TRUE;
                }
                char trail[2] = { (char)keyval, '\0' };
                ibus_lotus_commit_composing(vl_engine, trail);
                return TRUE;
            } else {
                lotuskey_feed_char(vl_engine->session, keyval);
                return FALSE;
            }
        }

        /* Auto-flush preedit before buffer overflow */
        if (lotuskey_is_composing(vl_engine->session)) {
            const char *raw_check = lotuskey_get_raw_text(vl_engine->session);
            const char *comp_check = lotuskey_get_composing_text(vl_engine->session);
            if ((raw_check && strlen(raw_check) >= 48) || (comp_check && strlen(comp_check) >= 48)) {
                ibus_lotus_commit_composing(vl_engine, NULL);
            }
        }

        ibus_lotus_append_raw_typed(vl_engine, orig_ascii);

        /* Telex stop-coda and tone corrections */
        if (!vl_engine->is_vni && lotuskey_is_composing(vl_engine->session)) {
            char lower_key = vl_tolower((char)keyval);
            uint8_t key_tone = ibus_lotus_telex_tone_for_key(lower_key);
            const char *raw_before = lotuskey_get_raw_text(vl_engine->session);
            const char *comp_before = lotuskey_get_composing_text(vl_engine->session);
            if (key_tone > 0 && raw_before && comp_before && ibus_lotus_has_non_ascii(comp_before)) {
                size_t rlen = strlen(raw_before);
                size_t clen = strlen(comp_before);
                uint8_t active_tone = ibus_lotus_active_tone_of_utf8(comp_before);

                if (vl_engine->replayed_after_backspace &&
                    active_tone == key_tone && rlen > 0 && vl_tolower(raw_before[rlen - 1]) != lower_key) {
                    char canon_raw[1024];
                    ibus_lotus_raw_keys_for_utf8(comp_before, FALSE, canon_raw, sizeof(canon_raw));
                    ibus_lotus_replay_raw_keys(vl_engine, canon_raw);
                    ibus_lotus_update_preedit(vl_engine);
                    return TRUE;
                }

                if ((key_tone == 2 || key_tone == 5) && active_tone == 0 && rlen >= 3 && clen >= 3 && rlen < 512) {
                    char last_r = vl_tolower(raw_before[rlen - 1]);
                    char prev_c = vl_tolower(comp_before[clen - 2]);
                    if ((last_r == 'f' || last_r == 'r' || last_r == 'x') &&
                        vl_tolower(comp_before[clen - 1]) == last_r &&
                        (prev_c == 't' || prev_c == 'c' || prev_c == 'p' || prev_c == 'h')) {
                        char fixed_raw[512];
                        memcpy(fixed_raw, raw_before, rlen);
                        fixed_raw[rlen - 1] = (char)keyval;
                        fixed_raw[rlen] = '\0';
                        ibus_lotus_replay_raw_keys(vl_engine, fixed_raw);
                        ibus_lotus_update_preedit(vl_engine);
                        return TRUE;
                    }
                }
            }
        }

        int32_t action = lotuskey_feed_char(vl_engine->session, keyval);

        if (!vl_engine->is_vni && lotuskey_is_composing(vl_engine->session)) {
            char lower_key = vl_tolower((char)keyval);
            if (lower_key == 'a' || lower_key == 'e' || lower_key == 'o') {
                const char *raw_after = lotuskey_get_raw_text(vl_engine->session);
                const char *comp_after = lotuskey_get_composing_text(vl_engine->session);
                if (raw_after && comp_after) {
                    size_t rlen = strlen(raw_after);
                    size_t clen = strlen(comp_after);
                    if (rlen >= 3 && rlen < 512 && clen >= 2 &&
                        vl_tolower(raw_after[rlen - 1]) == lower_key &&
                        vl_tolower(raw_after[rlen - 3]) == lower_key &&
                        vl_tolower(comp_after[clen - 1]) == lower_key) {
                        uint8_t mid_tone = ibus_lotus_telex_tone_for_key(vl_tolower(raw_after[rlen - 2]));
                        gboolean allow_swap = (mid_tone == 5) ||
                            (mid_tone > 0 && lower_key == 'e' && rlen >= 4 &&
                             (vl_tolower(raw_after[rlen - 4]) == 'i' || vl_tolower(raw_after[rlen - 4]) == 'y') &&
                             vl_tolower(raw_after[0]) != 'p') ||
                            (mid_tone > 0 && lower_key == 'o' && rlen >= 4 &&
                             vl_tolower(raw_after[rlen - 4]) == 'u');
                        if (allow_swap && ibus_lotus_active_tone_of_utf8(comp_after) == mid_tone) {
                            char swapped_raw[512];
                            memcpy(swapped_raw, raw_after, rlen + 1);
                            char tmp = swapped_raw[rlen - 2];
                            swapped_raw[rlen - 2] = swapped_raw[rlen - 1];
                            swapped_raw[rlen - 1] = tmp;
                            ibus_lotus_replay_raw_keys(vl_engine, swapped_raw);
                        }
                    }
                }
            }
        }

        if (action == LOTUSKEY_ACTION_COMMIT) {
            const char *committed = lotuskey_get_last_text(vl_engine->session);
            char converted[1024];
            lotus_convert_charset(committed ? committed : "", vl_engine->charset, converted, sizeof(converted));
            if (converted[0] != '\0') {
                IBusText *commit_text = ibus_text_new_from_string(converted);
                ibus_engine_commit_text(engine, commit_text);
            }
            ibus_lotus_engine_reset_internal(vl_engine);
            return TRUE;
        } else if (lotuskey_is_composing(vl_engine->session) ||
                   action == LOTUSKEY_ACTION_REPLACE ||
                   action == LOTUSKEY_ACTION_CONSUMED) {
            ibus_lotus_update_preedit(vl_engine);
            return TRUE;
        }
        return FALSE;
    }

    if (lotuskey_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    }
    return FALSE;
}

static void ibus_lotus_engine_class_init(IBusLotusEngineClass *klass) {
    GObjectClass *object_class = G_OBJECT_CLASS(klass);
    IBusEngineClass *engine_class = IBUS_ENGINE_CLASS(klass);

    object_class->finalize = ibus_lotus_engine_finalize;

    engine_class->reset = ibus_lotus_engine_reset;
    engine_class->enable = ibus_lotus_engine_enable;
    engine_class->disable = ibus_lotus_engine_disable;
    engine_class->focus_in = ibus_lotus_engine_focus_in;
    engine_class->focus_out = ibus_lotus_engine_focus_out;
    engine_class->set_capabilities = ibus_lotus_engine_set_capabilities;
    engine_class->set_content_type = ibus_lotus_engine_set_content_type;
    engine_class->property_activate = ibus_lotus_engine_property_activate;
    engine_class->process_key_event = ibus_lotus_engine_process_key_event;
}

/* ============================================================================
 * Native StatusNotifierItem (SNI) & DBusMenu Tray Indicator
 * Renders the 100% flat SVG flag icon (lotuskey-flag-vn/us/uk.svg) directly
 * on Ubuntu GNOME Top Bar (ubuntu-appindicators), KDE Plasma, XFCE, Waybar.
 * ============================================================================ */
static GDBusConnection *g_sni_conn = NULL;
static guint32 g_sni_menu_revision = 1;
static gboolean g_sni_fallback_enabled = TRUE;
static gint g_sni_fallback_im = IM_TELEX;
static gint g_sni_fallback_charset = LOTUS_CHARSET_UNICODE;
static gboolean g_sni_fallback_smart_bilingual = TRUE;
static gboolean g_sni_fallback_modern_orthography = TRUE;
static gboolean g_sni_fallback_sen_flex = TRUE;
static gboolean g_sni_fallback_macro_enabled = TRUE;
static gboolean g_sni_fallback_w2u = TRUE;
static gchar *g_sni_fallback_output_mode = NULL;
static gchar *g_sni_fallback_icon_style = NULL;
static gchar *g_sni_fallback_flag_var = NULL;
static gchar *g_sni_fallback_lang = NULL;

static void sni_sync_fallback_from_config(void) {
    if (active_engines != NULL) {
        IBusLotusEngine *vl = (IBusLotusEngine *)active_engines->data;
        g_sni_fallback_enabled = vl->enabled;
        g_sni_fallback_im = vl->input_method;
        g_sni_fallback_charset = vl->charset;
        g_sni_fallback_smart_bilingual = vl->smart_bilingual;
        g_sni_fallback_modern_orthography = vl->modern_orthography;
        g_sni_fallback_sen_flex = vl->sen_flex;
        g_sni_fallback_macro_enabled = vl->macro_enabled;
        g_sni_fallback_w2u = vl->w2u;
        g_free(g_sni_fallback_output_mode);
        g_sni_fallback_output_mode = g_strdup(vl->output_mode ? vl->output_mode : "preedit");
        g_free(g_sni_fallback_icon_style);
        g_sni_fallback_icon_style = g_strdup(vl->icon_style ? vl->icon_style : "flag");
        g_free(g_sni_fallback_flag_var);
        g_sni_fallback_flag_var = g_strdup(vl->flag_variant ? vl->flag_variant : "us");
        g_free(g_sni_fallback_lang);
        g_sni_fallback_lang = g_strdup(vl->ui_lang ? vl->ui_lang : "vi");
        return;
    }
    IBusLotusEngine tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.session = lotuskey_create_session();
    tmp.enabled = TRUE;
    tmp.input_method = IM_TELEX;
    tmp.charset = LOTUS_CHARSET_UNICODE;
    tmp.smart_bilingual = TRUE;
    tmp.sen_flex = TRUE;
    tmp.modern_orthography = TRUE;
    tmp.w2u = TRUE;
    tmp.bracket_transform = TRUE;
    tmp.macro_enabled = TRUE;
    tmp.auto_capitalize_macro = TRUE;
    tmp.per_app_remember = TRUE;
    tmp.auto_disable_url_bar = TRUE;
    tmp.compact_mode = TRUE;
    tmp.autostart = TRUE;
    tmp.grave_menu_enabled = TRUE;
    tmp.output_mode = g_strdup("preedit");
    tmp.im_framework = g_strdup("auto");
    tmp.icon_style = g_strdup("flag");
    tmp.flag_variant = g_strdup("us");
    tmp.ui_lang = g_strdup("vi");
    ibus_lotus_load_user_config(&tmp);
    g_sni_fallback_enabled = tmp.enabled;
    g_sni_fallback_im = tmp.input_method;
    g_sni_fallback_charset = tmp.charset;
    g_sni_fallback_smart_bilingual = tmp.smart_bilingual;
    g_sni_fallback_modern_orthography = tmp.modern_orthography;
    g_sni_fallback_sen_flex = tmp.sen_flex;
    g_sni_fallback_macro_enabled = tmp.macro_enabled;
    g_sni_fallback_w2u = tmp.w2u;
    g_free(g_sni_fallback_output_mode);
    g_sni_fallback_output_mode = g_strdup(tmp.output_mode ? tmp.output_mode : "preedit");
    g_free(g_sni_fallback_icon_style);
    g_sni_fallback_icon_style = g_strdup(tmp.icon_style ? tmp.icon_style : "flag");
    g_free(g_sni_fallback_flag_var);
    g_sni_fallback_flag_var = g_strdup(tmp.flag_variant ? tmp.flag_variant : "us");
    g_free(g_sni_fallback_lang);
    g_sni_fallback_lang = g_strdup(tmp.ui_lang ? tmp.ui_lang : "vi");
    g_free(tmp.output_mode);
    g_free(tmp.im_framework);
    g_free(tmp.ui_lang);
    g_free(tmp.icon_style);
    g_free(tmp.flag_variant);
    g_free(tmp.restore_key);
    g_free(tmp.theme);
    if (tmp.session) lotuskey_destroy_session(tmp.session);
}

static gchar *sni_get_current_icon_path(void) {
    if (active_engines != NULL) {
        return ibus_lotus_resolve_status_icon_path((IBusLotusEngine *)active_engines->data);
    }
    sni_sync_fallback_from_config();
    IBusLotusEngine tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.enabled = g_sni_fallback_enabled;
    tmp.icon_style = g_sni_fallback_icon_style;
    tmp.flag_variant = g_sni_fallback_flag_var;
    return ibus_lotus_resolve_status_icon_path(&tmp);
}

static gboolean sni_is_action_item_id(gint id) {
    return (id == 1 ||
            (id >= 10 && id <= 12) ||
            (id >= 21 && id <= 23) ||
            (id >= 31 && id <= 34) ||
            (id >= 41 && id <= 45) ||
            (id >= 51 && id <= 53) ||
            (id >= 61 && id <= 65));
}

static void sni_mutate_engine_for_item(IBusLotusEngine *vl, gint item_id) {
    switch (item_id) {
        case 21:
            vl->input_method = IM_TELEX;
            vl->is_vni = FALSE;
            if (vl->session) lotuskey_set_input_method(vl->session, LOTUSKEY_INPUT_TELEX);
            break;
        case 22:
            vl->input_method = IM_VNI;
            vl->is_vni = TRUE;
            if (vl->session) lotuskey_set_input_method(vl->session, LOTUSKEY_INPUT_VNI);
            break;
        case 23:
            vl->input_method = IM_TELEX_VNI;
            vl->is_vni = FALSE;
            if (vl->session) lotuskey_set_input_method(vl->session, LOTUSKEY_INPUT_TELEX);
            break;
        case 31:
            vl->charset = LOTUS_CHARSET_UNICODE;
            break;
        case 32:
            vl->charset = LOTUS_CHARSET_COMBINING_CFG;
            break;
        case 33:
            vl->charset = LOTUS_CHARSET_TCVN3_CFG;
            break;
        case 34:
            vl->charset = LOTUS_CHARSET_VNI_WIN_CFG;
            break;
        case 41:
            vl->smart_bilingual = !vl->smart_bilingual;
            if (vl->session) lotuskey_set_smart_bilingual(vl->session, vl->smart_bilingual);
            break;
        case 42:
            vl->modern_orthography = !vl->modern_orthography;
            if (vl->session) lotuskey_set_modern_orthography(vl->session, vl->modern_orthography);
            break;
        case 43:
            vl->sen_flex = !vl->sen_flex;
            if (vl->session) {
                lotuskey_set_grammar_profile(
                    vl->session,
                    vl->sen_flex ? LOTUSKEY_GRAMMAR_SEN_FLEX : LOTUSKEY_GRAMMAR_CLASSIC
                );
            }
            break;
        case 44:
            vl->macro_enabled = !vl->macro_enabled;
            break;
        case 45:
            vl->w2u = !vl->w2u;
            break;
        case 51:
            g_free(vl->output_mode);
            vl->output_mode = g_strdup("preedit");
            break;
        case 52:
            g_free(vl->output_mode);
            vl->output_mode = g_strdup("surrounding");
            break;
        case 53:
            g_free(vl->output_mode);
            vl->output_mode = g_strdup("forward");
            break;
        case 61:
            g_free(vl->icon_style);
            g_free(vl->flag_variant);
            vl->icon_style = g_strdup("flag");
            vl->flag_variant = g_strdup("us");
            break;
        case 62:
            g_free(vl->icon_style);
            g_free(vl->flag_variant);
            vl->icon_style = g_strdup("flag");
            vl->flag_variant = g_strdup("uk");
            break;
        case 63:
            g_free(vl->icon_style);
            vl->icon_style = g_strdup("badge");
            break;
        case 64:
            g_free(vl->icon_style);
            vl->icon_style = g_strdup("lotus");
            break;
        case 65:
            g_free(vl->icon_style);
            vl->icon_style = g_strdup("symbolic");
            break;
        default:
            break;
    }
}

static void sni_apply_menu_action(gint item_id) {
    if (item_id == 10) {
        ibus_lotus_spawn_tool_arg("lotuskey-setup", "--converter");
        return;
    }
    if (item_id == 11) {
        ibus_lotus_spawn_tool("lotuskey-menu");
        return;
    }
    if (item_id == 12) {
        ibus_lotus_spawn_tool("lotuskey-setup");
        return;
    }

    if (active_engines != NULL) {
        IBusLotusEngine *vl = (IBusLotusEngine *)active_engines->data;
        if (item_id == 1) {
            ibus_lotus_toggle_vietnamese(vl);
            return;
        }
        sni_mutate_engine_for_item(vl, item_id);
        ibus_lotus_save_user_config(vl);
        ibus_lotus_reload_all_engines();
        return;
    }

    /* Fallback if no engine instance has been focused yet */
    IBusLotusEngine tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.session = lotuskey_create_session();
    tmp.enabled = TRUE;
    tmp.input_method = IM_TELEX;
    tmp.charset = LOTUS_CHARSET_UNICODE;
    tmp.smart_bilingual = TRUE;
    tmp.sen_flex = TRUE;
    tmp.modern_orthography = TRUE;
    tmp.w2u = TRUE;
    tmp.bracket_transform = TRUE;
    tmp.macro_enabled = TRUE;
    tmp.auto_capitalize_macro = TRUE;
    tmp.per_app_remember = TRUE;
    tmp.auto_disable_url_bar = TRUE;
    tmp.compact_mode = TRUE;
    tmp.autostart = TRUE;
    tmp.grave_menu_enabled = TRUE;
    tmp.output_mode = g_strdup("preedit");
    tmp.im_framework = g_strdup("auto");
    tmp.ui_lang = g_strdup("vi");
    tmp.icon_style = g_strdup("flag");
    tmp.flag_variant = g_strdup("us");
    tmp.restore_key = g_strdup("esc");
    tmp.theme = g_strdup("auto");
    ibus_lotus_load_user_config(&tmp);
    if (item_id == 1) {
        tmp.enabled = !tmp.enabled;
    } else {
        sni_mutate_engine_for_item(&tmp, item_id);
    }
    ibus_lotus_save_user_config(&tmp);
    g_free(tmp.output_mode);
    g_free(tmp.im_framework);
    g_free(tmp.ui_lang);
    g_free(tmp.icon_style);
    g_free(tmp.flag_variant);
    g_free(tmp.restore_key);
    g_free(tmp.theme);
    if (tmp.session) lotuskey_destroy_session(tmp.session);
    ibus_lotus_sni_notify_update();
}

static void sni_fill_menu_item_props(gint id, GVariantBuilder *props) {
    gboolean is_en = (g_sni_fallback_lang && strcmp(g_sni_fallback_lang, "en") == 0);
    const char *st = g_sni_fallback_icon_style ? g_sni_fallback_icon_style : "flag";
    const char *fv = g_sni_fallback_flag_var ? g_sni_fallback_flag_var : "us";
    const char *out_m = g_sni_fallback_output_mode ? g_sni_fallback_output_mode : "preedit";

    if (id == 0) {
        g_variant_builder_add(props, "{sv}", "children-display", g_variant_new_string("submenu"));
        return;
    }
    if (id == 100 || id == 101) {
        g_variant_builder_add(props, "{sv}", "type", g_variant_new_string("separator"));
        g_variant_builder_add(props, "{sv}", "visible", g_variant_new_boolean(TRUE));
        return;
    }

    gboolean is_cs_comb = (g_sni_fallback_charset == LOTUS_CHARSET_COMBINING_CFG || g_sni_fallback_charset == LOTUS_CHARSET_COMBINING_ENUM);
    gboolean is_cs_tcvn = (g_sni_fallback_charset == LOTUS_CHARSET_TCVN3_CFG || g_sni_fallback_charset == LOTUS_CHARSET_TCVN3_ENUM);
    gboolean is_cs_vni  = (g_sni_fallback_charset == LOTUS_CHARSET_VNI_WIN_CFG || g_sni_fallback_charset == LOTUS_CHARSET_VNI_WIN_ENUM);
    gboolean is_cs_uni  = (!is_cs_comb && !is_cs_tcvn && !is_cs_vni);

    gboolean is_out_surr = (strcmp(out_m, "surrounding") == 0);
    gboolean is_out_fwd  = (strcmp(out_m, "forward") == 0);
    gboolean is_out_pre  = (!is_out_surr && !is_out_fwd);

    gboolean ic_flag_us = (strcmp(st, "flag") == 0 && strcmp(fv, "uk") != 0);
    gboolean ic_flag_uk = (strcmp(st, "flag") == 0 && strcmp(fv, "uk") == 0);
    gboolean ic_badge   = (strcmp(st, "badge") == 0);
    gboolean ic_lotus   = (strcmp(st, "lotus") == 0);
    gboolean ic_symb    = (strcmp(st, "symbolic") == 0);

    char label_buf[128] = {0};
    const char *label = label_buf;
    const char *toggle_type = NULL;
    gboolean checked = FALSE;
    gboolean is_submenu_parent = FALSE;

    switch (id) {
        case 1:
            label = is_en
                ? (g_sni_fallback_enabled ? "Vietnamese: ON (Click to switch EN)" : "English: OFF (Click to switch VN)")
                : (g_sni_fallback_enabled ? "Tiếng Việt: BẬT (Click chuyển Anh)" : "Tiếng Anh: TẮT (Click chuyển Việt)");
            toggle_type = "checkmark";
            checked = g_sni_fallback_enabled;
            break;
        /* Submenu 20: Input Method */
        case 20: {
            const char *im_s = (g_sni_fallback_im == IM_VNI) ? "VNI" : ((g_sni_fallback_im == IM_TELEX_VNI) ? "Telex+VNI" : "Telex");
            snprintf(label_buf, sizeof(label_buf), "%s: %s", is_en ? "Input Method" : "Kiểu gõ", im_s);
            is_submenu_parent = TRUE;
            break;
        }
        case 21:
            label = "Telex";
            toggle_type = "radio";
            checked = (g_sni_fallback_im == IM_TELEX);
            break;
        case 22:
            label = "VNI";
            toggle_type = "radio";
            checked = (g_sni_fallback_im == IM_VNI);
            break;
        case 23:
            label = "Telex + VNI";
            toggle_type = "radio";
            checked = (g_sni_fallback_im == IM_TELEX_VNI);
            break;
        /* Submenu 30: Charset */
        case 30: {
            const char *cs_s = is_en
                ? (is_cs_comb ? "Combining" : (is_cs_tcvn ? "TCVN3" : (is_cs_vni ? "VNI Win" : "Unicode")))
                : (is_cs_comb ? "Tổ hợp" : (is_cs_tcvn ? "TCVN3" : (is_cs_vni ? "VNI Win" : "Unicode")));
            snprintf(label_buf, sizeof(label_buf), "%s: %s", is_en ? "Charset" : "Bảng mã", cs_s);
            is_submenu_parent = TRUE;
            break;
        }
        case 31:
            label = is_en ? "Unicode (Precomposed NFC)" : "Unicode dựng sẵn (NFC)";
            toggle_type = "radio";
            checked = is_cs_uni;
            break;
        case 32:
            label = is_en ? "Unicode (Combining NFD)" : "Unicode tổ hợp (NFD)";
            toggle_type = "radio";
            checked = is_cs_comb;
            break;
        case 33:
            label = "TCVN3 (ABC)";
            toggle_type = "radio";
            checked = is_cs_tcvn;
            break;
        case 34:
            label = "VNI Windows";
            toggle_type = "radio";
            checked = is_cs_vni;
            break;
        /* Submenu 40: Typing Options */
        case 40:
            label = is_en ? "Typing Options" : "Tùy chọn gõ";
            is_submenu_parent = TRUE;
            break;
        case 41:
            label = is_en ? "Auto-restore English words" : "Tự khôi phục từ tiếng Anh";
            toggle_type = "checkmark";
            checked = g_sni_fallback_smart_bilingual;
            break;
        case 42:
            label = is_en ? "Modern tone placement (oà, uý)" : "Đặt dấu kiểu mới (oà, uý)";
            toggle_type = "checkmark";
            checked = g_sni_fallback_modern_orthography;
            break;
        case 43:
            label = is_en ? "Free tone marking (SEN Flex)" : "Bỏ dấu tự do (SEN Flex)";
            toggle_type = "checkmark";
            checked = g_sni_fallback_sen_flex;
            break;
        case 44:
            label = is_en ? "Enable Macros (Shortcuts)" : "Bật gõ tắt (Macro)";
            toggle_type = "checkmark";
            checked = g_sni_fallback_macro_enabled;
            break;
        case 45:
            label = is_en ? "Convert initial W to Ư" : "Đổi W thành Ư ở đầu từ";
            toggle_type = "checkmark";
            checked = g_sni_fallback_w2u;
            break;
        /* Submenu 50: Output Mode */
        case 50: {
            const char *out_s = is_out_surr ? "Surrounding" : (is_out_fwd ? "Forward" : "Pre-edit");
            snprintf(label_buf, sizeof(label_buf), "%s: %s", is_en ? "Output Mode" : "Chế độ xuất chữ", out_s);
            is_submenu_parent = TRUE;
            break;
        }
        case 51:
            label = is_en ? "Pre-edit (Recommended)" : "Pre-edit (Mặc định)";
            toggle_type = "radio";
            checked = is_out_pre;
            break;
        case 52:
            label = "Surrounding Text";
            toggle_type = "radio";
            checked = is_out_surr;
            break;
        case 53:
            label = "Forward Backspace";
            toggle_type = "radio";
            checked = is_out_fwd;
            break;
        /* Submenu 60: Icon Style */
        case 60: {
            const char *ic_s = is_en
                ? (ic_flag_uk ? "Flag VN/UK" : (ic_badge ? "V/E Badge" : (ic_lotus ? "Lotus" : (ic_symb ? "Symbolic" : "Flag VN/US"))))
                : (ic_flag_uk ? "Cờ VN/UK" : (ic_badge ? "Chữ V/E" : (ic_lotus ? "Hoa sen" : (ic_symb ? "Đơn sắc" : "Cờ VN/US"))));
            snprintf(label_buf, sizeof(label_buf), "%s: %s", is_en ? "Icon Style" : "Biểu tượng", ic_s);
            is_submenu_parent = TRUE;
            break;
        }
        case 61:
            label = is_en ? "Flat Flag VN / US" : "Cờ phẳng VN / US";
            toggle_type = "radio";
            checked = ic_flag_us;
            break;
        case 62:
            label = is_en ? "Flat Flag VN / UK" : "Cờ phẳng VN / UK";
            toggle_type = "radio";
            checked = ic_flag_uk;
            break;
        case 63:
            label = is_en ? "V / E Badge (UniKey)" : "Chữ V / E (UniKey)";
            toggle_type = "radio";
            checked = ic_badge;
            break;
        case 64:
            label = is_en ? "Lotus Flower" : "Hoa sen LotusKey";
            toggle_type = "radio";
            checked = ic_lotus;
            break;
        case 65:
            label = is_en ? "Monochrome Symbolic" : "Đơn sắc (Symbolic)";
            toggle_type = "radio";
            checked = ic_symb;
            break;
        /* Action items */
        case 10:
            label = is_en ? "Clipboard Charset Converter..." : "Chuyển mã Clipboard...";
            break;
        case 11:
            label = is_en ? "Quick Menu (` key)..." : "Menu nhanh (Phím `)...";
            break;
        case 12:
            label = is_en ? "LotusKey Settings..." : "Cài đặt LotusKey...";
            break;
        default:
            break;
    }

    g_variant_builder_add(props, "{sv}", "type", g_variant_new_string("standard"));
    g_variant_builder_add(props, "{sv}", "label", g_variant_new_string(label));
    g_variant_builder_add(props, "{sv}", "enabled", g_variant_new_boolean(TRUE));
    g_variant_builder_add(props, "{sv}", "visible", g_variant_new_boolean(TRUE));
    if (is_submenu_parent) {
        g_variant_builder_add(props, "{sv}", "children-display", g_variant_new_string("submenu"));
    }
    if (toggle_type != NULL) {
        g_variant_builder_add(props, "{sv}", "toggle-type", g_variant_new_string(toggle_type));
        g_variant_builder_add(props, "{sv}", "toggle-state", g_variant_new_int32(checked ? 1 : 0));
    }
}

static GVariant *sni_build_menu_node(gint id, gboolean include_children) {
    GVariantBuilder props;
    g_variant_builder_init(&props, G_VARIANT_TYPE("a{sv}"));
    sni_fill_menu_item_props(id, &props);

    GVariantBuilder children;
    g_variant_builder_init(&children, G_VARIANT_TYPE("av"));

    static const gint root_ids[] = { 1, 100, 20, 30, 40, 50, 60, 101, 10, 11, 12 };
    static const gint im_ids[]   = { 21, 22, 23 };
    static const gint cs_ids[]   = { 31, 32, 33, 34 };
    static const gint opt_ids[]  = { 41, 42, 43, 44, 45 };
    static const gint out_ids[]  = { 51, 52, 53 };
    static const gint ic_ids[]   = { 61, 62, 63, 64, 65 };

    const gint *child_ids = NULL;
    size_t child_count = 0;

    if (include_children) {
        switch (id) {
            case 0:
                child_ids = root_ids;
                child_count = sizeof(root_ids) / sizeof(root_ids[0]);
                break;
            case 20:
                child_ids = im_ids;
                child_count = sizeof(im_ids) / sizeof(im_ids[0]);
                break;
            case 30:
                child_ids = cs_ids;
                child_count = sizeof(cs_ids) / sizeof(cs_ids[0]);
                break;
            case 40:
                child_ids = opt_ids;
                child_count = sizeof(opt_ids) / sizeof(opt_ids[0]);
                break;
            case 50:
                child_ids = out_ids;
                child_count = sizeof(out_ids) / sizeof(out_ids[0]);
                break;
            case 60:
                child_ids = ic_ids;
                child_count = sizeof(ic_ids) / sizeof(ic_ids[0]);
                break;
            default:
                break;
        }
    }

    for (size_t i = 0; i < child_count; i++) {
        GVariant *child_node = sni_build_menu_node(child_ids[i], TRUE);
        g_variant_builder_add(&children, "v", child_node);
    }

    return g_variant_new("(ia{sv}av)", id, &props, &children);
}

static void on_sni_method_call(GDBusConnection *conn, const gchar *sender, const gchar *object_path,
                               const gchar *interface_name, const gchar *method_name,
                               GVariant *parameters, GDBusMethodInvocation *invocation, gpointer user_data) {
    (void)conn; (void)sender; (void)object_path; (void)interface_name; (void)parameters; (void)user_data;
    if (g_strcmp0(method_name, "Activate") == 0 ||
        g_strcmp0(method_name, "SecondaryActivate") == 0 ||
        g_strcmp0(method_name, "XAyatanaSecondaryActivate") == 0 ||
        g_strcmp0(method_name, "Scroll") == 0) {
        sni_apply_menu_action(1);
        g_dbus_method_invocation_return_value(invocation, g_variant_new("()"));
        return;
    }
    if (g_strcmp0(method_name, "ContextMenu") == 0) {
        ibus_lotus_spawn_tool("lotuskey-menu");
        g_dbus_method_invocation_return_value(invocation, g_variant_new("()"));
        return;
    }
    if (g_strcmp0(method_name, "ProvideXdgActivationToken") == 0) {
        g_dbus_method_invocation_return_value(invocation, g_variant_new("()"));
        return;
    }
    g_dbus_method_invocation_return_value(invocation, g_variant_new("()"));
}

static GVariant *on_sni_get_property(GDBusConnection *conn, const gchar *sender, const gchar *object_path,
                                     const gchar *interface_name, const gchar *property_name,
                                     GError **error, gpointer user_data) {
    (void)conn; (void)sender; (void)object_path; (void)interface_name; (void)error; (void)user_data;
    if (g_strcmp0(property_name, "Category") == 0) return g_variant_new_string("ApplicationStatus");
    if (g_strcmp0(property_name, "Id") == 0) return g_variant_new_string("lotuskey");
    if (g_strcmp0(property_name, "Title") == 0) return g_variant_new_string("LotusKey");
    if (g_strcmp0(property_name, "Status") == 0) return g_variant_new_string("Active");
    if (g_strcmp0(property_name, "WindowId") == 0) return g_variant_new_int32(0);
    if (g_strcmp0(property_name, "IconThemePath") == 0) return g_variant_new_string("");
    if (g_strcmp0(property_name, "Menu") == 0) return g_variant_new_object_path("/StatusNotifierMenu");
    if (g_strcmp0(property_name, "ItemIsMenu") == 0) return g_variant_new_boolean(FALSE);
    if (g_strcmp0(property_name, "IconName") == 0) {
        gchar *icon_p = sni_get_current_icon_path();
        GVariant *ret = g_variant_new_string(icon_p ? icon_p : "input-keyboard");
        g_free(icon_p);
        return ret;
    }
    if (g_strcmp0(property_name, "IconPixmap") == 0 ||
        g_strcmp0(property_name, "OverlayIconPixmap") == 0 ||
        g_strcmp0(property_name, "AttentionIconPixmap") == 0) {
        return g_variant_new_array(G_VARIANT_TYPE("(iiay)"), NULL, 0);
    }
    return g_variant_new_string("");
}

static void on_dbusmenu_method_call(GDBusConnection *conn, const gchar *sender, const gchar *object_path,
                                    const gchar *interface_name, const gchar *method_name,
                                    GVariant *parameters, GDBusMethodInvocation *invocation, gpointer user_data) {
    (void)conn; (void)sender; (void)object_path; (void)interface_name; (void)user_data;
    if (g_strcmp0(method_name, "GetLayout") == 0) {
        gint parent_id = 0;
        gint recursion_depth = -1;
        g_variant_get(parameters, "(ii^as)", &parent_id, &recursion_depth, NULL);
        sni_sync_fallback_from_config();
        GVariant *layout = sni_build_menu_node(parent_id, recursion_depth != 0);
        g_dbus_method_invocation_return_value(
            invocation,
            g_variant_new("(u@(ia{sv}av))", g_sni_menu_revision, layout)
        );
        return;
    }
    if (g_strcmp0(method_name, "GetGroupProperties") == 0) {
        GVariantIter *id_iter = NULL;
        g_variant_get(parameters, "(ai^as)", &id_iter, NULL);
        sni_sync_fallback_from_config();
        GVariantBuilder res;
        g_variant_builder_init(&res, G_VARIANT_TYPE("a(ia{sv})"));
        gint id = 0;
        while (g_variant_iter_loop(id_iter, "i", &id)) {
            GVariantBuilder props;
            g_variant_builder_init(&props, G_VARIANT_TYPE("a{sv}"));
            sni_fill_menu_item_props(id, &props);
            g_variant_builder_add(&res, "(ia{sv})", id, &props);
        }
        g_variant_iter_free(id_iter);
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(a(ia{sv}))", &res));
        return;
    }
    if (g_strcmp0(method_name, "GetProperty") == 0) {
        gint id = 0;
        const gchar *name = NULL;
        g_variant_get(parameters, "(i&s)", &id, &name);
        sni_sync_fallback_from_config();
        GVariantBuilder props;
        g_variant_builder_init(&props, G_VARIANT_TYPE("a{sv}"));
        sni_fill_menu_item_props(id, &props);
        GVariant *dict = g_variant_ref_sink(g_variant_builder_end(&props));
        GVariant *val = name ? g_variant_lookup_value(dict, name, NULL) : NULL;
        GVariant *ret_tuple = g_variant_new("(v)", val ? val : g_variant_new_string(""));
        if (val) {
            g_variant_unref(val);
        }
        g_variant_unref(dict);
        g_dbus_method_invocation_return_value(invocation, ret_tuple);
        return;
    }
    if (g_strcmp0(method_name, "Event") == 0) {
        gint id = 0;
        const gchar *event_id = NULL;
        GVariant *data = NULL;
        guint32 ts = 0;
        g_variant_get(parameters, "(i&svu)", &id, &event_id, &data, &ts);
        if (data) g_variant_unref(data);
        if (g_strcmp0(event_id, "clicked") == 0 && sni_is_action_item_id(id)) {
            sni_apply_menu_action(id);
        }
        g_dbus_method_invocation_return_value(invocation, g_variant_new("()"));
        return;
    }
    if (g_strcmp0(method_name, "EventGroup") == 0) {
        GVariantIter *ev_iter = NULL;
        g_variant_get(parameters, "(a(isvu))", &ev_iter);
        gint id = 0;
        gchar *event_id = NULL;
        GVariant *data = NULL;
        guint32 ts = 0;
        while (g_variant_iter_loop(ev_iter, "(isvu)", &id, &event_id, &data, &ts)) {
            if (g_strcmp0(event_id, "clicked") == 0 && sni_is_action_item_id(id)) {
                sni_apply_menu_action(id);
            }
        }
        g_variant_iter_free(ev_iter);
        GVariantBuilder err_ids;
        g_variant_builder_init(&err_ids, G_VARIANT_TYPE("ai"));
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(ai)", &err_ids));
        return;
    }
    if (g_strcmp0(method_name, "AboutToShow") == 0) {
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(b)", FALSE));
        return;
    }
    if (g_strcmp0(method_name, "AboutToShowGroup") == 0) {
        GVariantBuilder b1, b2;
        g_variant_builder_init(&b1, G_VARIANT_TYPE("ai"));
        g_variant_builder_init(&b2, G_VARIANT_TYPE("ai"));
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(aiai)", &b1, &b2));
        return;
    }
}

static GVariant *on_dbusmenu_get_property(GDBusConnection *conn, const gchar *sender, const gchar *object_path,
                                          const gchar *interface_name, const gchar *property_name,
                                          GError **error, gpointer user_data) {
    (void)conn; (void)sender; (void)object_path; (void)interface_name; (void)error; (void)user_data;
    if (g_strcmp0(property_name, "Version") == 0) return g_variant_new_uint32(3);
    if (g_strcmp0(property_name, "TextDirection") == 0) return g_variant_new_string("ltr");
    if (g_strcmp0(property_name, "Status") == 0) return g_variant_new_string("normal");
    if (g_strcmp0(property_name, "IconThemePath") == 0) return g_variant_new_array(G_VARIANT_TYPE_STRING, NULL, 0);
    return g_variant_new_string("");
}

static void ibus_lotus_sni_notify_update(void) {
    if (!g_sni_conn) return;
    g_sni_menu_revision++;
    gchar *icon_p = sni_get_current_icon_path();

    GVariantBuilder changed;
    g_variant_builder_init(&changed, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&changed, "{sv}", "IconName", g_variant_new_string(icon_p ? icon_p : "input-keyboard"));
    g_variant_builder_add(&changed, "{sv}", "Status", g_variant_new_string("Active"));
    GVariantBuilder invalidated;
    g_variant_builder_init(&invalidated, G_VARIANT_TYPE("as"));

    g_dbus_connection_emit_signal(
        g_sni_conn, NULL, "/StatusNotifierItem",
        "org.freedesktop.DBus.Properties", "PropertiesChanged",
        g_variant_new("(sa{sv}as)", "org.kde.StatusNotifierItem", &changed, &invalidated),
        NULL
    );
    g_dbus_connection_emit_signal(
        g_sni_conn, NULL, "/StatusNotifierItem",
        "org.kde.StatusNotifierItem", "NewIcon",
        NULL, NULL
    );
    g_dbus_connection_emit_signal(
        g_sni_conn, NULL, "/StatusNotifierMenu",
        "com.canonical.dbusmenu", "LayoutUpdated",
        g_variant_new("(ui)", g_sni_menu_revision, 0),
        NULL
    );
    g_free(icon_p);
}

static void register_with_sni_watcher(GDBusConnection *conn) {
    const gchar *unique_name = g_dbus_connection_get_unique_name(conn);
    if (!unique_name) return;
    g_dbus_connection_call(
        conn,
        "org.kde.StatusNotifierWatcher",
        "/StatusNotifierWatcher",
        "org.kde.StatusNotifierWatcher",
        "RegisterStatusNotifierItem",
        g_variant_new("(s)", unique_name),
        NULL,
        G_DBUS_CALL_FLAGS_NONE,
        1000,
        NULL,
        NULL,
        NULL
    );
}

static void on_sni_watcher_appeared(GDBusConnection *conn, const gchar *name, const gchar *name_owner, gpointer user_data) {
    (void)name; (void)name_owner; (void)user_data;
    register_with_sni_watcher(conn);
}

static void setup_sni_tray_indicator(void) {
    g_sni_conn = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, NULL);
    if (!g_sni_conn) return;

    static const gchar sni_xml[] =
        "<node>"
        "  <interface name='org.kde.StatusNotifierItem'>"
        "    <property name='Category' type='s' access='read'/>"
        "    <property name='Id' type='s' access='read'/>"
        "    <property name='Title' type='s' access='read'/>"
        "    <property name='Status' type='s' access='read'/>"
        "    <property name='WindowId' type='i' access='read'/>"
        "    <property name='IconThemePath' type='s' access='read'/>"
        "    <property name='Menu' type='o' access='read'/>"
        "    <property name='ItemIsMenu' type='b' access='read'/>"
        "    <property name='IconName' type='s' access='read'/>"
        "    <property name='IconPixmap' type='a(iiay)' access='read'/>"
        "    <property name='OverlayIconName' type='s' access='read'/>"
        "    <property name='OverlayIconPixmap' type='a(iiay)' access='read'/>"
        "    <property name='AttentionIconName' type='s' access='read'/>"
        "    <property name='AttentionIconPixmap' type='a(iiay)' access='read'/>"
        "    <property name='AttentionMovieName' type='s' access='read'/>"
        "    <method name='ContextMenu'><arg name='x' type='i' direction='in'/><arg name='y' type='i' direction='in'/></method>"
        "    <method name='Activate'><arg name='x' type='i' direction='in'/><arg name='y' type='i' direction='in'/></method>"
        "    <method name='ProvideXdgActivationToken'><arg name='token' type='s' direction='in'/></method>"
        "    <method name='SecondaryActivate'><arg name='x' type='i' direction='in'/><arg name='y' type='i' direction='in'/></method>"
        "    <method name='XAyatanaSecondaryActivate'><arg name='timestamp' type='u' direction='in'/></method>"
        "    <method name='Scroll'><arg name='delta' type='i' direction='in'/><arg name='orientation' type='s' direction='in'/></method>"
        "    <signal name='NewTitle'/>"
        "    <signal name='NewIcon'/>"
        "    <signal name='NewAttentionIcon'/>"
        "    <signal name='NewOverlayIcon'/>"
        "    <signal name='NewToolTip'/>"
        "    <signal name='NewStatus'><arg name='status' type='s'/></signal>"
        "  </interface>"
        "</node>";

    static const gchar dbusmenu_xml[] =
        "<node>"
        "  <interface name='com.canonical.dbusmenu'>"
        "    <property name='Version' type='u' access='read'/>"
        "    <property name='TextDirection' type='s' access='read'/>"
        "    <property name='Status' type='s' access='read'/>"
        "    <property name='IconThemePath' type='as' access='read'/>"
        "    <method name='GetLayout'>"
        "      <arg type='i' name='parentId' direction='in'/>"
        "      <arg type='i' name='recursionDepth' direction='in'/>"
        "      <arg type='as' name='propertyNames' direction='in'/>"
        "      <arg type='u' name='revision' direction='out'/>"
        "      <arg type='(ia{sv}av)' name='layout' direction='out'/>"
        "    </method>"
        "    <method name='GetGroupProperties'>"
        "      <arg type='ai' name='ids' direction='in'/>"
        "      <arg type='as' name='propertyNames' direction='in'/>"
        "      <arg type='a(ia{sv})' name='properties' direction='out'/>"
        "    </method>"
        "    <method name='GetProperty'>"
        "      <arg type='i' name='id' direction='in'/>"
        "      <arg type='s' name='name' direction='in'/>"
        "      <arg type='v' name='value' direction='out'/>"
        "    </method>"
        "    <method name='Event'>"
        "      <arg type='i' name='id' direction='in'/>"
        "      <arg type='s' name='eventId' direction='in'/>"
        "      <arg type='v' name='data' direction='in'/>"
        "      <arg type='u' name='timestamp' direction='in'/>"
        "    </method>"
        "    <method name='EventGroup'>"
        "      <arg type='a(isvu)' name='events' direction='in'/>"
        "      <arg type='ai' name='idErrors' direction='out'/>"
        "    </method>"
        "    <method name='AboutToShow'>"
        "      <arg type='i' name='id' direction='in'/>"
        "      <arg type='b' name='needUpdate' direction='out'/>"
        "    </method>"
        "    <method name='AboutToShowGroup'>"
        "      <arg type='ai' name='ids' direction='in'/>"
        "      <arg type='ai' name='updatesNeeded' direction='out'/>"
        "      <arg type='ai' name='idErrors' direction='out'/>"
        "    </method>"
        "    <signal name='ItemsPropertiesUpdated'>"
        "      <arg type='a(ia{sv})' name='updatedProps' direction='out'/>"
        "      <arg type='a(ias)' name='removedProps' direction='out'/>"
        "    </signal>"
        "    <signal name='LayoutUpdated'>"
        "      <arg type='u' name='revision' direction='out'/>"
        "      <arg type='i' name='parent' direction='out'/>"
        "    </signal>"
        "  </interface>"
        "</node>";

    static const GDBusInterfaceVTable sni_vtable = {
        on_sni_method_call,
        on_sni_get_property,
        NULL,
        { 0 }
    };
    static const GDBusInterfaceVTable dbusmenu_vtable = {
        on_dbusmenu_method_call,
        on_dbusmenu_get_property,
        NULL,
        { 0 }
    };

    GDBusNodeInfo *sni_node = g_dbus_node_info_new_for_xml(sni_xml, NULL);
    if (sni_node) {
        g_dbus_connection_register_object(
            g_sni_conn, "/StatusNotifierItem",
            sni_node->interfaces[0], &sni_vtable, NULL, NULL, NULL
        );
        g_dbus_node_info_unref(sni_node);
    }

    GDBusNodeInfo *menu_node = g_dbus_node_info_new_for_xml(dbusmenu_xml, NULL);
    if (menu_node) {
        g_dbus_connection_register_object(
            g_sni_conn, "/StatusNotifierMenu",
            menu_node->interfaces[0], &dbusmenu_vtable, NULL, NULL, NULL
        );
        g_dbus_node_info_unref(menu_node);
    }

    g_bus_watch_name_on_connection(
        g_sni_conn,
        "org.kde.StatusNotifierWatcher",
        G_BUS_NAME_WATCHER_FLAGS_NONE,
        on_sni_watcher_appeared,
        NULL,
        NULL,
        NULL
    );
}

static void setup_config_monitors(void) {
    gchar *dir_path = ibus_lotus_get_config_dir();
    if (!dir_path) return;
    g_mkdir_with_parents(dir_path, 0700);
    chmod(dir_path, 0700);

    gchar *env_path = g_build_filename(dir_path, "config.env", NULL);
    GFile *env_file = g_file_new_for_path(env_path);
    g_config_monitor = g_file_monitor_file(env_file, G_FILE_MONITOR_NONE, NULL, NULL);
    if (g_config_monitor) {
        g_signal_connect(g_config_monitor, "changed", G_CALLBACK(on_config_file_changed), NULL);
    }
    g_object_unref(env_file);
    g_free(env_path);

    gchar *macro_path = g_build_filename(dir_path, "macros.conf", NULL);
    GFile *macro_file = g_file_new_for_path(macro_path);
    g_macro_monitor = g_file_monitor_file(macro_file, G_FILE_MONITOR_NONE, NULL, NULL);
    if (g_macro_monitor) {
        g_signal_connect(g_macro_monitor, "changed", G_CALLBACK(on_config_file_changed), NULL);
    }
    g_object_unref(macro_file);
    g_free(macro_path);

    g_free(dir_path);
}

static void ensure_live_ibus_socket(void) {
    const gchar *home = g_get_home_dir();
    if (!home) return;
    gchar *bus_dir = g_build_filename(home, ".config", "ibus", "bus", NULL);
    GDir *dir = g_dir_open(bus_dir, 0, NULL);
    if (!dir) {
        g_free(bus_dir);
        return;
    }

    const gchar *entry = NULL;
    gchar *wayland_file = NULL;
    gchar *x11_file = NULL;
    while ((entry = g_dir_read_name(dir)) != NULL) {
        if (strstr(entry, "-unix-wayland-") != NULL) {
            g_free(wayland_file);
            wayland_file = g_build_filename(bus_dir, entry, NULL);
            const char *dash = strchr(entry, '-');
            if (dash) {
                gchar *mid = g_strndup(entry, (gsize)(dash - entry));
                gchar *x11_name = g_strdup_printf("%s-unix-0", mid);
                g_free(x11_file);
                x11_file = g_build_filename(bus_dir, x11_name, NULL);
                g_free(x11_name);
                g_free(mid);
            }
        }
    }
    g_dir_close(dir);

    if (wayland_file && g_file_test(wayland_file, G_FILE_TEST_IS_REGULAR)) {
        if (x11_file && !g_file_test(x11_file, G_FILE_TEST_IS_SYMLINK)) {
            unlink(x11_file);
            gchar *base_wf = g_path_get_basename(wayland_file);
            if (symlink(base_wf, x11_file) != 0) {
                /* ignore */
            }
            g_free(base_wf);
        }

        if (!g_getenv("IBUS_ADDRESS")) {
            FILE *fp = fopen(wayland_file, "r");
            if (fp) {
                char line[512];
                char addr[512] = {0};
                long pid = 0;
                while (fgets(line, sizeof(line), fp)) {
                    if (strncmp(line, "IBUS_ADDRESS=", 13) == 0) {
                        snprintf(addr, sizeof(addr), "%s", line + 13);
                        size_t alen = strlen(addr);
                        while (alen > 0 && (addr[alen - 1] == '\n' || addr[alen - 1] == '\r')) {
                            addr[--alen] = '\0';
                        }
                    } else if (strncmp(line, "IBUS_DAEMON_PID=", 16) == 0) {
                        pid = atol(line + 16);
                    }
                }
                fclose(fp);
                if (addr[0] != '\0' && (pid <= 0 || kill((pid_t)pid, 0) == 0)) {
                    g_setenv("IBUS_ADDRESS", addr, TRUE);
                }
            }
        }
    }

    g_free(wayland_file);
    g_free(x11_file);
    g_free(bus_dir);
}

int main(int argc, char **argv) {
    prctl(PR_SET_DUMPABLE, 0);

    static gboolean ibus = FALSE;
    GError *error = NULL;
    GOptionContext *context;

    static const GOptionEntry entries[] = {
        { "ibus", 'i', 0, G_OPTION_ARG_NONE, &ibus, "Executed by ibus-daemon", NULL },
        { NULL }
    };

    context = g_option_context_new("- LotusKey Vietnamese Input Method Engine");
    g_option_context_add_main_entries(context, entries, "ibus-lotus");

    if (!g_option_context_parse(context, &argc, &argv, &error)) {
        g_print("Option parsing failed: %s\n", error->message);
        g_error_free(error);
        return 1;
    }
    g_option_context_free(context);

    ensure_live_ibus_socket();
    ibus_init();
    ibus_lotus_reload_macros();
    setup_config_monitors();
    setup_sni_tray_indicator();
    g_unix_signal_add(SIGUSR1, on_sigusr1_unix_signal, NULL);

    IBusBus *bus = NULL;
    for (int attempt = 0; attempt < 20; attempt++) {
        ensure_live_ibus_socket();
        bus = ibus_bus_new();
        if (bus && ibus_bus_is_connected(bus)) {
            break;
        }
        if (bus) {
            g_object_unref(bus);
            bus = NULL;
        }
        usleep(500000);
    }
    if (!bus || !ibus_bus_is_connected(bus)) {
        g_warning("Cannot connect to IBus daemon!");
        return 1;
    }

    IBusFactory *factory = ibus_factory_new(ibus_bus_get_connection(bus));
    ibus_factory_add_engine(factory, "lotuskey", IBUS_TYPE_LOTUS_ENGINE);
    ibus_factory_add_engine(factory, "lotuskey-vni", IBUS_TYPE_LOTUS_ENGINE);
    ibus_factory_add_engine(factory, "lotus", IBUS_TYPE_LOTUS_ENGINE);
    ibus_factory_add_engine(factory, "lotus-vni", IBUS_TYPE_LOTUS_ENGINE);

    if (ibus) {
        ibus_bus_request_name(bus, "org.freedesktop.IBus.LotusKey", 0);
    } else {
        const gchar *home = g_get_home_dir();
        gchar *user_xml = home ? g_build_filename(home, ".local", "share", "ibus", "component", "lotuskey.xml", NULL) : NULL;
        gchar *rel_xml = NULL;
        if (!user_xml || !g_file_test(user_xml, G_FILE_TEST_EXISTS)) {
            char self_path[PATH_MAX];
            ssize_t len = readlink("/proc/self/exe", self_path, sizeof(self_path) - 1);
            if (len > 0) {
                self_path[len] = '\0';
                gchar *bin_dir = g_path_get_dirname(self_path);
                gchar *parent_dir = g_path_get_dirname(bin_dir);
                gchar *prefix_dir = g_path_get_dirname(parent_dir);
                gchar *cand1 = g_build_filename(prefix_dir, "share", "ibus", "component", "lotuskey.xml", NULL);
                gchar *cand2 = g_build_filename(parent_dir, "engine", "lotuskey.xml", NULL);
                g_free(bin_dir);
                g_free(parent_dir);
                g_free(prefix_dir);
                if (g_file_test(cand1, G_FILE_TEST_EXISTS)) {
                    rel_xml = cand1;
                    g_free(cand2);
                } else if (g_file_test(cand2, G_FILE_TEST_EXISTS)) {
                    rel_xml = cand2;
                    g_free(cand1);
                } else {
                    g_free(cand1);
                    g_free(cand2);
                }
            }
        }
        const gchar *xml_path = (user_xml && g_file_test(user_xml, G_FILE_TEST_EXISTS))
            ? user_xml
            : (rel_xml ? rel_xml : "/usr/share/ibus/component/lotuskey.xml");
        IBusComponent *component = ibus_component_new_from_file(xml_path);
        if (component) {
            ibus_bus_register_component(bus, component);
        }
        g_free(user_xml);
        g_free(rel_xml);
    }

    ibus_main();
    return 0;
}
