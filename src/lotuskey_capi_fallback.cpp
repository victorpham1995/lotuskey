/*
 * LotusKey - Portable C-ABI Fallback Implementation (libLotusKeyCAPI.so)
 *
 * Implements the 21 functions declared in include/lotuskey.h directly on top of
 * the open-source C++ core engine (core/engine.cpp).
 *
 * Used automatically by install.sh / setup_wizard.py when the precompiled x86_64
 * GLIBC 2.38 binary (lib/libLotusKeyCAPI.so) cannot load on the target system
 * (e.g., Debian 12 / Ubuntu 22.04 / RHEL 9 with GLIBC < 2.38, Alpine/Void musl,
 * or ARM64 / aarch64 / riscv64 architectures).
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "lotuskey.h"
#include "engine.h"
#include "input_method.h"
#include "utf8.h"

#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>

extern "C" {

/* Provide C23 strtoul symbol shim for older GLIBC (< 2.38) compatibility */
unsigned long __isoc23_strtoul(const char* nptr, char** endptr, int base) {
    return std::strtoul(nptr, endptr, base);
}

struct LotusKeySession {
    std::unique_ptr<lotus::Engine> engine;
    lotuskey_input_method_t input_method = LOTUSKEY_INPUT_TELEX;
    int32_t grammar_profile = LOTUSKEY_GRAMMAR_SEN_FLEX;
    bool smart_bilingual = true;
    bool modern_orthography = true;
    bool quick_telex = false;

    std::string raw_text;
    std::string composing_utf8;
    std::string last_text;
    std::u32string prev_u32;

    int32_t last_action = LOTUSKEY_ACTION_PASSTHROUGH;
    int32_t last_backspaces = 0;
    bool last_is_override = false;

    lotus::EngineFlags compute_flags() const {
        lotus::EngineFlags flags{};
        if (grammar_profile == LOTUSKEY_GRAMMAR_SEN_FLEX) {
            flags.add(lotus::EngineFlag::FreeToneMarking);
        }
        if (modern_orthography) {
            flags.add(lotus::EngineFlag::StdToneStyle);
        }
        if (smart_bilingual) {
            flags.add(lotus::EngineFlag::AutoCorrectEnabled);
        }
        flags.add(lotus::EngineFlag::W2uEnabled);
        flags.add(lotus::EngineFlag::BracketTransformEnabled);
        return flags;
    }

    void rebuild_engine() {
        auto im_id = (input_method == LOTUSKEY_INPUT_VNI)
            ? lotus::InputMethodId::Vni
            : lotus::InputMethodId::Telex;
        engine = std::make_unique<lotus::Engine>(
            lotus::cachedInputMethod(im_id),
            compute_flags()
        );
        raw_text.clear();
        composing_utf8.clear();
        prev_u32.clear();
    }

    void sync_flags() {
        if (engine) {
            engine->setFlag(compute_flags());
        }
    }

    void refresh_composing() {
        if (!engine) {
            composing_utf8.clear();
            return;
        }
        lotus::ModeSet mode{lotus::Mode::FullText};
        if (smart_bilingual && !engine->isValid(false)) {
            mode.add(lotus::Mode::EnglishMode);
        }
        std::u32string u32 = engine->processedString(mode);
        composing_utf8 = lotus::utf8::encode(u32);
    }
};

static LotusKeySession* as_session(lotuskey_session_t s) {
    return static_cast<LotusKeySession*>(s);
}

lotuskey_session_t lotuskey_create_session(void) {
    auto* s = new LotusKeySession();
    s->rebuild_engine();
    return static_cast<lotuskey_session_t>(s);
}

void lotuskey_destroy_session(lotuskey_session_t session) {
    delete as_session(session);
}

void lotuskey_reset_session(lotuskey_session_t session) {
    auto* s = as_session(session);
    if (!s) return;
    if (s->engine) {
        s->engine->reset();
    }
    s->raw_text.clear();
    s->composing_utf8.clear();
    s->prev_u32.clear();
    s->last_action = LOTUSKEY_ACTION_RESET;
    s->last_backspaces = 0;
    s->last_is_override = false;
}

void lotuskey_set_input_method(lotuskey_session_t session, lotuskey_input_method_t method) {
    auto* s = as_session(session);
    if (!s) return;
    if (s->input_method != method || !s->engine) {
        s->input_method = method;
        s->rebuild_engine();
    }
}

void lotuskey_set_grammar_profile(lotuskey_session_t session, int32_t profile) {
    auto* s = as_session(session);
    if (!s) return;
    s->grammar_profile = profile;
    s->sync_flags();
}

int32_t lotuskey_get_grammar_profile(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->grammar_profile : LOTUSKEY_GRAMMAR_SEN_FLEX;
}

void lotuskey_set_smart_bilingual(lotuskey_session_t session, bool enabled) {
    auto* s = as_session(session);
    if (!s) return;
    s->smart_bilingual = enabled;
    s->sync_flags();
}

void lotuskey_set_modern_orthography(lotuskey_session_t session, bool enabled) {
    auto* s = as_session(session);
    if (!s) return;
    s->modern_orthography = enabled;
    s->sync_flags();
}

void lotuskey_set_quick_telex(lotuskey_session_t session, bool enabled) {
    auto* s = as_session(session);
    if (!s) return;
    s->quick_telex = enabled;
}

static bool is_word_codepoint( LotusKeySession* s, uint32_t cp) {
    if ((cp >= 'a' && cp <= 'z') || (cp >= 'A' && cp <= 'Z')) {
        return true;
    }
    if (s->input_method == LOTUSKEY_INPUT_VNI && cp >= '0' && cp <= '9' && !s->raw_text.empty()) {
        return true;
    }
    return false;
}

int32_t lotuskey_feed_char(lotuskey_session_t session, uint32_t codepoint) {
    auto* s = as_session(session);
    if (!s || !s->engine) return LOTUSKEY_ACTION_PASSTHROUGH;

    s->last_is_override = false;

    if (!is_word_codepoint(s, codepoint)) {
        if (!s->raw_text.empty()) {
            return lotuskey_commit_word(session);
        }
        s->last_action = LOTUSKEY_ACTION_PASSTHROUGH;
        s->last_backspaces = 0;
        s->last_text.clear();
        return s->last_action;
    }

    /* Quick Telex expansion: cc->ch, gg->gi, kk->kh, nn->ng, qq->qu, pp->ph, tt->th */
    if (s->quick_telex && s->input_method == LOTUSKEY_INPUT_TELEX && !s->raw_text.empty()) {
        char last_c = s->raw_text.back();
        char lower_last = (last_c >= 'A' && last_c <= 'Z') ? static_cast<char>(last_c + 32) : last_c;
        char lower_curr = (codepoint >= 'A' && codepoint <= 'Z') ? static_cast<char>(codepoint + 32) : static_cast<char>(codepoint);
        if (lower_last == lower_curr) {
            char replacement = 0;
            switch (lower_curr) {
                case 'c': replacement = 'h'; break;
                case 'g': replacement = 'i'; break;
                case 'k': replacement = 'h'; break;
                case 'n': replacement = 'g'; break;
                case 'q': replacement = 'u'; break;
                case 'p': replacement = 'h'; break;
                case 't': replacement = 'h'; break;
                default: break;
            }
            if (replacement != 0) {
                if (codepoint >= 'A' && codepoint <= 'Z') {
                    replacement = static_cast<char>(replacement - 32);
                }
                codepoint = static_cast<uint32_t>(static_cast<unsigned char>(replacement));
            }
        }
    }

    lotus::utf8::appendEncoded(s->raw_text, static_cast<char32_t>(codepoint));
    s->engine->processKey(static_cast<char32_t>(codepoint), lotus::ModeSet{lotus::Mode::VietnameseMode});

    lotus::ModeSet mode{lotus::Mode::FullText};
    if (s->smart_bilingual && !s->engine->isValid(false)) {
        mode.add(lotus::Mode::EnglishMode);
    }
    std::u32string curr_u32 = s->engine->processedString(mode);
    s->composing_utf8 = lotus::utf8::encode(curr_u32);

    size_t common = 0;
    while (common < s->prev_u32.size() && common < curr_u32.size() &&
           s->prev_u32[common] == curr_u32[common]) {
        common++;
    }
    s->last_backspaces = static_cast<int32_t>(s->prev_u32.size() - common);
    s->last_text = lotus::utf8::encode(curr_u32.substr(common));
    s->prev_u32 = curr_u32;
    s->last_action = (s->last_backspaces > 0) ? LOTUSKEY_ACTION_REPLACE : LOTUSKEY_ACTION_CONSUMED;
    return s->last_action;
}

int32_t lotuskey_feed_backspace(lotuskey_session_t session) {
    auto* s = as_session(session);
    if (!s || !s->engine || s->raw_text.empty()) {
        return LOTUSKEY_ACTION_PASSTHROUGH;
    }
    s->engine->removeLastChar(true);
    if (!s->raw_text.empty()) {
        s->raw_text.pop_back();
    }
    s->refresh_composing();
    if (s->composing_utf8.empty()) {
        lotuskey_reset_session(session);
        return LOTUSKEY_ACTION_RESET;
    }
    s->prev_u32 = lotus::utf8::decode(s->composing_utf8);
    s->last_text = s->composing_utf8;
    s->last_action = LOTUSKEY_ACTION_REPLACE;
    return s->last_action;
}

int32_t lotuskey_feed_key(
    lotuskey_session_t session,
    uint32_t key_code,
    char char_code,
    uint32_t modifiers
) {
    (void)key_code;
    (void)modifiers;
    if (char_code == '\b' || char_code == 127) {
        return lotuskey_feed_backspace(session);
    }
    return lotuskey_feed_char(session, static_cast<uint32_t>(static_cast<unsigned char>(char_code)));
}

int32_t lotuskey_commit_word(lotuskey_session_t session) {
    auto* s = as_session(session);
    if (!s || !s->engine || s->raw_text.empty()) {
        return LOTUSKEY_ACTION_PASSTHROUGH;
    }
    bool valid_vn = s->engine->isValid(true);
    if (s->smart_bilingual && !valid_vn) {
        std::u32string eng_u32 = s->engine->processedString(
            lotus::ModeSet{lotus::Mode::FullText} | lotus::Mode::EnglishMode
        );
        s->last_text = lotus::utf8::encode(eng_u32);
        s->last_is_override = (s->last_text != s->composing_utf8);
    } else {
        std::u32string vn_u32 = s->engine->processedString(lotus::ModeSet{lotus::Mode::FullText});
        s->last_text = lotus::utf8::encode(vn_u32);
        s->last_is_override = false;
    }
    s->engine->reset();
    s->raw_text.clear();
    s->composing_utf8.clear();
    s->prev_u32.clear();
    s->last_backspaces = 0;
    s->last_action = LOTUSKEY_ACTION_COMMIT;
    return s->last_action;
}

int32_t lotuskey_feed_char_ex(
    lotuskey_session_t session,
    uint32_t codepoint,
    int32_t* out_backspaces,
    const char** out_text
) {
    int32_t action = lotuskey_feed_char(session, codepoint);
    if (out_backspaces) *out_backspaces = lotuskey_get_last_backspaces(session);
    if (out_text) *out_text = lotuskey_get_last_text(session);
    return action;
}

int32_t lotuskey_get_last_action(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->last_action : LOTUSKEY_ACTION_PASSTHROUGH;
}

int32_t lotuskey_get_last_backspaces(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->last_backspaces : 0;
}

const char* lotuskey_get_last_text(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->last_text.c_str() : "";
}

bool lotuskey_get_last_is_override(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->last_is_override : false;
}

bool lotuskey_is_composing(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s && !s->composing_utf8.empty();
}

const char* lotuskey_get_composing_text(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->composing_utf8.c_str() : "";
}

const char* lotuskey_get_raw_text(lotuskey_session_t session) {
    auto* s = as_session(session);
    return s ? s->raw_text.c_str() : "";
}

void lotuskey_append_context(lotuskey_session_t session, const char* context_word) {
    (void)session;
    (void)context_word;
}

void lotuskey_sync_armed_word(lotuskey_session_t session, const char* before_context_utf8) {
    auto* s = as_session(session);
    if (!s || !s->engine || !before_context_utf8 || before_context_utf8[0] == '\0') {
        return;
    }
    std::u32string u32 = lotus::utf8::decode(before_context_utf8);
    s->engine->rebuildFromText(u32);
    s->refresh_composing();
    s->raw_text = s->composing_utf8;
    s->prev_u32 = lotus::utf8::decode(s->composing_utf8);
}

const char* lotuskey_get_version(void) {
    return "1.1.0-fallback";
}

} // extern "C"
