/*
 * LotusKey - Minimal ABI-Compatible IBus Fallback Header
 * Allows building ibus-engine-lotuskey on any Linux distribution (Ubuntu, Fedora,
 * Arch, openSUSE, Alpine, Void, NixOS) without requiring libibus-1.0-dev / ibus-devel.
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */

#ifndef __IBUS_FALLBACK_H__
#define __IBUS_FALLBACK_H__

#include <glib.h>
#include <glib-object.h>
#include <gio/gio.h>

G_BEGIN_DECLS

/* ============================================================================
 * IBus Modifier Masks, Capabilities, and Enums
 * ============================================================================ */

typedef enum {
    IBUS_SHIFT_MASK    = 1 << 0,
    IBUS_LOCK_MASK     = 1 << 1,
    IBUS_CONTROL_MASK  = 1 << 2,
    IBUS_MOD1_MASK     = 1 << 3,
    IBUS_MOD2_MASK     = 1 << 4,
    IBUS_MOD3_MASK     = 1 << 5,
    IBUS_MOD4_MASK     = 1 << 6,
    IBUS_MOD5_MASK     = 1 << 7,
    IBUS_BUTTON1_MASK  = 1 << 8,
    IBUS_BUTTON2_MASK  = 1 << 9,
    IBUS_BUTTON3_MASK  = 1 << 10,
    IBUS_BUTTON4_MASK  = 1 << 11,
    IBUS_BUTTON5_MASK  = 1 << 12,
    IBUS_HANDLED_MASK  = 1 << 24,
    IBUS_FORWARD_MASK  = 1 << 25,
    IBUS_IGNORED_MASK  = IBUS_FORWARD_MASK,
    IBUS_SUPER_MASK    = 1 << 26,
    IBUS_HYPER_MASK    = 1 << 27,
    IBUS_META_MASK     = 1 << 28,
    IBUS_RELEASE_MASK  = 1 << 30,
    IBUS_MODIFIER_MASK = 0x5f001fff
} IBusModifierType;

typedef enum {
    IBUS_CAP_PREEDIT_TEXT       = 1 << 0,
    IBUS_CAP_AUXILIARY_TEXT     = 1 << 1,
    IBUS_CAP_LOOKUP_TABLE       = 1 << 2,
    IBUS_CAP_FOCUS              = 1 << 3,
    IBUS_CAP_PROPERTY           = 1 << 4,
    IBUS_CAP_SURROUNDING_TEXT   = 1 << 5,
    IBUS_CAP_OSK                = 1 << 6,
    IBUS_CAP_SYNC_PROCESS_KEY   = 1 << 7
} IBusCapabilite;

typedef enum {
    IBUS_ENGINE_PREEDIT_CLEAR   = 0,
    IBUS_ENGINE_PREEDIT_COMMIT  = 1
} IBusPreeditFocusMode;

typedef enum {
    IBUS_INPUT_PURPOSE_FREE_FORM,
    IBUS_INPUT_PURPOSE_ALPHA,
    IBUS_INPUT_PURPOSE_DIGITS,
    IBUS_INPUT_PURPOSE_NUMBER,
    IBUS_INPUT_PURPOSE_PHONE,
    IBUS_INPUT_PURPOSE_URL,
    IBUS_INPUT_PURPOSE_EMAIL,
    IBUS_INPUT_PURPOSE_NAME,
    IBUS_INPUT_PURPOSE_PASSWORD,
    IBUS_INPUT_PURPOSE_PIN,
    IBUS_INPUT_PURPOSE_TERMINAL,
    IBUS_INPUT_PURPOSE_DATE,
    IBUS_INPUT_PURPOSE_TIME,
    IBUS_INPUT_PURPOSE_DATETIME
} IBusInputPurpose;

typedef enum {
    IBUS_INPUT_HINT_NONE                = 0,
    IBUS_INPUT_HINT_SPELLCHECK          = 1 << 0,
    IBUS_INPUT_HINT_NO_SPELLCHECK       = 1 << 1,
    IBUS_INPUT_HINT_WORD_COMPLETION     = 1 << 2,
    IBUS_INPUT_HINT_LOWERCASE           = 1 << 3,
    IBUS_INPUT_HINT_UPPERCASE_CHARS     = 1 << 4,
    IBUS_INPUT_HINT_UPPERCASE_WORDS     = 1 << 5,
    IBUS_INPUT_HINT_UPPERCASE_SENTENCES = 1 << 6,
    IBUS_INPUT_HINT_INHIBIT_OSK         = 1 << 7,
    IBUS_INPUT_HINT_VERTICAL_WRITING    = 1 << 8,
    IBUS_INPUT_HINT_EMOJI               = 1 << 9,
    IBUS_INPUT_HINT_NO_EMOJI            = 1 << 10,
    IBUS_INPUT_HINT_PRIVATE             = 1 << 11,
    IBUS_INPUT_HINT_HIDDEN_TEXT         = 1 << 12,
    IBUS_INPUT_HINT_LATIN               = 1 << 13,
    IBUS_INPUT_HINT_MULTILINE           = 1 << 14
} IBusInputHints;

typedef enum {
    IBUS_ATTR_TYPE_UNDERLINE  = 1,
    IBUS_ATTR_TYPE_FOREGROUND = 2,
    IBUS_ATTR_TYPE_BACKGROUND = 3,
    IBUS_ATTR_TYPE_HINT       = 4
} IBusAttrType;

typedef enum {
    IBUS_ATTR_UNDERLINE_NONE   = 0,
    IBUS_ATTR_UNDERLINE_SINGLE = 1,
    IBUS_ATTR_UNDERLINE_DOUBLE = 2,
    IBUS_ATTR_UNDERLINE_LOW    = 3,
    IBUS_ATTR_UNDERLINE_ERROR  = 4
} IBusAttrUnderline;

typedef enum {
    PROP_TYPE_NORMAL    = 0,
    PROP_TYPE_TOGGLE    = 1,
    PROP_TYPE_RADIO     = 2,
    PROP_TYPE_MENU      = 3,
    PROP_TYPE_SEPARATOR = 4
} IBusPropType;

typedef enum {
    PROP_STATE_UNCHECKED    = 0,
    PROP_STATE_CHECKED      = 1,
    PROP_STATE_INCONSISTENT = 2
} IBusPropState;

typedef struct _IBusRectangle {
    gint x;
    gint y;
    gint width;
    gint height;
} IBusRectangle;

/* ============================================================================
 * IBus Keysyms
 * ============================================================================ */

#define IBUS_KEY_BackSpace        0xff08
#define IBUS_KEY_Tab              0xff09
#define IBUS_KEY_Linefeed         0xff0a
#define IBUS_KEY_Return           0xff0d
#define IBUS_KEY_Escape           0xff1b
#define IBUS_KEY_Delete           0xffff
#define IBUS_KEY_Home             0xff50
#define IBUS_KEY_Insert           0xff63
#define IBUS_KEY_KP_Tab           0xff89
#define IBUS_KEY_KP_Enter         0xff8d
#define IBUS_KEY_KP_Home          0xff95
#define IBUS_KEY_KP_Delete        0xff9f
#define IBUS_KEY_Shift_L          0xffe1
#define IBUS_KEY_Shift_R          0xffe2
#define IBUS_KEY_Control_L        0xffe3
#define IBUS_KEY_Control_R        0xffe4
#define IBUS_KEY_Caps_Lock        0xffe5
#define IBUS_KEY_Shift_Lock       0xffe6
#define IBUS_KEY_ISO_Level3_Shift 0xfe03
#define IBUS_KEY_ISO_Left_Tab     0xfe20
#define IBUS_KEY_space            0x0020

/* ============================================================================
 * Object Hierarchy: IBusObject -> IBusService -> IBusEngine
 * ============================================================================ */

typedef struct _IBusObject IBusObject;
typedef struct _IBusObjectClass IBusObjectClass;
typedef struct _IBusObjectPrivate IBusObjectPrivate;

struct _IBusObject {
    GInitiallyUnowned parent;
    guint32 flags;
    IBusObjectPrivate *priv;
};

struct _IBusObjectClass {
    GInitiallyUnownedClass parent;
    void (* destroy) (IBusObject *object);
    gpointer pdummy[7];
};

GType ibus_object_get_type(void);

typedef struct _IBusService IBusService;
typedef struct _IBusServiceClass IBusServiceClass;
typedef struct _IBusServicePrivate IBusServicePrivate;

struct _IBusService {
    IBusObject parent;
    IBusServicePrivate *priv;
};

struct _IBusServiceClass {
    IBusObjectClass parent;
    void (* service_method_call) (IBusService *service,
                                  GDBusConnection *connection,
                                  const gchar *sender,
                                  const gchar *object_path,
                                  const gchar *interface_name,
                                  const gchar *method_name,
                                  GVariant *parameters,
                                  GDBusMethodInvocation *invocation);
    GVariant * (* service_get_property) (IBusService *service,
                                         GDBusConnection *connection,
                                         const gchar *sender,
                                         const gchar *object_path,
                                         const gchar *interface_name,
                                         const gchar *property_name,
                                         GError **error);
    gboolean (* service_set_property) (IBusService *service,
                                       GDBusConnection *connection,
                                       const gchar *sender,
                                       const gchar *object_path,
                                       const gchar *interface_name,
                                       const gchar *property_name,
                                       GVariant *value,
                                       GError **error);
    gpointer pdummy[5];
};

GType ibus_service_get_type(void);

#define IBUS_TYPE_ENGINE            (ibus_engine_get_type())
#define IBUS_ENGINE(obj)            (G_TYPE_CHECK_INSTANCE_CAST((obj), IBUS_TYPE_ENGINE, IBusEngine))
#define IBUS_ENGINE_CLASS(klass)    (G_TYPE_CHECK_CLASS_CAST((klass), IBUS_TYPE_ENGINE, IBusEngineClass))
#define IBUS_IS_ENGINE(obj)         (G_TYPE_CHECK_INSTANCE_TYPE((obj), IBUS_TYPE_ENGINE))
#define IBUS_IS_ENGINE_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE((klass), IBUS_TYPE_ENGINE))
#define IBUS_ENGINE_GET_CLASS(obj)  (G_TYPE_INSTANCE_GET_CLASS((obj), IBUS_TYPE_ENGINE, IBusEngineClass))

typedef struct _IBusEngine IBusEngine;
typedef struct _IBusEngineClass IBusEngineClass;
typedef struct _IBusEnginePrivate IBusEnginePrivate;

struct _IBusEngine {
    IBusService parent;
    IBusEnginePrivate *priv;
    gboolean enabled;
    gboolean has_focus;
    IBusRectangle cursor_area;
    guint client_capabilities;
};

struct _IBusEngineClass {
    IBusServiceClass parent;

    gboolean (* process_key_event) (IBusEngine *engine,
                                    guint keyval,
                                    guint keycode,
                                    guint state);
    void (* focus_in)              (IBusEngine *engine);
    void (* focus_out)             (IBusEngine *engine);
    void (* reset)                 (IBusEngine *engine);
    void (* enable)                (IBusEngine *engine);
    void (* disable)               (IBusEngine *engine);
    void (* set_cursor_location)   (IBusEngine *engine,
                                    gint x,
                                    gint y,
                                    gint w,
                                    gint h);
    void (* set_capabilities)      (IBusEngine *engine,
                                    guint caps);
    void (* page_up)               (IBusEngine *engine);
    void (* page_down)             (IBusEngine *engine);
    void (* cursor_up)             (IBusEngine *engine);
    void (* cursor_down)           (IBusEngine *engine);
    void (* property_activate)     (IBusEngine *engine,
                                    const gchar *prop_name,
                                    guint prop_state);
    void (* property_show)         (IBusEngine *engine,
                                    const gchar *prop_name);
    void (* property_hide)         (IBusEngine *engine,
                                    const gchar *prop_name);
    void (* candidate_clicked)     (IBusEngine *engine,
                                    guint index,
                                    guint button,
                                    guint state);
    void (* set_surrounding_text)  (IBusEngine *engine,
                                    GObject *text,
                                    guint cursor_pos,
                                    guint anchor_pos);
    void (* process_hand_writing_event) (IBusEngine *engine,
                                         const gdouble *coordinates,
                                         guint coordinates_len);
    void (* cancel_hand_writing)   (IBusEngine *engine,
                                    guint n_strokes);
    void (* set_content_type)      (IBusEngine *engine,
                                    guint purpose,
                                    guint hints);
    void (* focus_in_id)           (IBusEngine *engine,
                                    const gchar *object_path,
                                    const gchar *client);
    void (* focus_out_id)          (IBusEngine *engine,
                                    const gchar *object_path);
    gpointer pdummy[2];
};

GType ibus_engine_get_type(void);

/* ============================================================================
 * Opaque Types & Function Declarations
 * ============================================================================ */

typedef struct _IBusText IBusText;
typedef struct _IBusProperty IBusProperty;
typedef struct _IBusPropList IBusPropList;
typedef struct _IBusBus IBusBus;
typedef struct _IBusFactory IBusFactory;
typedef struct _IBusComponent IBusComponent;

void           ibus_init(void);
void           ibus_main(void);
void           ibus_quit(void);

IBusText      *ibus_text_new_from_string(const gchar *str);
IBusText      *ibus_text_new_from_static_string(const gchar *str);
guint          ibus_text_get_length(IBusText *text);
void           ibus_text_append_attribute(IBusText *text,
                                          guint type,
                                          guint value,
                                          guint start_index,
                                          gint end_index);

IBusPropList  *ibus_prop_list_new(void);
void           ibus_prop_list_append(IBusPropList *prop_list, IBusProperty *prop);

IBusProperty  *ibus_property_new(const gchar *key,
                                 IBusPropType type,
                                 IBusText *label,
                                 const gchar *icon,
                                 IBusText *tooltip,
                                 gboolean sensitive,
                                 gboolean visible,
                                 IBusPropState state,
                                 IBusPropList *prop_list);

void           ibus_engine_commit_text(IBusEngine *engine, IBusText *text);
void           ibus_engine_update_preedit_text_with_mode(IBusEngine *engine,
                                                         IBusText *text,
                                                         guint cursor_pos,
                                                         gboolean visible,
                                                         IBusPreeditFocusMode mode);
void           ibus_engine_hide_preedit_text(IBusEngine *engine);
void           ibus_engine_delete_surrounding_text(IBusEngine *engine,
                                                   gint offset,
                                                   guint nchars);
void           ibus_engine_forward_key_event(IBusEngine *engine,
                                             guint keyval,
                                             guint keycode,
                                             guint state);
void           ibus_engine_register_properties(IBusEngine *engine,
                                               IBusPropList *prop_list);
const gchar   *ibus_engine_get_name(IBusEngine *engine);
void           ibus_engine_get_content_type(IBusEngine *engine,
                                            guint *purpose,
                                            guint *hints);

IBusBus       *ibus_bus_new(void);
gboolean       ibus_bus_is_connected(IBusBus *bus);
GDBusConnection *ibus_bus_get_connection(IBusBus *bus);
guint32        ibus_bus_request_name(IBusBus *bus,
                                     const gchar *name,
                                     guint32 flags);
gboolean       ibus_bus_register_component(IBusBus *bus,
                                           IBusComponent *component);

IBusFactory   *ibus_factory_new(GDBusConnection *connection);
void           ibus_factory_add_engine(IBusFactory *factory,
                                       const gchar *name,
                                       GType engine_type);

IBusComponent *ibus_component_new_from_file(const gchar *filename);

G_END_DECLS

#endif /* __IBUS_FALLBACK_H__ */
