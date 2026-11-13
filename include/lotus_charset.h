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
 */
enum {
    LOTUS_CHARSET_UNICODE          = 0,
    LOTUS_CHARSET_TCVN3_ENUM       = 5,
    LOTUS_CHARSET_COMBINING_ENUM   = 9,
    LOTUS_CHARSET_VIQR_ENUM        = 10,
    LOTUS_CHARSET_VNI_WIN_ENUM     = 12,
    LOTUS_CHARSET_TCVN3_CFG        = 27,
    LOTUS_CHARSET_COMBINING_CFG    = 31,
    LOTUS_CHARSET_VNI_WIN_CFG      = 34
};

typedef struct {
    const char *utf8_nfc;
    const char *combining;
    const char *tcvn3;
    const char *vni_win;
} LotusCharsetEntry;

static const LotusCharsetEntry kLotusCharsetTable[] = {
    { "À", "À", "µ", "AØ" }, { "Á", "Á", "¸", "AÙ" }, { "Â", "Â", "¢", "AÂ" }, { "Ã", "Ã", "·", "AÕ" },
    { "È", "È", "Ì", "EØ" }, { "É", "É", "Ð", "EÙ" }, { "Ê", "Ê", "£", "EÂ" }, { "Ì", "Ì", "×", "Ì" },
    { "Í", "Í", "Ý", "Í" },  { "Ò", "Ò", "ß", "OØ" }, { "Ó", "Ó", "ã", "OÙ" }, { "Ô", "Ô", "¤", "OÂ" },
    { "Õ", "Õ", "â", "OÕ" }, { "Ù", "Ù", "ï", "UØ" }, { "Ú", "Ú", "ó", "UÙ" }, { "Ý", "Ý", "ý", "YÙ" },
    { "à", "à", "µ", "aø" }, { "á", "á", "¸", "aù" }, { "â", "â", "©", "aâ" }, { "ã", "ã", "·", "aõ" },
    { "è", "è", "Ì", "eø" }, { "é", "é", "Ð", "eù" }, { "ê", "ê", "ª", "eâ" }, { "ì", "ì", "×", "ì" },
    { "í", "í", "Ý", "í" },  { "ò", "ò", "ß", "oø" }, { "ó", "ó", "ã", "où" }, { "ô", "ô", "«", "oâ" },
    { "õ", "õ", "â", "oõ" }, { "ù", "ù", "ï", "uø" }, { "ú", "ú", "ó", "uù" }, { "ý", "ý", "ý", "yù" },
    { "Ă", "Ă", "¡", "AÊ" }, { "ă", "ă", "¨", "aê" }, { "Đ", "Đ", "§", "Ñ" },  { "đ", "đ", "®", "ñ" },
    { "Ĩ", "Ĩ", "Ü", "Ó" },  { "ĩ", "ĩ", "Ü", "ó" },  { "Ũ", "Ũ", "ò", "UÕ" }, { "ũ", "ũ", "ò", "uõ" },
    { "Ơ", "Ơ", "¥", "Ô" },  { "ơ", "ơ", "¬", "ô" },  { "Ư", "Ư", "¦", "Ö" },  { "ư", "ư", "\xc2\xad", "ö" },
    { "Ạ", "Ạ", "¹", "AÏ" }, { "ạ", "ạ", "¹", "aï" }, { "Ả", "Ả", "¶", "AÛ" }, { "ả", "ả", "¶", "aû" },
    { "Ấ", "Ấ", "Ê", "AÁ" }, { "ấ", "ấ", "Ê", "aá" }, { "Ầ", "Ầ", "Ç", "AÀ" }, { "ầ", "ầ", "Ç", "aà" },
    { "Ẩ", "Ẩ", "È", "AÅ" }, { "ẩ", "ẩ", "È", "aå" }, { "Ẫ", "Ẫ", "É", "AÃ" }, { "ẫ", "ẫ", "É", "aã" },
    { "Ậ", "Ậ", "Ë", "AÄ" }, { "ậ", "ậ", "Ë", "aä" }, { "Ắ", "Ắ", "¾", "AÉ" }, { "ắ", "ắ", "¾", "aé" },
    { "Ằ", "Ằ", "»", "AÈ" }, { "ằ", "ằ", "»", "aè" }, { "Ẳ", "Ẳ", "¼", "AÚ" }, { "ẳ", "ẳ", "¼", "aú" },
    { "Ẵ", "Ẵ", "½", "AÜ" }, { "ẵ", "ẵ", "½", "aü" }, { "Ặ", "Ặ", "Æ", "AË" }, { "ặ", "ặ", "Æ", "aë" },
    { "Ẹ", "Ẹ", "Ñ", "EÏ" }, { "ẹ", "ẹ", "Ñ", "eï" }, { "Ẻ", "Ẻ", "Î", "EÛ" }, { "ẻ", "ẻ", "Î", "eû" },
    { "Ẽ", "Ẽ", "Ï", "EÕ" }, { "ẽ", "ẽ", "Ï", "eõ" }, { "Ế", "Ế", "Õ", "EÁ" }, { "ế", "ế", "Õ", "eá" },
    { "Ề", "Ề", "Ò", "EÀ" }, { "ề", "ề", "Ò", "eà" }, { "Ể", "Ể", "Ó", "EÅ" }, { "ể", "ể", "Ó", "eå" },
    { "Ễ", "Ễ", "Ô", "EÃ" }, { "ễ", "ễ", "Ô", "eã" }, { "Ệ", "Ệ", "Ö", "EÄ" }, { "ệ", "ệ", "Ö", "eä" },
    { "Ỉ", "Ỉ", "Ø", "Æ" },  { "ỉ", "ỉ", "Ø", "æ" },  { "Ị", "Ị", "Þ", "Ò" },  { "ị", "ị", "Þ", "ò" },
    { "Ọ", "Ọ", "ä", "OÏ" }, { "ọ", "ọ", "ä", "oï" }, { "Ỏ", "Ỏ", "á", "OÛ" }, { "ỏ", "ỏ", "á", "oû" },
    { "Ố", "Ố", "è", "OÁ" }, { "ố", "ố", "è", "oá" }, { "Ồ", "Ồ", "å", "OÀ" }, { "ồ", "ồ", "å", "oà" },
    { "Ổ", "Ổ", "æ", "OÅ" }, { "ổ", "ổ", "æ", "oå" }, { "Ỗ", "Ỗ", "ç", "OÃ" }, { "ỗ", "ỗ", "ç", "oã" },
    { "Ộ", "Ộ", "é", "OÄ" }, { "ộ", "ộ", "é", "oä" }, { "Ớ", "Ớ", "í", "ÔÙ" }, { "ớ", "ớ", "í", "ôù" },
    { "Ờ", "Ờ", "ê", "ÔØ" }, { "ờ", "ờ", "ê", "ôø" }, { "Ở", "Ở", "ë", "ÔÛ" }, { "ở", "ở", "ë", "ôû" },
    { "Ỡ", "Ỡ", "ì", "ÔÕ" }, { "ỡ", "ỡ", "ì", "ôõ" }, { "Ợ", "Ợ", "î", "ÔÏ" }, { "ợ", "ợ", "î", "ôï" },
    { "Ụ", "Ụ", "ô", "UÏ" }, { "ụ", "ụ", "ô", "uï" }, { "Ủ", "Ủ", "ñ", "UÛ" }, { "ủ", "ủ", "ñ", "uû" },
    { "Ứ", "Ứ", "ø", "ÖÙ" }, { "ứ", "ứ", "ø", "öù" }, { "Ừ", "Ừ", "õ", "ÖØ" }, { "ừ", "ừ", "õ", "öø" },
    { "Ử", "Ử", "ö", "ÖÛ" }, { "ử", "ử", "ö", "öû" }, { "Ữ", "Ữ", "÷", "ÖÕ" }, { "ữ", "ữ", "÷", "öõ" },
    { "Ự", "Ự", "ù", "ÖÏ" }, { "ự", "ự", "ù", "öï" }, { "Ỳ", "Ỳ", "ú", "YØ" }, { "ỳ", "ỳ", "ú", "yø" },
    { "Ỵ", "Ỵ", "þ", "Î" },  { "ỵ", "ỵ", "þ", "î" },  { "Ỷ", "Ỷ", "û", "YÛ" }, { "ỷ", "ỷ", "û", "yû" },
    { "Ỹ", "Ỹ", "ü", "YÕ" }, { "ỹ", "ỹ", "ü", "yõ" }
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
 * Macro Table Support (Gõ tắt)
 * Reads ~/.config/LotusKey/macros.conf (key=value per line)
 * Supports case-preserving expansion:
 *   - "vn" -> "Việt Nam" (exact defined case)
 *   - "VN" -> "VIỆT NAM" (all uppercase when input is all uppercase)
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
                /* In kLotusCharsetTable, lowercase entries follow uppercase or are paired */
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

static inline int lotus_macro_lookup(const LotusMacroTable *table, const char *word, char *out_buf, size_t out_cap) {
    if (!table || !word || word[0] == '\0' || !out_buf || out_cap == 0) return 0;
    /* 1. Exact match first */
    for (size_t i = 0; i < table->count; i++) {
        if (strcmp(table->entries[i].key, word) == 0) {
            snprintf(out_buf, out_cap, "%s", table->entries[i].val);
            return 1;
        }
    }
    /* 2. Case-insensitive match */
    for (size_t i = 0; i < table->count; i++) {
        if (lotus_strcasecmp_ascii(table->entries[i].key, word) == 0) {
            if (lotus_is_all_upper_ascii(word) && strlen(word) > 1) {
                lotus_utf8_toupper(table->entries[i].val, out_buf, out_cap);
            } else {
                snprintf(out_buf, out_cap, "%s", table->entries[i].val);
            }
            return 1;
        }
    }
    return 0;
}

#endif /* LOTUS_CHARSET_H */
