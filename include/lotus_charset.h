#ifndef LOTUS_CHARSET_H
#define LOTUS_CHARSET_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>

/*
 * Charset IDs supported by LotusKey:
 *   0           : Unicode (UTF-8 dựng sẵn - NFC)
 *   9  or 31    : Unicode Tổ hợp (Combining - NFD)
 *   5  or 27    : TCVN3 (ABC)
 *   12 or 34    : VNI Windows
 *   10          : VIQR
 *   99          : ASCII (Strip diacritics)
 */
enum {
    LOTUS_CHARSET_UNICODE          = 0,
    LOTUS_CHARSET_TCVN3_ENUM       = 5,
    LOTUS_CHARSET_COMBINING_ENUM   = 9,
    LOTUS_CHARSET_VIQR_ENUM        = 10,
    LOTUS_CHARSET_VNI_WIN_ENUM     = 12,
    LOTUS_CHARSET_TCVN3_CFG        = 27,
    LOTUS_CHARSET_COMBINING_CFG    = 31,
    LOTUS_CHARSET_VNI_WIN_CFG      = 34,
    LOTUS_CHARSET_ASCII_STRIP      = 99
};

typedef struct {
    const char *utf8_nfc;
    const char *combining;
    const char *tcvn3;
    const char *vni_win;
    const char *ascii_base;
} LotusCharsetEntry;

static const LotusCharsetEntry kLotusCharsetTable[] = {
    { "À", "À", "µ", "AØ", "A" }, { "Á", "Á", "¸", "AÙ", "A" }, { "Â", "Â", "¢", "AÂ", "A" }, { "Ã", "Ã", "·", "AÕ", "A" },
    { "È", "È", "Ì", "EØ", "E" }, { "É", "É", "Ð", "EÙ", "E" }, { "Ê", "Ê", "£", "EÂ", "E" }, { "Ì", "Ì", "×", "Ì", "I" },
    { "Í", "Í", "Ý", "Í", "I" },  { "Ò", "Ò", "ß", "OØ", "O" }, { "Ó", "Ó", "ã", "OÙ", "O" }, { "Ô", "Ô", "¤", "OÂ", "O" },
    { "Õ", "Õ", "â", "OÕ", "O" }, { "Ù", "Ù", "ï", "UØ", "U" }, { "Ú", "Ú", "ó", "UÙ", "U" }, { "Ý", "Ý", "ý", "YÙ", "Y" },
    { "à", "à", "µ", "aø", "a" }, { "á", "á", "¸", "aù", "a" }, { "â", "â", "©", "aâ", "a" }, { "ã", "ã", "·", "aõ", "a" },
    { "è", "è", "Ì", "eø", "e" }, { "é", "é", "Ð", "eù", "e" }, { "ê", "ê", "ª", "eâ", "e" }, { "ì", "ì", "×", "ì", "i" },
    { "í", "í", "Ý", "í", "i" },  { "ò", "ò", "ß", "oø", "o" }, { "ó", "ó", "ã", "où", "o" }, { "ô", "ô", "«", "oâ", "o" },
    { "õ", "õ", "â", "oõ", "o" }, { "ù", "ù", "ï", "uø", "u" }, { "ú", "ú", "ó", "uù", "u" }, { "ý", "ý", "ý", "yù", "y" },
    { "Ă", "Ă", "¡", "AÊ", "A" }, { "ă", "ă", "¨", "aê", "a" }, { "Đ", "Đ", "§", "Ñ", "D" },  { "đ", "đ", "®", "ñ", "d" },
    { "Ĩ", "Ĩ", "Ü", "Ó", "I" },  { "ĩ", "ĩ", "Ü", "ó", "i" },  { "Ũ", "Ũ", "ò", "UÕ", "U" }, { "ũ", "ũ", "ò", "uõ", "u" },
    { "Ơ", "Ơ", "¥", "Ô", "O" },  { "ơ", "ơ", "¬", "ô", "o" },  { "Ư", "Ư", "¦", "Ö", "U" },  { "ư", "ư", "\xc2\xad", "ö", "u" },
    { "Ạ", "Ạ", "¹", "AÏ", "A" }, { "ạ", "ạ", "¹", "aï", "a" }, { "Ả", "Ả", "¶", "AÛ", "A" }, { "ả", "ả", "¶", "aû", "a" },
    { "Ấ", "Ấ", "Ê", "AÁ", "A" }, { "ấ", "ấ", "Ê", "aá", "a" }, { "Ầ", "Ầ", "Ç", "AÀ", "A" }, { "ầ", "ầ", "Ç", "aà", "a" },
    { "Ẩ", "Ẩ", "È", "AÅ", "A" }, { "ẩ", "ẩ", "È", "aå", "a" }, { "Ẫ", "Ẫ", "É", "AÃ", "A" }, { "ẫ", "ẫ", "É", "aã", "a" },
    { "Ậ", "Ậ", "Ë", "AÄ", "A" }, { "ậ", "ậ", "Ë", "aä", "a" }, { "Ắ", "Ắ", "¾", "AÉ", "A" }, { "ắ", "ắ", "¾", "aé", "a" },
    { "Ằ", "Ằ", "»", "AÈ", "A" }, { "ằ", "ằ", "»", "aè", "a" }, { "Ẳ", "Ẳ", "¼", "AÚ", "A" }, { "ẳ", "ẳ", "¼", "aú", "a" },
    { "Ẵ", "Ẵ", "½", "AÜ", "A" }, { "ẵ", "ẵ", "½", "aü", "a" }, { "Ặ", "Ặ", "Æ", "AË", "A" }, { "ặ", "ặ", "Æ", "aë", "a" },
    { "Ẹ", "Ẹ", "Ñ", "EÏ", "E" }, { "ẹ", "ẹ", "Ñ", "eï", "e" }, { "Ẻ", "Ẻ", "Î", "EÛ", "E" }, { "ẻ", "ẻ", "Î", "eû", "e" },
    { "Ẽ", "Ẽ", "Ï", "EÕ", "E" }, { "ẽ", "ẽ", "Ï", "eõ", "e" }, { "Ế", "Ế", "Õ", "EÁ", "E" }, { "ế", "ế", "Õ", "eá", "e" },
    { "Ề", "Ề", "Ò", "EÀ", "E" }, { "ề", "ề", "Ò", "eà", "e" }, { "Ể", "Ể", "Ó", "EÅ", "E" }, { "ể", "ể", "Ó", "eå", "e" },
    { "Ễ", "Ễ", "Ô", "EÃ", "E" }, { "ễ", "ễ", "Ô", "eã", "e" }, { "Ệ", "Ệ", "Ö", "EÄ", "E" }, { "ệ", "ệ", "Ö", "eä", "e" },
    { "Ỉ", "Ỉ", "Ø", "Æ", "I" },  { "ỉ", "ỉ", "Ø", "æ", "i" },  { "Ị", "Ị", "Þ", "Ò", "I" },  { "ị", "ị", "Þ", "ò", "i" },
    { "Ọ", "Ọ", "ä", "OÏ", "O" }, { "ọ", "ọ", "ä", "oï", "o" }, { "Ỏ", "Ỏ", "á", "OÛ", "O" }, { "ỏ", "ỏ", "á", "oû", "o" },
    { "Ố", "Ố", "è", "OÁ", "O" }, { "ố", "ố", "è", "oá", "o" }, { "Ồ", "Ồ", "å", "OÀ", "O" }, { "ồ", "ồ", "å", "oà", "o" },
    { "Ổ", "Ổ", "æ", "OÅ", "O" }, { "ổ", "ổ", "æ", "oå", "o" }, { "Ỗ", "Ỗ", "ç", "OÃ", "O" }, { "ỗ", "ỗ", "ç", "oã", "o" },
    { "Ộ", "Ộ", "é", "OÄ", "O" }, { "ộ", "ộ", "é", "oä", "o" }, { "Ớ", "Ớ", "í", "ÔÙ", "O" }, { "ớ", "ớ", "í", "ôù", "o" },
    { "Ờ", "Ờ", "ê", "ÔØ", "O" }, { "ờ", "ờ", "ê", "ôø", "o" }, { "Ở", "Ở", "ë", "ÔÛ", "O" }, { "ở", "ở", "ë", "ôû", "o" },
    { "Ỡ", "Ỡ", "ì", "ÔÕ", "O" }, { "ỡ", "ỡ", "ì", "ôõ", "o" }, { "Ợ", "Ợ", "î", "ÔÏ", "O" }, { "ợ", "ợ", "î", "ôï", "o" },
    { "Ụ", "Ụ", "ô", "UÏ", "U" }, { "ụ", "ụ", "ô", "uï", "u" }, { "Ủ", "Ủ", "ñ", "UÛ", "U" }, { "ủ", "ủ", "ñ", "uû", "u" },
    { "Ứ", "Ứ", "ø", "ÖÙ", "U" }, { "ứ", "ứ", "ø", "öù", "u" }, { "Ừ", "Ừ", "õ", "ÖØ", "U" }, { "ừ", "ừ", "õ", "öø", "u" },
    { "Ử", "Ử", "ö", "ÖÛ", "U" }, { "ử", "ử", "ö", "öû", "u" }, { "Ữ", "Ữ", "÷", "ÖÕ", "U" }, { "ữ", "ữ", "÷", "öõ", "u" },
    { "Ự", "Ự", "ù", "ÖÏ", "U" }, { "ự", "ự", "ù", "öï", "u" }, { "Ỳ", "Ỳ", "ú", "YØ", "Y" }, { "ỳ", "ỳ", "ú", "yø", "y" },
    { "Ỵ", "Ỵ", "þ", "Î", "Y" },  { "ỵ", "ỵ", "þ", "î", "y" },  { "Ỷ", "Ỷ", "û", "YÛ", "Y" }, { "ỷ", "ỷ", "û", "yû", "y" },
    { "Ỹ", "Ỹ", "ü", "YÕ", "Y" }, { "ỹ", "ỹ", "ü", "yõ", "y" }
};

static inline size_t lotus_utf8_seq_len(unsigned char b) {
    if ((b & 0x80) == 0) return 1;
    if ((b & 0xE0) == 0xC0) return 2;
    if ((b & 0xF0) == 0xE0) return 3;
    if ((b & 0xF8) == 0xF0) return 4;
    return 1;
}

static inline void lotus_convert_charset(const char *src_utf8, int charset_id, char *out_buf, size_t out_cap) {
    if (!out_buf || out_cap == 0) return;
    if (!src_utf8 || src_utf8[0] == '\0') {
        out_buf[0] = '\0';
        return;
    }
    if (charset_id == LOTUS_CHARSET_UNICODE) {
        snprintf(out_buf, out_cap, "%s", src_utf8);
        return;
    }

    size_t out_len = 0;
    const char *p = src_utf8;
    const size_t table_len = sizeof(kLotusCharsetTable) / sizeof(kLotusCharsetTable[0]);

    while (*p && out_len + 8 < out_cap) {
        size_t clen = lotus_utf8_seq_len((unsigned char)*p);
        if (clen == 1) {
            out_buf[out_len++] = *p++;
            continue;
        }
        const char *replacement = NULL;
        for (size_t i = 0; i < table_len; i++) {
            const char *nfc = kLotusCharsetTable[i].utf8_nfc;
            if (strlen(nfc) == clen && strncmp(p, nfc, clen) == 0) {
                if (charset_id == LOTUS_CHARSET_COMBINING_CFG || charset_id == LOTUS_CHARSET_COMBINING_ENUM) {
                    replacement = kLotusCharsetTable[i].combining;
                } else if (charset_id == LOTUS_CHARSET_TCVN3_CFG || charset_id == LOTUS_CHARSET_TCVN3_ENUM) {
                    replacement = kLotusCharsetTable[i].tcvn3;
                } else if (charset_id == LOTUS_CHARSET_VNI_WIN_CFG || charset_id == LOTUS_CHARSET_VNI_WIN_ENUM) {
                    replacement = kLotusCharsetTable[i].vni_win;
                } else if (charset_id == LOTUS_CHARSET_ASCII_STRIP) {
                    replacement = kLotusCharsetTable[i].ascii_base;
                }
                break;
            }
        }
        if (replacement) {
            size_t rlen = strlen(replacement);
            if (out_len + rlen < out_cap) {
                memcpy(out_buf + out_len, replacement, rlen);
                out_len += rlen;
            }
        } else {
            for (size_t k = 0; k < clen && p[k] && out_len + 1 < out_cap; k++) {
                out_buf[out_len++] = p[k];
            }
        }
        p += clen;
    }
    out_buf[out_len] = '\0';
}

/*
 * Decode from TCVN3 / VNI Windows / Unicode Combining (NFD) back to Unicode NFC
 * Includes Title-Case VNI Windows ("Aùo", "Oâng", "Uûy") and TCVN3 ALL-CAPS context detection.
 */
static inline void lotus_decode_to_unicode_nfc(const char *src_text, int src_charset_id, char *out_buf, size_t out_cap) {
    if (!out_buf || out_cap == 0) return;
    if (!src_text || src_text[0] == '\0') {
        out_buf[0] = '\0';
        return;
    }
    if (src_charset_id == LOTUS_CHARSET_UNICODE) {
        snprintf(out_buf, out_cap, "%s", src_text);
        return;
    }

    size_t out_len = 0;
    const char *p = src_text;
    const size_t table_len = sizeof(kLotusCharsetTable) / sizeof(kLotusCharsetTable[0]);
    const int is_tcvn3 = (src_charset_id == LOTUS_CHARSET_TCVN3_CFG || src_charset_id == LOTUS_CHARSET_TCVN3_ENUM);
    const int is_vni   = (src_charset_id == LOTUS_CHARSET_VNI_WIN_CFG || src_charset_id == LOTUS_CHARSET_VNI_WIN_ENUM);
    const int is_comb  = (src_charset_id == LOTUS_CHARSET_COMBINING_CFG || src_charset_id == LOTUS_CHARSET_COMBINING_ENUM);

    int has_any_lower_ascii = 0;
    int has_any_upper_ascii = 0;
    for (const char *s = src_text; *s; s++) {
        if (*s >= 'a' && *s <= 'z') has_any_lower_ascii = 1;
        if (*s >= 'A' && *s <= 'Z') has_any_upper_ascii = 1;
    }

    while (*p && out_len + 8 < out_cap) {
        size_t best_len = 0;
        const char *best_nfc = NULL;
        int best_is_lower = 0;

        /* Determine if current TCVN3 token is in an ALL-CAPS word context */
        int prefer_tcvn_upper = 0;
        if (is_tcvn3) {
            int prev_upper = (p > src_text && p[-1] >= 'A' && p[-1] <= 'Z');
            int prev2_upper = (p > src_text + 1 && p[-2] >= 'A' && p[-2] <= 'Z');
            if (prev_upper && (prev2_upper || (!has_any_lower_ascii && has_any_upper_ascii))) {
                prefer_tcvn_upper = 1;
            }
        }

        for (size_t i = 0; i < table_len; i++) {
            const char *pattern = NULL;
            if (is_tcvn3) pattern = kLotusCharsetTable[i].tcvn3;
            else if (is_vni) pattern = kLotusCharsetTable[i].vni_win;
            else if (is_comb) pattern = kLotusCharsetTable[i].combining;
            if (!pattern || !pattern[0]) continue;

            size_t plen = strlen(pattern);
            int cur_is_lower = (kLotusCharsetTable[i].ascii_base[0] >= 'a' && kLotusCharsetTable[i].ascii_base[0] <= 'z');
            if (strncmp(p, pattern, plen) == 0) {
                int next_upper = (p[plen] >= 'A' && p[plen] <= 'Z');
                int want_upper = prefer_tcvn_upper || (is_tcvn3 && next_upper);
                if (plen > best_len ||
                    (plen == best_len && is_tcvn3 && ((want_upper && !cur_is_lower && best_is_lower) || (!want_upper && cur_is_lower && !best_is_lower)))) {
                    best_len = plen;
                    best_nfc = kLotusCharsetTable[i].utf8_nfc;
                    best_is_lower = cur_is_lower;
                }
            } else if (is_vni && !cur_is_lower) {
                /* Check Title-Case VNI Windows: uppercase base vowel + lowercase VNI tone mark (e.g. "Aù", "Oâ", "Öù") */
                size_t low_idx = (i < 16) ? (i + 16) : ((i >= 32 && (i % 2 == 0)) ? (i + 1) : table_len);
                if (low_idx < table_len) {
                    const char *up_vni = kLotusCharsetTable[i].vni_win;
                    const char *lo_vni = kLotusCharsetTable[low_idx].vni_win;
                    size_t up_c1 = lotus_utf8_seq_len((unsigned char)up_vni[0]);
                    size_t lo_c1 = lotus_utf8_seq_len((unsigned char)lo_vni[0]);
                    if (strlen(up_vni) > up_c1 && strlen(lo_vni) > lo_c1) {
                        char mixed_vni[16];
                        snprintf(mixed_vni, sizeof(mixed_vni), "%.*s%s", (int)up_c1, up_vni, lo_vni + lo_c1);
                        size_t mlen = strlen(mixed_vni);
                        if (mlen > best_len && strncmp(p, mixed_vni, mlen) == 0) {
                            best_len = mlen;
                            best_nfc = kLotusCharsetTable[i].utf8_nfc;
                            best_is_lower = 0;
                        }
                    }
                }
            }
        }

        if (best_nfc && best_len > 0) {
            size_t nlen = strlen(best_nfc);
            if (out_len + nlen < out_cap) {
                memcpy(out_buf + out_len, best_nfc, nlen);
                out_len += nlen;
            }
            p += best_len;
        } else {
            size_t clen = lotus_utf8_seq_len((unsigned char)*p);
            for (size_t k = 0; k < clen && p[k] && out_len + 1 < out_cap; k++) {
                out_buf[out_len++] = p[k];
            }
            p += clen;
        }
    }
    out_buf[out_len] = '\0';
}

static inline void lotus_transcode_charset(const char *src_text, int src_charset_id, int dst_charset_id, char *out_buf, size_t out_cap) {
    if (!out_buf || out_cap == 0) return;
    if (src_charset_id == dst_charset_id) {
        snprintf(out_buf, out_cap, "%s", src_text ? src_text : "");
        return;
    }
    char nfc_buf[4096];
    lotus_decode_to_unicode_nfc(src_text, src_charset_id, nfc_buf, sizeof(nfc_buf));
    lotus_convert_charset(nfc_buf, dst_charset_id, out_buf, out_cap);
}

/*
 * Macro Table Support (Gõ tắt)
 * Reads ~/.config/LotusKey/macros.conf (key=value per line)
 * Supports case-preserving expansion:
 *   - "vn" -> "Việt Nam" (exact defined case)
 *   - "VN" -> "VIỆT NAM" (all uppercase when input is all uppercase and auto_capitalize is enabled)
 *   - "Vn" -> "Việt Nam" (capitalizes first letter when input is Title Case and auto_capitalize is enabled)
 */
#define LOTUS_MAX_MACROS 256
#define LOTUS_MACRO_KEY_MAX 64
#define LOTUS_MACRO_VAL_MAX 256

typedef struct {
    char key[LOTUS_MACRO_KEY_MAX];
    char val[LOTUS_MACRO_VAL_MAX];
} LotusMacroEntry;

typedef struct {
    LotusMacroEntry entries[LOTUS_MAX_MACROS];
    size_t count;
} LotusMacroTable;

static inline void lotus_macro_table_load(LotusMacroTable *table, const char *filepath) {
    if (!table) return;
    table->count = 0;
    if (!filepath) return;
    FILE *fp = fopen(filepath, "r");
    if (!fp) return;

    char line[512];
    while (fgets(line, sizeof(line), fp) && table->count < LOTUS_MAX_MACROS) {
        size_t len = strlen(line);
        while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
            line[--len] = '\0';
        }
        if (len == 0 || line[0] == '#') continue;
        char *eq = strchr(line, '=');
        if (!eq || eq == line) continue;
        *eq = '\0';
        const char *k = line;
        const char *v = eq + 1;
        if (k[0] == '\0' || v[0] == '\0') continue;

        snprintf(table->entries[table->count].key, LOTUS_MACRO_KEY_MAX, "%s", k);
        snprintf(table->entries[table->count].val, LOTUS_MACRO_VAL_MAX, "%s", v);
        table->count++;
    }
    fclose(fp);
}

static inline int lotus_strcasecmp_ascii(const char *a, const char *b) {
    while (*a && *b) {
        char ca = (*a >= 'A' && *a <= 'Z') ? (char)(*a + 32) : *a;
        char cb = (*b >= 'A' && *b <= 'Z') ? (char)(*b + 32) : *b;
        if (ca != cb) return (unsigned char)ca - (unsigned char)cb;
        a++;
        b++;
    }
    return (unsigned char)*a - (unsigned char)*b;
}

static inline int lotus_is_all_upper_ascii(const char *s) {
    if (!s || !*s) return 0;
    int has_alpha = 0;
    for (; *s; s++) {
        if (*s >= 'a' && *s <= 'z') return 0;
        if (*s >= 'A' && *s <= 'Z') has_alpha = 1;
    }
    return has_alpha;
}

static inline void lotus_utf8_toupper(const char *src, char *out, size_t out_cap) {
    size_t len = 0;
    const char *p = src;
    const size_t table_len = sizeof(kLotusCharsetTable) / sizeof(kLotusCharsetTable[0]);
    while (*p && len + 5 < out_cap) {
        size_t clen = lotus_utf8_seq_len((unsigned char)*p);
        if (clen == 1) {
            char c = *p++;
            out[len++] = (c >= 'a' && c <= 'z') ? (char)(c - 32) : c;
            continue;
        }
        const char *upper_rep = NULL;
        for (size_t i = 0; i < table_len; i++) {
            const char *nfc = kLotusCharsetTable[i].utf8_nfc;
            if (strlen(nfc) == clen && strncmp(p, nfc, clen) == 0) {
                if (i >= 16 && i < 32) {
                    upper_rep = kLotusCharsetTable[i - 16].utf8_nfc;
                } else if (i >= 32 && (i % 2 == 1)) {
                    upper_rep = kLotusCharsetTable[i - 1].utf8_nfc;
                }
                break;
            }
        }
        if (upper_rep) {
            size_t ulen = strlen(upper_rep);
            memcpy(out + len, upper_rep, ulen);
            len += ulen;
        } else {
            for (size_t k = 0; k < clen && p[k]; k++) {
                out[len++] = p[k];
            }
        }
        p += clen;
    }
    out[len] = '\0';
}

static inline void lotus_utf8_capitalize_first(const char *src, char *out, size_t out_cap) {
    if (!out || out_cap == 0) return;
    if (!src || !*src) {
        out[0] = '\0';
        return;
    }
    size_t clen = lotus_utf8_seq_len((unsigned char)src[0]);
    char first_ch[8] = {0};
    char first_up[8] = {0};
    for (size_t k = 0; k < clen && src[k] && k < 7; k++) {
        first_ch[k] = src[k];
    }
    lotus_utf8_toupper(first_ch, first_up, sizeof(first_up));
    snprintf(out, out_cap, "%s%s", first_up, src + clen);
}

static inline int lotus_macro_lookup_ex(const LotusMacroTable *table, const char *word, int auto_capitalize, char *out_buf, size_t out_cap) {
    if (!table || !word || word[0] == '\0' || !out_buf || out_cap == 0) return 0;
    /* 1. Exact match first */
    for (size_t i = 0; i < table->count; i++) {
        if (strcmp(table->entries[i].key, word) == 0) {
            snprintf(out_buf, out_cap, "%s", table->entries[i].val);
            return 1;
        }
    }
    if (!auto_capitalize) {
        return 0;
    }
    /* 2. Case-insensitive match */
    for (size_t i = 0; i < table->count; i++) {
        if (lotus_strcasecmp_ascii(table->entries[i].key, word) == 0) {
            if (lotus_is_all_upper_ascii(word) && strlen(word) > 1) {
                lotus_utf8_toupper(table->entries[i].val, out_buf, out_cap);
            } else if (word[0] >= 'A' && word[0] <= 'Z') {
                lotus_utf8_capitalize_first(table->entries[i].val, out_buf, out_cap);
            } else {
                snprintf(out_buf, out_cap, "%s", table->entries[i].val);
            }
            return 1;
        }
    }
    return 0;
}

static inline int lotus_macro_lookup(const LotusMacroTable *table, const char *word, char *out_buf, size_t out_cap) {
    return lotus_macro_lookup_ex(table, word, 1, out_buf, out_cap);
}

#endif /* LOTUS_CHARSET_H */
