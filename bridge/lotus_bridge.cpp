#include "engine.h"
#include "encoder.h"
#include "input_method.h"

#include <cstring>
#include <string>
#include <memory>
#include <vector>

extern "C" {

struct LotusBridge {
    std::unique_ptr<lotus::Engine> engine;
    std::u32string prev_u32;
    int input_method_id;
    uint32_t flags;
    lotus::Charset charset;
};

// Helper: UTF-32 to UTF-8
static std::string u32_to_utf8(const std::u32string& s) {
    std::string out;
    for (char32_t ch : s) {
        if (ch <= 0x7F) {
            out += static_cast<char>(ch);
        } else if (ch <= 0x7FF) {
            out += static_cast<char>(0xC0 | ((ch >> 6) & 0x1F));
            out += static_cast<char>(0x80 | (ch & 0x3F));
        } else if (ch <= 0xFFFF) {
            out += static_cast<char>(0xE0 | ((ch >> 12) & 0x0F));
            out += static_cast<char>(0x80 | ((ch >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (ch & 0x3F));
        } else if (ch <= 0x10FFFF) {
            out += static_cast<char>(0xF0 | ((ch >> 18) & 0x07));
            out += static_cast<char>(0x80 | ((ch >> 12) & 0x3F));
            out += static_cast<char>(0x80 | ((ch >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (ch & 0x3F));
        }
    }
    return out;
}

static std::string format_output(const LotusBridge* b, const std::u32string& u32) {
    if (b->charset == lotus::Charset::Unicode || b->charset == lotus::Charset::Utf8) {
        return u32_to_utf8(u32);
    }
    return lotus::encode(b->charset, u32);
}

LotusBridge* lotus_bridge_create(int method_id, uint32_t flags, int charset_id) {
    auto* b = new LotusBridge();
    b->input_method_id = method_id;
    b->flags = flags;
    b->charset = static_cast<lotus::Charset>(charset_id);
    auto im = static_cast<lotus::InputMethodId>(method_id);
    b->engine = std::make_unique<lotus::Engine>(lotus::cachedInputMethod(im), lotus::EngineFlags{flags});
    b->prev_u32 = U"";
    return b;
}

void lotus_bridge_free(LotusBridge* b) {
    delete b;
}

void lotus_bridge_reset(LotusBridge* b) {
    if (!b || !b->engine) return;
    b->engine->reset();
    b->prev_u32 = U"";
}

void lotus_bridge_remove_last(LotusBridge* b) {
    if (!b || !b->engine) return;
    b->engine->removeLastChar(false);
    b->prev_u32 = b->engine->processedString(lotus::toMask(lotus::Mode::FullText));
}

void lotus_bridge_set_flags(LotusBridge* b, uint32_t flags) {
    if (!b || !b->engine) return;
    b->flags = flags;
    b->engine->setFlag(lotus::EngineFlags{flags});
}

void lotus_bridge_set_charset(LotusBridge* b, int charset_id) {
    if (!b) return;
    b->charset = static_cast<lotus::Charset>(charset_id);
}

void lotus_bridge_set_method(LotusBridge* b, int method_id) {
    if (!b) return;
    b->input_method_id = method_id;
    auto im = static_cast<lotus::InputMethodId>(method_id);
    b->engine = std::make_unique<lotus::Engine>(lotus::cachedInputMethod(im), lotus::EngineFlags{b->flags});
    b->prev_u32 = U"";
}

int lotus_bridge_get_full_string(LotusBridge* b, char* out_buf, size_t max_len) {
    if (!b || !b->engine || !out_buf || max_len == 0) return 0;
    std::u32string curr_u32 = b->engine->processedString(lotus::toMask(lotus::Mode::FullText));
    std::string text = format_output(b, curr_u32);
    strncpy(out_buf, text.c_str(), max_len - 1);
    out_buf[max_len - 1] = '\0';
    return static_cast<int>(curr_u32.size());
}

int lotus_bridge_feed_key(
    LotusBridge* b,
    uint32_t key,
    int* out_delete_count,
    char* out_commit_buf,
    size_t commit_buf_max
) {
    if (!b || !b->engine || !out_delete_count || !out_commit_buf || commit_buf_max == 0) {
        return 0;
    }

    b->engine->processKey(static_cast<char32_t>(key), lotus::toMask(lotus::Mode::VietnameseMode));
    std::u32string curr_u32 = b->engine->processedString(lotus::toMask(lotus::Mode::FullText));

    // Find common prefix length
    size_t common_len = 0;
    while (common_len < b->prev_u32.size() && common_len < curr_u32.size() &&
           b->prev_u32[common_len] == curr_u32[common_len]) {
        common_len++;
    }

    *out_delete_count = static_cast<int>(b->prev_u32.size() - common_len);
    std::u32string commit_u32 = curr_u32.substr(common_len);
    std::string commit_str = format_output(b, commit_u32);

    strncpy(out_commit_buf, commit_str.c_str(), commit_buf_max - 1);
    out_commit_buf[commit_buf_max - 1] = '\0';

    b->prev_u32 = curr_u32;
    return 1;
}

int lotus_bridge_is_valid_word(LotusBridge* b) {
    if (!b || !b->engine) return 0;
    return b->engine->isValid(false) ? 1 : 0;
}

} // extern "C"
