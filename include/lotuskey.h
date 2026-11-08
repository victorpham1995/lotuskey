#ifndef LOTUSKEY_H
#define LOTUSKEY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/// Opaque pointer to a typing session instance
typedef void* lotuskey_session_t;

/// Input method layout type
typedef enum {
    LOTUSKEY_INPUT_TELEX = 0,
    LOTUSKEY_INPUT_VNI = 1
} lotuskey_input_method_t;

/// Input grammar profile (0 = Classic Telex/VNI, 1 = SEN Flex free-order)
typedef enum {
    LOTUSKEY_GRAMMAR_CLASSIC = 0,
    LOTUSKEY_GRAMMAR_SEN_FLEX = 1
} lotuskey_grammar_profile_t;

/// Result action returned after feeding a keystroke to the session
typedef enum {
    LOTUSKEY_ACTION_PASSTHROUGH = 0, // Key not handled; let host application process it
    LOTUSKEY_ACTION_CONSUMED    = 1, // Key consumed internally; update composing text
    LOTUSKEY_ACTION_REPLACE     = 2, // Host should delete backspaces and insert text
    LOTUSKEY_ACTION_COMMIT      = 3, // Word committed to host application
    LOTUSKEY_ACTION_RESET       = 4  // Composition cancelled or cleared
} lotuskey_action_t;

// ============================================================================
// Lifecycle Management
// ============================================================================

/// Creates a new typing session with default Telex settings.
lotuskey_session_t lotuskey_create_session(void);

/// Destroys a typing session and frees all allocated memory.
void lotuskey_destroy_session(lotuskey_session_t session);

/// Resets session composition state (clears active buffer).
void lotuskey_reset_session(lotuskey_session_t session);

// ============================================================================
// Configuration
// ============================================================================

/// Sets the input method (0 = Telex, 1 = VNI).
void lotuskey_set_input_method(lotuskey_session_t session, lotuskey_input_method_t method);

/// Sets the grammar profile (0 = Classic, 1 = SEN Flex).
void lotuskey_set_grammar_profile(lotuskey_session_t session, int32_t profile);

/// Returns the active grammar profile (0 = Classic, 1 = SEN Flex).
int32_t lotuskey_get_grammar_profile(lotuskey_session_t session);

/// Enables or disables smart bilingual auto-restore.
void lotuskey_set_smart_bilingual(lotuskey_session_t session, bool enabled);

/// Enables or disables modern diacritic orthography (òa/òe vs oà/oè).
void lotuskey_set_modern_orthography(lotuskey_session_t session, bool enabled);

/// Enables or disables Quick Telex shorthand.
void lotuskey_set_quick_telex(lotuskey_session_t session, bool enabled);

// ============================================================================
// Keystroke Processing
// ============================================================================

/// Feeds a single UTF-8 codepoint into the session.
/// Returns the resulting action code (0..4).
int32_t lotuskey_feed_char(lotuskey_session_t session, uint32_t codepoint);

/// Feeds a backspace keystroke into the session.
/// Returns the resulting action code (0..4).
int32_t lotuskey_feed_backspace(lotuskey_session_t session);

/// Feeds a full key event with scan code, ASCII char, and modifier flags.
/// Returns the resulting action code (0..4).
int32_t lotuskey_feed_key(
    lotuskey_session_t session,
    uint32_t key_code,
    char char_code,
    uint32_t modifiers
);

/// Explicitly commits the current composing word (triggers Smart Bilingual and macro resolution).
/// Returns the resulting action code (0..4).
int32_t lotuskey_commit_word(lotuskey_session_t session);

/// Convenience function feeding character and extracting backspaces and replacement text directly.
int32_t lotuskey_feed_char_ex(
    lotuskey_session_t session,
    uint32_t codepoint,
    int32_t* out_backspaces,
    const char** out_text
);

/// Returns the action from the most recent feed call.
int32_t lotuskey_get_last_action(lotuskey_session_t session);

/// Returns the number of trailing UTF-16 code units to delete from the most recent feed call.
int32_t lotuskey_get_last_backspaces(lotuskey_session_t session);

/// Returns the replacement string to insert from the most recent feed call (valid until next feed).
const char* lotuskey_get_last_text(lotuskey_session_t session);

/// Returns true if the most recent commit action replaced the composed word (e.g. Smart Bilingual restore or Macro).
bool lotuskey_get_last_is_override(lotuskey_session_t session);

// ============================================================================
// Buffer & State Inspection
// ============================================================================

/// Checks whether the session is currently composing a syllable.
bool lotuskey_is_composing(lotuskey_session_t session);

/// Returns the current composing string (UTF-8 encoded, valid until next call).
const char* lotuskey_get_composing_text(lotuskey_session_t session);

/// Returns the raw typed ASCII string before Vietnamese transformation.
const char* lotuskey_get_raw_text(lotuskey_session_t session);

/// Appends preceding text into the session's context window for bilingual detection.
void lotuskey_append_context(lotuskey_session_t session, const char* context_word);

/// Synchronizes and arms the word immediately preceding the cursor when idle, enabling seamless post-commit tone edits and backspacing.
void lotuskey_sync_armed_word(lotuskey_session_t session, const char* before_context_utf8);

// ============================================================================
// Version & Metadata
// ============================================================================

/// Returns the SemVer string of the LotusKey Core engine (e.g. "1.0.0").
const char* lotuskey_get_version(void);

#ifdef __cplusplus
}
#endif

#endif // LOTUSKEY_H
