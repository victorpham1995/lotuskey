/*
 * LotusKey (ibus-LotusKey) - Native IBus Engine
 * Author: Victor Pham
 * High-performance Vietnamese Input Method Engine for GNOME Wayland
 * Powered by pure C-ABI Bridge (VieLotus Core)
 */

#include <ibus.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <stdarg.h>
#include <signal.h>
#include "vielotus.h"

static void log_debug(const char *fmt, ...) {
    FILE *fp = fopen("/tmp/ibus_lotus.log", "a");
    if (!fp) return;
    va_list args;
    va_start(args, fmt);
    vfprintf(fp, fmt, args);
    va_end(args);
    fclose(fp);
}

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

typedef struct _IBusLotusEngine IBusLotusEngine;
typedef struct _IBusLotusEngineClass IBusLotusEngineClass;

struct _IBusLotusEngine {
    IBusEngine parent;
    vielotus_session_t session;
    gboolean enabled;
    gboolean is_vni;
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
    gboolean autostart;
    gchar *output_mode;
    gint charset;
    gint toggle_mode;
    gboolean ctrl_pressed;
    gboolean shift_pressed;
    gboolean other_key_in_chord;
    gint64 last_grave_time_ms;
    time_t config_mtime;
    IBusPropList *prop_list;
};

struct _IBusLotusEngineClass {
    IBusEngineClass parent_class;
};

GType ibus_lotus_engine_get_type(void);
G_DEFINE_TYPE(IBusLotusEngine, ibus_lotus_engine, IBUS_TYPE_ENGINE)

static gint64 get_current_time_ms(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((gint64)tv.tv_sec) * 1000 + (tv.tv_usec / 1000);
}

static gchar *ibus_lotus_get_config_dir(void) {
    const gchar *cfg_root = g_get_user_config_dir();
    if (!cfg_root) {
        return NULL;
    }
    return g_build_filename(cfg_root, "LotusKey", NULL);
}

static GList *active_engines = NULL;
static void ibus_lotus_load_user_config(IBusLotusEngine *vl_engine);
static void ibus_lotus_build_prop_list(IBusLotusEngine *vl_engine);

static void ibus_lotus_reload_all_engines(void) {
    for (GList *l = active_engines; l != NULL; l = l->next) {
        IBusLotusEngine *vl = (IBusLotusEngine *)l->data;
        ibus_lotus_load_user_config(vl);
        ibus_lotus_build_prop_list(vl);
        ibus_engine_register_properties((IBusEngine *)vl, vl->prop_list);
    }
}

static void sigusr1_handler(int sig) {
    (void)sig;
    ibus_lotus_reload_all_engines();
}

static void ibus_lotus_check_and_reload_config(IBusLotusEngine *vl_engine) {
    gchar *dir_path = ibus_lotus_get_config_dir();
    if (!dir_path) return;
    gchar *path = g_build_filename(dir_path, "config.env", NULL);
    g_free(dir_path);
    struct stat st;
    if (stat(path, &st) == 0) {
        if (st.st_mtime != vl_engine->config_mtime) {
            ibus_lotus_load_user_config(vl_engine);
            ibus_lotus_build_prop_list(vl_engine);
            ibus_engine_register_properties((IBusEngine *)vl_engine, vl_engine->prop_list);
        }
    }
    g_free(path);
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

static void ibus_lotus_engine_reset_internal(IBusLotusEngine *vl_engine) {
    vl_engine->replayed_after_backspace = FALSE;
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    if (vl_engine->session) {
        vielotus_reset_session(vl_engine->session);
    }
    ibus_lotus_clear_preedit((IBusEngine *)vl_engine);
}

static void ibus_lotus_commit_composing(IBusLotusEngine *vl_engine, const char *trailing_ascii) {
    IBusEngine *engine = (IBusEngine *)vl_engine;
    char buf[1024];
    buf[0] = '\0';

    if (vl_engine->session && vielotus_is_composing(vl_engine->session)) {
        if (trailing_ascii && trailing_ascii[0] != '\0' && trailing_ascii[1] == '\0') {
            uint32_t cp = (uint32_t)(unsigned char)trailing_ascii[0];
            vielotus_feed_char(vl_engine->session, cp);
        } else {
            vielotus_commit_word(vl_engine->session);
        }
        const char *committed = vielotus_get_last_text(vl_engine->session);
        if (committed && committed[0] != '\0') {
            snprintf(buf, sizeof(buf), "%s", committed);
        }
    }

    if (trailing_ascii && trailing_ascii[0] != '\0') {
        size_t len = strlen(buf);
        if (len < sizeof(buf) - 1) {
            snprintf(buf + len, sizeof(buf) - len, "%s", trailing_ascii);
        }
    }

    if (buf[0] != '\0') {
        IBusText *commit_text = ibus_text_new_from_string(buf);
        ibus_engine_commit_text(engine, commit_text);
    }

    ibus_lotus_engine_reset_internal(vl_engine);
}

static void ibus_lotus_update_preedit(IBusLotusEngine *vl_engine) {
    IBusEngine *engine = (IBusEngine *)vl_engine;
    if (vl_engine->session && vielotus_is_composing(vl_engine->session)) {
        const char *composing = vielotus_get_composing_text(vl_engine->session);
        if (composing && composing[0] != '\0') {
            IBusText *text = ibus_text_new_from_string(composing);
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
    gboolean config_is_vni = FALSE;

    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "ENABLED=", 8) == 0) {
            vl_engine->enabled = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "INPUT_METHOD=", 13) == 0) {
            has_input_method_override = TRUE;
            config_is_vni = (strstr(line, "vni") != NULL || strstr(line, "VNI") != NULL);
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
        } else if (strncmp(line, "OUTPUT_MODE=", 12) == 0) {
            if (vl_engine->output_mode) g_free(vl_engine->output_mode);
            if (strstr(line, "surrounding")) vl_engine->output_mode = g_strdup("surrounding");
            else if (strstr(line, "forward")) vl_engine->output_mode = g_strdup("forward");
            else vl_engine->output_mode = g_strdup("preedit");
        } else if (strncmp(line, "CHARSET=", 8) == 0) {
            vl_engine->charset = atoi(line + 8);
        } else if (strncmp(line, "AUTOSTART=", 10) == 0) {
            vl_engine->autostart = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        }
    }
    fclose(fp);

    const gchar *engine_name = ibus_engine_get_name((IBusEngine *)vl_engine);
    if (engine_name && strstr(engine_name, "vni") != NULL) {
        vl_engine->is_vni = TRUE;
    } else if (has_input_method_override) {
        vl_engine->is_vni = config_is_vni;
    }

    vielotus_set_input_method(
        vl_engine->session,
        vl_engine->is_vni ? VIELOTUS_INPUT_VNI : VIELOTUS_INPUT_TELEX
    );
    vielotus_set_grammar_profile(
        vl_engine->session,
        vl_engine->sen_flex ? VIELOTUS_GRAMMAR_SEN_FLEX : VIELOTUS_GRAMMAR_CLASSIC
    );
    vielotus_set_smart_bilingual(vl_engine->session, vl_engine->smart_bilingual);
    vielotus_set_modern_orthography(vl_engine->session, vl_engine->modern_orthography);
    vielotus_set_quick_telex(vl_engine->session, vl_engine->quick_telex);
}

static void ibus_lotus_save_user_config(IBusLotusEngine *vl_engine) {
    gchar *dir_path = ibus_lotus_get_config_dir();
    if (!dir_path) {
        return;
    }
    g_mkdir_with_parents(dir_path, 0755);
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

    fprintf(fp, "ENABLED=\"%s\"\n", vl_engine->enabled ? "true" : "false");
    fprintf(fp, "INPUT_METHOD=\"%s\"\n", vl_engine->is_vni ? "vni" : "telex");
    fprintf(fp, "GRAMMAR_PROFILE=\"%s\"\n", vl_engine->sen_flex ? "sen_flex" : "classic");
    fprintf(fp, "SMART_BILINGUAL=\"%s\"\n", vl_engine->smart_bilingual ? "true" : "false");
    fprintf(fp, "MODERN_ORTHOGRAPHY=\"%s\"\n", vl_engine->modern_orthography ? "true" : "false");
    fprintf(fp, "QUICK_TELEX=\"%s\"\n", vl_engine->quick_telex ? "true" : "false");
    fprintf(fp, "PREEDIT_UNDERLINE=\"%s\"\n", vl_engine->preedit_underline ? "true" : "false");
    fprintf(fp, "MODE_MENU_KEY=\"%s\"\n", vl_engine->grave_menu_enabled ? "grave" : "None");
    fprintf(fp, "TOGGLE_KEY=\"%s\"\n", tm_str);
    fprintf(fp, "W2U=\"%s\"\n", vl_engine->w2u ? "true" : "false");
    fprintf(fp, "BRACKET_TRANSFORM=\"%s\"\n", vl_engine->bracket_transform ? "true" : "false");
    fprintf(fp, "OUTPUT_MODE=\"%s\"\n", vl_engine->output_mode ? vl_engine->output_mode : "preedit");
    fprintf(fp, "CHARSET=\"%d\"\n", vl_engine->charset);
    fprintf(fp, "AUTOSTART=\"%s\"\n", vl_engine->autostart ? "true" : "false");
    fclose(fp);

    struct stat st;
    if (stat(path, &st) == 0) {
        vl_engine->config_mtime = st.st_mtime;
    }
    g_free(path);

    // Also synchronize config.json
    gchar *path_json = g_build_filename(dir_path, "config.json", NULL);
    FILE *fp_json = fopen(path_json, "w");
    if (fp_json) {
        fprintf(fp_json, "{\n");
        fprintf(fp_json, "    \"enabled\": %s,\n", vl_engine->enabled ? "true" : "false");
        fprintf(fp_json, "    \"input_method\": %d,\n", vl_engine->is_vni ? 1 : 0);
        fprintf(fp_json, "    \"output_mode\": \"%s\",\n", vl_engine->output_mode ? vl_engine->output_mode : "preedit");
        fprintf(fp_json, "    \"charset\": %d,\n", vl_engine->charset);
        fprintf(fp_json, "    \"free_tone_marking\": %s,\n", vl_engine->sen_flex ? "true" : "false");
        fprintf(fp_json, "    \"modern_tone_style\": %s,\n", vl_engine->modern_orthography ? "true" : "false");
        fprintf(fp_json, "    \"auto_correct\": %s,\n", vl_engine->smart_bilingual ? "true" : "false");
        fprintf(fp_json, "    \"w2u\": %s,\n", vl_engine->w2u ? "true" : "false");
        fprintf(fp_json, "    \"bracket_transform\": %s,\n", vl_engine->bracket_transform ? "true" : "false");
        fprintf(fp_json, "    \"toggle_key\": \"%s\",\n", tm_str);
        fprintf(fp_json, "    \"mode_menu_key\": \"%s\",\n", vl_engine->grave_menu_enabled ? "grave" : "None");
        fprintf(fp_json, "    \"quick_telex\": %s,\n", vl_engine->quick_telex ? "true" : "false");
        fprintf(fp_json, "    \"preedit_underline\": %s,\n", vl_engine->preedit_underline ? "true" : "false");
        fprintf(fp_json, "    \"autostart\": %s\n", vl_engine->autostart ? "true" : "false");
        fprintf(fp_json, "}\n");
        fclose(fp_json);
    }
    g_free(path_json);
    g_free(dir_path);
}

static void ibus_lotus_build_prop_list(IBusLotusEngine *vl_engine) {
    if (vl_engine->prop_list) {
        g_object_unref(vl_engine->prop_list);
    }
    vl_engine->prop_list = ibus_prop_list_new();
    g_object_ref_sink(vl_engine->prop_list);

    IBusProperty *prop;
    IBusText *label;

    char status_str[64];
    snprintf(status_str, sizeof(status_str), "LotusKey: %s [%s]",
             vl_engine->enabled ? "Tiếng Việt" : "English",
             vl_engine->is_vni ? "VNI" : "Telex");

    label = ibus_text_new_from_string(status_str);
    prop = ibus_property_new("lotus-status", PROP_TYPE_NORMAL, label, NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    label = ibus_text_new_from_static_string("Quick Menu (Phím `)...");
    prop = ibus_property_new("lotus-quick-menu", PROP_TYPE_NORMAL, label, NULL, NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    label = ibus_text_new_from_static_string("Bảng điều khiển LotusKey...");
    prop = ibus_property_new("lotus-setup", PROP_TYPE_NORMAL, label, "preferences-system", NULL,
                             TRUE, TRUE, PROP_STATE_UNCHECKED, NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    label = ibus_text_new_from_static_string("Smart Bilingual (Song ngữ tự phục hồi)");
    prop = ibus_property_new("smart-bilingual", PROP_TYPE_TOGGLE, label, NULL, NULL,
                             TRUE, TRUE,
                             vl_engine->smart_bilingual ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED,
                             NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);

    label = ibus_text_new_from_static_string("Modern Orthography (Bỏ dấu oà, uý)");
    prop = ibus_property_new("modern-orthography", PROP_TYPE_TOGGLE, label, NULL, NULL,
                             TRUE, TRUE,
                             vl_engine->modern_orthography ? PROP_STATE_CHECKED : PROP_STATE_UNCHECKED,
                             NULL);
    ibus_prop_list_append(vl_engine->prop_list, prop);
}

static void ibus_lotus_toggle_vietnamese(IBusLotusEngine *vl_engine) {
    vl_engine->enabled = !vl_engine->enabled;
    log_debug(">>> TOGGLED: enabled=%d\n", vl_engine->enabled);
    if (!vl_engine->enabled && vielotus_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    }
    ibus_lotus_save_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
    ibus_engine_register_properties((IBusEngine *)vl_engine, vl_engine->prop_list);

    // Desktop Notification feedback
    if (vl_engine->enabled) {
        g_spawn_command_line_async("notify-send -t 1200 -h string:x-canonical-private-synchronous:lotus-toggle -i /usr/share/icons/hicolor/scalable/apps/fcitx-lotus.svg 'LotusKey' '🇻🇳 Chế độ Tiếng Việt (ON)'", NULL);
    } else {
        g_spawn_command_line_async("notify-send -t 1200 -h string:x-canonical-private-synchronous:lotus-toggle 'LotusKey' '🇬🇧 Chế độ Tiếng Anh / English (OFF)'", NULL);
    }
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
    vielotus_reset_session(vl_engine->session);
    for (size_t i = 0; raw_keys[i] != '\0'; i++) {
        vielotus_feed_char(vl_engine->session, (uint32_t)(unsigned char)raw_keys[i]);
    }
}

static void ibus_lotus_backspace_composing(IBusLotusEngine *vl_engine) {
    const char *composing = vielotus_get_composing_text(vl_engine->session);
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

    vielotus_feed_backspace(vl_engine->session);
    if (!vielotus_is_composing(vl_engine->session)) {
        ibus_lotus_engine_reset_internal(vl_engine);
        return;
    }
    const char *after = vielotus_get_composing_text(vl_engine->session);
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
    vielotus_reset_session(vl_engine->session);
    for (size_t i = 0; raw_keys[i] != '\0'; i++) {
        vielotus_feed_char(vl_engine->session, (uint32_t)(unsigned char)raw_keys[i]);
    }
    vl_engine->replayed_after_backspace = TRUE;
    if (!vielotus_is_composing(vl_engine->session)) {
        ibus_lotus_engine_reset_internal(vl_engine);
    } else {
        ibus_lotus_update_preedit(vl_engine);
    }
}

static void ibus_lotus_engine_init(IBusLotusEngine *vl_engine) {
    vl_engine->session = vielotus_create_session();
    vl_engine->enabled = TRUE;
    vl_engine->is_vni = FALSE;
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
    vl_engine->autostart = TRUE;
    vl_engine->output_mode = g_strdup("preedit");
    vl_engine->charset = 0;
    vl_engine->toggle_mode = TOGGLE_BOTH;
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    vl_engine->last_grave_time_ms = 0;
    vl_engine->prop_list = NULL;

    active_engines = g_list_append(active_engines, vl_engine);

    vielotus_set_input_method(vl_engine->session, VIELOTUS_INPUT_TELEX);
    ibus_lotus_load_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
}

static void ibus_lotus_engine_finalize(GObject *object) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)object;
    active_engines = g_list_remove(active_engines, vl_engine);
    if (vl_engine->output_mode) {
        g_free(vl_engine->output_mode);
        vl_engine->output_mode = NULL;
    }
    if (vl_engine->prop_list) {
        g_object_unref(vl_engine->prop_list);
        vl_engine->prop_list = NULL;
    }
    if (vl_engine->session) {
        vielotus_destroy_session(vl_engine->session);
        vl_engine->session = NULL;
    }
    G_OBJECT_CLASS(ibus_lotus_engine_parent_class)->finalize(object);
}

static void ibus_lotus_engine_reset(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    ibus_lotus_engine_reset_internal(vl_engine);
    if (vl_engine->session) {
        vielotus_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->reset(engine);
}

static void ibus_lotus_engine_enable(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    const gchar *engine_name = ibus_engine_get_name(engine);
    if (engine_name && strstr(engine_name, "vni") != NULL) {
        vl_engine->is_vni = TRUE;
        vielotus_set_input_method(vl_engine->session, VIELOTUS_INPUT_VNI);
    } else {
        vl_engine->is_vni = FALSE;
        vielotus_set_input_method(vl_engine->session, VIELOTUS_INPUT_TELEX);
    }
    ibus_lotus_load_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
    ibus_lotus_engine_reset_internal(vl_engine);
    if (vl_engine->session) {
        vielotus_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->enable(engine);
}

static void ibus_lotus_engine_disable(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->is_password_field = FALSE;
    if (vielotus_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    } else {
        ibus_lotus_engine_reset_internal(vl_engine);
    }
    if (vl_engine->session) {
        vielotus_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->disable(engine);
}

static void ibus_lotus_engine_focus_in(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    guint purpose = IBUS_INPUT_PURPOSE_FREE_FORM;
    guint hints = IBUS_INPUT_HINT_NONE;
    ibus_engine_get_content_type(engine, &purpose, &hints);
    vl_engine->is_password_field = (purpose == IBUS_INPUT_PURPOSE_PASSWORD) || (purpose == IBUS_INPUT_PURPOSE_PIN);
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    ibus_lotus_load_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
    ibus_engine_register_properties(engine, vl_engine->prop_list);
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->focus_in(engine);
}

static void ibus_lotus_engine_focus_out(IBusEngine *engine) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->is_password_field = FALSE;
    vl_engine->ctrl_pressed = FALSE;
    vl_engine->shift_pressed = FALSE;
    vl_engine->other_key_in_chord = FALSE;
    if (vielotus_is_composing(vl_engine->session)) {
        ibus_lotus_commit_composing(vl_engine, NULL);
    } else {
        ibus_lotus_engine_reset_internal(vl_engine);
    }
    if (vl_engine->session) {
        vielotus_append_context(vl_engine->session, "");
    }
    IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->focus_out(engine);
}

static void ibus_lotus_engine_set_content_type(IBusEngine *engine, guint purpose, guint hints) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    vl_engine->is_password_field = (purpose == IBUS_INPUT_PURPOSE_PASSWORD) || (purpose == IBUS_INPUT_PURPOSE_PIN);
    if (vl_engine->is_password_field && vielotus_is_composing(vl_engine->session)) {
        ibus_lotus_engine_reset_internal(vl_engine);
    }
    if (IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->set_content_type) {
        IBUS_ENGINE_CLASS(ibus_lotus_engine_parent_class)->set_content_type(engine, purpose, hints);
    }
}

static void ibus_lotus_engine_property_activate(IBusEngine *engine, const gchar *prop_name, guint prop_state) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    if (g_strcmp0(prop_name, "lotus-setup") == 0) {
        g_spawn_command_line_async("/usr/bin/lotuskey-setup", NULL);
        return;
    } else if (g_strcmp0(prop_name, "lotus-quick-menu") == 0) {
        g_spawn_command_line_async("/usr/bin/lotuskey-menu", NULL);
        return;
    } else if (g_strcmp0(prop_name, "lotus-status") == 0) {
        ibus_lotus_toggle_vietnamese(vl_engine);
        return;
    } else if (g_strcmp0(prop_name, "smart-bilingual") == 0) {
        vl_engine->smart_bilingual = (prop_state == PROP_STATE_CHECKED);
        vielotus_set_smart_bilingual(vl_engine->session, vl_engine->smart_bilingual);
    } else if (g_strcmp0(prop_name, "modern-orthography") == 0) {
        vl_engine->modern_orthography = (prop_state == PROP_STATE_CHECKED);
        vielotus_set_modern_orthography(vl_engine->session, vl_engine->modern_orthography);
    }
    ibus_lotus_save_user_config(vl_engine);
    ibus_lotus_build_prop_list(vl_engine);
    ibus_engine_register_properties(engine, vl_engine->prop_list);
}

static gboolean ibus_lotus_engine_process_key_event(IBusEngine *engine, guint keyval, guint keycode, guint state) {
    IBusLotusEngine *vl_engine = (IBusLotusEngine *)engine;
    (void)keycode;

    // Check if configuration on disk has changed and hot-reload
    ibus_lotus_check_and_reload_config(vl_engine);

    gboolean is_release = (state & IBUS_RELEASE_MASK) != 0;

    // Handle key release events (used for Ctrl+Shift chord detection)
    if (is_release) {
        if (keyval == IBUS_KEY_Control_L || keyval == IBUS_KEY_Control_R ||
            keyval == IBUS_KEY_Shift_L || keyval == IBUS_KEY_Shift_R) {

            // If both Ctrl and Shift were held down and no other key was pressed:
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

    // Key Press Events:
    // Update modifier trackers
    if (keyval == IBUS_KEY_Control_L || keyval == IBUS_KEY_Control_R) {
        vl_engine->ctrl_pressed = TRUE;
        return FALSE;
    }
    if (keyval == IBUS_KEY_Shift_L || keyval == IBUS_KEY_Shift_R) {
        vl_engine->shift_pressed = TRUE;
        return FALSE;
    }

    // Mark chord corrupted if another key is pressed while holding Ctrl/Shift
    if (vl_engine->ctrl_pressed || vl_engine->shift_pressed) {
        vl_engine->other_key_in_chord = TRUE;
    }

    // Password / PIN protection
    if (vl_engine->is_password_field) {
        if (vielotus_is_composing(vl_engine->session)) {
            ibus_lotus_engine_reset_internal(vl_engine);
        }
        return FALSE;
    }

    // Pure modifier keys: CapsLock, ShiftLock, Level3
    if (keyval == IBUS_KEY_Caps_Lock || keyval == IBUS_KEY_Shift_Lock ||
        keyval == IBUS_KEY_ISO_Level3_Shift) {
        return FALSE;
    }

    // Hotkey Alt + Z: Toggle VN/EN
    if ((state & IBUS_MOD1_MASK) && (keyval == 'z' || keyval == 'Z')) {
        if (vl_engine->toggle_mode == TOGGLE_ALT_Z || vl_engine->toggle_mode == TOGGLE_BOTH) {
            ibus_lotus_toggle_vietnamese(vl_engine);
            return TRUE;
        }
    }

    // Hotkey Shift + Space: Toggle VN/EN
    if ((state & IBUS_SHIFT_MASK) && (keyval == IBUS_KEY_space || keyval == ' ')) {
        if (vl_engine->toggle_mode == TOGGLE_SHIFT_SPACE) {
            ibus_lotus_toggle_vietnamese(vl_engine);
            return TRUE;
        }
    }

    // Pass through system hotkeys (Ctrl, Alt, Super/Win)
    if (state & (IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_SUPER_MASK)) {
        if (vielotus_is_composing(vl_engine->session)) {
            ibus_lotus_commit_composing(vl_engine, NULL);
        }
        return FALSE;
    }

    // Navigation & action keys: commit active word first
    if (keyval == IBUS_KEY_Return || keyval == IBUS_KEY_KP_Enter || keyval == IBUS_KEY_Linefeed ||
        keyval == IBUS_KEY_Tab || keyval == IBUS_KEY_ISO_Left_Tab || keyval == IBUS_KEY_KP_Tab ||
        keyval == IBUS_KEY_Delete || keyval == IBUS_KEY_KP_Delete ||
        keyval == IBUS_KEY_Escape ||
        keyval == '\r' || keyval == '\n' || keyval == '\t' || keyval == 0x1b ||
        (keyval >= IBUS_KEY_Home && keyval <= IBUS_KEY_Insert) ||
        (keyval >= IBUS_KEY_KP_Home && keyval <= IBUS_KEY_KP_Delete)) {
        if (vielotus_is_composing(vl_engine->session)) {
            ibus_lotus_commit_composing(vl_engine, NULL);
        }
        if (vl_engine->session) {
            vielotus_append_context(vl_engine->session, "");
        }
        return FALSE;
    }

    // Handle BackSpace
    if (keyval == IBUS_KEY_BackSpace) {
        if (vielotus_is_composing(vl_engine->session)) {
            ibus_lotus_backspace_composing(vl_engine);
            return TRUE;
        }
        vielotus_reset_session(vl_engine->session);
        return FALSE;
    }

    // Handle Grave Key ` to open Quick Menu (if enabled and not composing)
    if (keyval == '`' && vl_engine->grave_menu_enabled && !vielotus_is_composing(vl_engine->session)) {
        gint64 now = get_current_time_ms();
        if (now - vl_engine->last_grave_time_ms < 400) {
            // Second press in rapid succession: pass literal ` to app
            vl_engine->last_grave_time_ms = 0;
            return FALSE;
        }
        vl_engine->last_grave_time_ms = now;
        g_spawn_command_line_async("/usr/bin/lotuskey-menu", NULL);
        return TRUE;
    }

    // If Vietnamese is disabled, pass all printable characters through directly (English passthrough)
    if (!vl_engine->enabled) {
        return FALSE;
    }

    // Handle Bracket transforms '[' -> 'ơ', ']' -> 'ư', '{' -> 'Ơ', '}' -> 'Ư'
    if (vl_engine->bracket_transform && !vl_engine->is_vni) {
        if (keyval == '[') {
            if (vielotus_is_composing(vl_engine->session)) {
                ibus_lotus_commit_composing(vl_engine, NULL);
            }
            IBusText *commit_text = ibus_text_new_from_static_string("ơ");
            ibus_engine_commit_text(engine, commit_text);
            ibus_lotus_engine_reset_internal(vl_engine);
            return TRUE;
        } else if (keyval == ']') {
            if (vielotus_is_composing(vl_engine->session)) {
                ibus_lotus_commit_composing(vl_engine, NULL);
            }
            IBusText *commit_text = ibus_text_new_from_static_string("ư");
            ibus_engine_commit_text(engine, commit_text);
            ibus_lotus_engine_reset_internal(vl_engine);
            return TRUE;
        } else if (keyval == '{') {
            if (vielotus_is_composing(vl_engine->session)) {
                ibus_lotus_commit_composing(vl_engine, NULL);
            }
            IBusText *commit_text = ibus_text_new_from_static_string("Ơ");
            ibus_engine_commit_text(engine, commit_text);
            ibus_lotus_engine_reset_internal(vl_engine);
            return TRUE;
        } else if (keyval == '}') {
            if (vielotus_is_composing(vl_engine->session)) {
                ibus_lotus_commit_composing(vl_engine, NULL);
            }
            IBusText *commit_text = ibus_text_new_from_static_string("Ư");
            ibus_engine_commit_text(engine, commit_text);
            ibus_lotus_engine_reset_internal(vl_engine);
            return TRUE;
        }
    }

    // Handle W2U option: If w2u is disabled, typing 'w' or 'W' at start of word should NOT turn into 'ư'/'Ư'
    if (!vl_engine->w2u && !vl_engine->is_vni && (keyval == 'w' || keyval == 'W') && !vielotus_is_composing(vl_engine->session)) {
        char buf[2] = { (char)keyval, '\0' };
        IBusText *commit_text = ibus_text_new_from_string(buf);
        ibus_engine_commit_text(engine, commit_text);
        return TRUE;
    }

    // Handle printable ASCII characters (32..126)
    if (keyval >= 32 && keyval < 127) {
        gboolean is_alpha = (keyval >= 'a' && keyval <= 'z') || (keyval >= 'A' && keyval <= 'Z');
        gboolean is_digit = (keyval >= '0' && keyval <= '9');
        gboolean is_word_char = is_alpha || (vl_engine->is_vni && is_digit && vielotus_is_composing(vl_engine->session));

        if (!is_word_char) {
            if (vielotus_is_composing(vl_engine->session)) {
                if (keyval == '(' || keyval == '[' || keyval == '{') {
                    vielotus_feed_char(vl_engine->session, keyval);
                    const char *committed = vielotus_get_last_text(vl_engine->session);
                    char buf[1024];
                    snprintf(buf, sizeof(buf), "%s%c", committed ? committed : "", (char)keyval);
                    IBusText *commit_text = ibus_text_new_from_string(buf);
                    ibus_engine_commit_text(engine, commit_text);
                    ibus_lotus_engine_reset_internal(vl_engine);
                    return TRUE;
                }
                char trail[2] = { (char)keyval, '\0' };
                ibus_lotus_commit_composing(vl_engine, trail);
                return TRUE;
            } else {
                vielotus_feed_char(vl_engine->session, keyval);
                return FALSE;
            }
        }

        /* Auto-flush preedit before buffer overflow */
        if (vielotus_is_composing(vl_engine->session)) {
            const char *raw_check = vielotus_get_raw_text(vl_engine->session);
            const char *comp_check = vielotus_get_composing_text(vl_engine->session);
            if ((raw_check && strlen(raw_check) >= 48) || (comp_check && strlen(comp_check) >= 48)) {
                ibus_lotus_commit_composing(vl_engine, NULL);
            }
        }

        // Telex stop-coda and tone corrections
        if (!vl_engine->is_vni && vielotus_is_composing(vl_engine->session)) {
            char lower_key = vl_tolower((char)keyval);
            uint8_t key_tone = ibus_lotus_telex_tone_for_key(lower_key);
            const char *raw_before = vielotus_get_raw_text(vl_engine->session);
            const char *comp_before = vielotus_get_composing_text(vl_engine->session);
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

        int32_t action = vielotus_feed_char(vl_engine->session, keyval);

        if (!vl_engine->is_vni && vielotus_is_composing(vl_engine->session)) {
            char lower_key = vl_tolower((char)keyval);
            if (lower_key == 'a' || lower_key == 'e' || lower_key == 'o') {
                const char *raw_after = vielotus_get_raw_text(vl_engine->session);
                const char *comp_after = vielotus_get_composing_text(vl_engine->session);
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

        if (action == VIELOTUS_ACTION_COMMIT) {
            const char *committed = vielotus_get_last_text(vl_engine->session);
            char buf[1024];
            snprintf(buf, sizeof(buf), "%s", committed ? committed : "");
            if (buf[0] != '\0') {
                IBusText *commit_text = ibus_text_new_from_string(buf);
                ibus_engine_commit_text(engine, commit_text);
            }
            ibus_lotus_engine_reset_internal(vl_engine);
            return TRUE;
        } else if (vielotus_is_composing(vl_engine->session) ||
                   action == VIELOTUS_ACTION_REPLACE ||
                   action == VIELOTUS_ACTION_CONSUMED) {
            ibus_lotus_update_preedit(vl_engine);
            return TRUE;
        }
        return FALSE;
    }

    if (vielotus_is_composing(vl_engine->session)) {
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
    engine_class->set_content_type = ibus_lotus_engine_set_content_type;
    engine_class->property_activate = ibus_lotus_engine_property_activate;
    engine_class->process_key_event = ibus_lotus_engine_process_key_event;
}

int main(int argc, char **argv) {
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

    ibus_init();
    signal(SIGUSR1, sigusr1_handler);

    IBusBus *bus = ibus_bus_new();
    if (!ibus_bus_is_connected(bus)) {
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
        IBusComponent *component = ibus_component_new_from_file("/usr/share/ibus/component/lotuskey.xml");
        if (component) {
            ibus_bus_register_component(bus, component);
        }
    }

    ibus_main();
    return 0;
}
