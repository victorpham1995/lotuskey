/*
 * LotusKey C-ABI Parity Test
 * Verifies behavioral parity between source-compiled and prebuilt libLotusKeyCAPI.so
 *
 * Usage: gcc -o test_capi_parity tests/test_capi_parity.c -ldl -Iinclude && ./test_capi_parity
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include "lotuskey.h"

#define MAX_TESTS 128
#define TEST_PASS "\033[32mPASS\033[0m"
#define TEST_FAIL "\033[31mFAIL\033[0m"

static int g_pass = 0, g_fail = 0;

typedef lotuskey_session_t (*fn_create)(void);
typedef void (*fn_destroy)(lotuskey_session_t);
typedef void (*fn_reset)(lotuskey_session_t);
typedef void (*fn_set_input)(lotuskey_session_t, lotuskey_input_method_t);
typedef void (*fn_set_grammar)(lotuskey_session_t, int32_t);
typedef int32_t (*fn_get_grammar)(lotuskey_session_t);
typedef void (*fn_set_bool)(lotuskey_session_t, bool);
typedef int32_t (*fn_feed_char)(lotuskey_session_t, uint32_t);
typedef int32_t (*fn_feed_bs)(lotuskey_session_t);
typedef int32_t (*fn_feed_key)(lotuskey_session_t, uint32_t, char, uint32_t);
typedef int32_t (*fn_commit)(lotuskey_session_t);
typedef int32_t (*fn_feed_char_ex)(lotuskey_session_t, uint32_t, int32_t*, const char**);
typedef int32_t (*fn_get_action)(lotuskey_session_t);
typedef int32_t (*fn_get_bs)(lotuskey_session_t);
typedef const char* (*fn_get_text)(lotuskey_session_t);
typedef bool (*fn_get_bool)(lotuskey_session_t);
typedef bool (*fn_is_composing)(lotuskey_session_t);
typedef const char* (*fn_get_ctext)(lotuskey_session_t);
typedef void (*fn_append_ctx)(lotuskey_session_t, const char*);
typedef void (*fn_sync_armed)(lotuskey_session_t, const char*);
typedef const char* (*fn_get_version)(void);

struct API {
    void *handle;
    fn_create           create;
    fn_destroy          destroy;
    fn_reset            reset;
    fn_set_input        set_input;
    fn_set_grammar      set_grammar;
    fn_get_grammar      get_grammar;
    fn_set_bool         set_bilingual;
    fn_set_bool         set_modern;
    fn_set_bool         set_quick;
    fn_feed_char        feed_char;
    fn_feed_bs          feed_backspace;
    fn_feed_key         feed_key;
    fn_commit           commit_word;
    fn_feed_char_ex     feed_char_ex;
    fn_get_action       get_action;
    fn_get_bs           get_backspaces;
    fn_get_text         get_text;
    fn_get_bool         get_override;
    fn_is_composing     is_composing;
    fn_get_ctext        get_composing;
    fn_get_ctext        get_raw;
    fn_append_ctx       append_context;
    fn_sync_armed       sync_armed;
    fn_get_version      get_version;
};

static int load_api(const char *path, struct API *api) {
    api->handle = dlopen(path, RTLD_NOW);
    if (!api->handle) { fprintf(stderr, "dlopen(%s): %s\n", path, dlerror()); return 1; }
#define LOAD(name) api->name = (fn_##name)dlsym(api->handle, "lotuskey_" #name); \
    if (!api->name) { fprintf(stderr, "Missing symbol: lotuskey_%s\n", #name); return 1; }
    api->create        = (fn_create)dlsym(api->handle, "lotuskey_create_session");
    api->destroy       = (fn_destroy)dlsym(api->handle, "lotuskey_destroy_session");
    api->reset         = (fn_reset)dlsym(api->handle, "lotuskey_reset_session");
    api->set_input     = (fn_set_input)dlsym(api->handle, "lotuskey_set_input_method");
    api->set_grammar   = (fn_set_grammar)dlsym(api->handle, "lotuskey_set_grammar_profile");
    api->get_grammar   = (fn_get_grammar)dlsym(api->handle, "lotuskey_get_grammar_profile");
    api->set_bilingual = (fn_set_bool)dlsym(api->handle, "lotuskey_set_smart_bilingual");
    api->set_modern    = (fn_set_bool)dlsym(api->handle, "lotuskey_set_modern_orthography");
    api->set_quick     = (fn_set_bool)dlsym(api->handle, "lotuskey_set_quick_telex");
    api->feed_char     = (fn_feed_char)dlsym(api->handle, "lotuskey_feed_char");
    api->feed_backspace= (fn_feed_bs)dlsym(api->handle, "lotuskey_feed_backspace");
    api->feed_key      = (fn_feed_key)dlsym(api->handle, "lotuskey_feed_key");
    api->commit_word   = (fn_commit)dlsym(api->handle, "lotuskey_commit_word");
    api->feed_char_ex  = (fn_feed_char_ex)dlsym(api->handle, "lotuskey_feed_char_ex");
    api->get_action    = (fn_get_action)dlsym(api->handle, "lotuskey_get_last_action");
    api->get_backspaces= (fn_get_bs)dlsym(api->handle, "lotuskey_get_last_backspaces");
    api->get_text      = (fn_get_text)dlsym(api->handle, "lotuskey_get_last_text");
    api->get_override  = (fn_get_bool)dlsym(api->handle, "lotuskey_get_last_is_override");
    api->is_composing  = (fn_is_composing)dlsym(api->handle, "lotuskey_is_composing");
    api->get_composing = (fn_get_ctext)dlsym(api->handle, "lotuskey_get_composing_text");
    api->get_raw       = (fn_get_ctext)dlsym(api->handle, "lotuskey_get_raw_text");
    api->append_context= (fn_append_ctx)dlsym(api->handle, "lotuskey_append_context");
    api->sync_armed    = (fn_sync_armed)dlsym(api->handle, "lotuskey_sync_armed_word");
    api->get_version   = (fn_get_version)dlsym(api->handle, "lotuskey_get_version");
#undef LOAD
    return 0;
}

static const char* safe_str(const char *s) { return s ? s : "(null)"; }

static void type_string(struct API *api, lotuskey_session_t s, const char *keys) {
    for (int i = 0; keys[i]; i++) {
        api->feed_char(s, (uint32_t)(unsigned char)keys[i]);
    }
}

static void check_composing(const char *test, struct API *a, struct API *b,
                             lotuskey_session_t sa, lotuskey_session_t sb) {
    const char *ca = safe_str(a->get_composing(sa));
    const char *cb = safe_str(b->get_composing(sb));
    if (strcmp(ca, cb) == 0) {
        printf("  [%s] %-40s composing='%s'\n", TEST_PASS, test, ca);
        g_pass++;
    } else {
        printf("  [%s] %-40s prebuilt='%s' vs source='%s'\n", TEST_FAIL, test, ca, cb);
        g_fail++;
    }
}

static void check_raw(const char *test, struct API *a, struct API *b,
                       lotuskey_session_t sa, lotuskey_session_t sb) {
    const char *ra = safe_str(a->get_raw(sa));
    const char *rb = safe_str(b->get_raw(sb));
    if (strcmp(ra, rb) == 0) {
        printf("  [%s] %-40s raw='%s'\n", TEST_PASS, test, ra);
        g_pass++;
    } else {
        printf("  [%s] %-40s prebuilt='%s' vs source='%s'\n", TEST_FAIL, test, ra, rb);
        g_fail++;
    }
}

static void check_action(const char *test, struct API *a, struct API *b,
                          lotuskey_session_t sa, lotuskey_session_t sb) {
    int32_t aa = a->get_action(sa);
    int32_t ab = b->get_action(sb);
    if (aa == ab) {
        printf("  [%s] %-40s action=%d\n", TEST_PASS, test, aa);
        g_pass++;
    } else {
        printf("  [%s] %-40s prebuilt=%d vs source=%d\n", TEST_FAIL, test, aa, ab);
        g_fail++;
    }
}

static void check_backspaces(const char *test, struct API *a, struct API *b,
                              lotuskey_session_t sa, lotuskey_session_t sb) {
    int32_t ba = a->get_backspaces(sa);
    int32_t bb = b->get_backspaces(sb);
    if (ba == bb) {
        printf("  [%s] %-40s backspaces=%d\n", TEST_PASS, test, ba);
        g_pass++;
    } else {
        printf("  [%s] %-40s prebuilt=%d vs source=%d\n", TEST_FAIL, test, ba, bb);
        g_fail++;
    }
}

static void check_text(const char *test, struct API *a, struct API *b,
                        lotuskey_session_t sa, lotuskey_session_t sb) {
    const char *ta = safe_str(a->get_text(sa));
    const char *tb = safe_str(b->get_text(sb));
    if (strcmp(ta, tb) == 0) {
        printf("  [%s] %-40s text='%s'\n", TEST_PASS, test, ta);
        g_pass++;
    } else {
        printf("  [%s] %-40s prebuilt='%s' vs source='%s'\n", TEST_FAIL, test, ta, tb);
        g_fail++;
    }
}

int main(int argc, char *argv[]) {
    const char *prebuilt_path = "lib/libLotusKeyCAPI.so";
    const char *source_path = NULL;

    if (argc >= 2) prebuilt_path = argv[1];
    if (argc >= 3) source_path = argv[2];

    struct API pre, src;
    if (load_api(prebuilt_path, &pre)) return 1;

    /* If only one library specified, test against itself */
    if (source_path) {
        if (load_api(source_path, &src)) return 1;
    } else {
        src = pre;
    }

    printf("=== LotusKey C-ABI Parity Test ===\n");
    printf("Prebuilt: %s (v%s)\n", prebuilt_path, pre.get_version());
    printf("Source:   %s (v%s)\n", source_path ? source_path : "(same)", src.get_version());
    printf("\n");

    /* Version check */
    if (strcmp(pre.get_version(), src.get_version()) == 0) {
        printf("  [%s] %-40s version='%s'\n", TEST_PASS, "Version match", pre.get_version());
        g_pass++;
    } else {
        printf("  [%s] %-40s prebuilt='%s' vs source='%s'\n", TEST_FAIL, "Version match",
               pre.get_version(), src.get_version());
        g_fail++;
    }

    /* ============================================================ */
    /* Test 1: Telex Classic - basic Vietnamese */
    /* ============================================================ */
    printf("\n--- Telex Classic ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_CLASSIC);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_CLASSIC);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);
        pre.set_quick(sa, false); src.set_quick(sb, false);

        /* "tieengs" -> "tiếng" */
        type_string(&pre, sa, "tieengs"); type_string(&src, sb, "tieengs");
        check_composing("Telex 'tieengs' -> tiếng", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "vieetj" -> "việt" */
        type_string(&pre, sa, "vieetj"); type_string(&src, sb, "vieetj");
        check_composing("Telex 'vieetj' -> việt", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "xin chaof" -> "chào" */
        type_string(&pre, sa, "chaof"); type_string(&src, sb, "chaof");
        check_composing("Telex 'chaof' -> chào", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "thuongw" -> "thương" */
        type_string(&pre, sa, "thuongw"); type_string(&src, sb, "thuongw");
        check_composing("Telex 'thuongw' -> thương", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "oaan" -> modern orthography test */
        type_string(&pre, sa, "hoaf"); type_string(&src, sb, "hoaf");
        check_composing("Telex modern 'hoaf' -> hoà", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* Dấu nặng: "naangj" -> "nặng" */
        type_string(&pre, sa, "naangj"); type_string(&src, sb, "naangj");
        check_composing("Telex 'naangj' -> nặng", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "ees" -> "ế" */
        type_string(&pre, sa, "ees"); type_string(&src, sb, "ees");
        check_composing("Telex 'ees' -> ế", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "ddi" -> "đi" */
        type_string(&pre, sa, "ddi"); type_string(&src, sb, "ddi");
        check_composing("Telex 'ddi' -> đi", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 2: VNI - basic Vietnamese */
    /* ============================================================ */
    printf("\n--- VNI Classic ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_VNI);
        src.set_input(sb, LOTUSKEY_INPUT_VNI);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_CLASSIC);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_CLASSIC);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);

        /* "tie61ng" -> "tiếng" */
        type_string(&pre, sa, "tie61ng"); type_string(&src, sb, "tie61ng");
        check_composing("VNI 'tie61ng' -> tiếng", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "vie65t" -> "việt" */
        type_string(&pre, sa, "vie65t"); type_string(&src, sb, "vie65t");
        check_composing("VNI 'vie65t' -> việt", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "d9i" -> "đi" */
        type_string(&pre, sa, "d9i"); type_string(&src, sb, "d9i");
        check_composing("VNI 'd9i' -> đi", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 3: SEN Flex grammar */
    /* ============================================================ */
    printf("\n--- SEN Flex Grammar ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_SEN_FLEX);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_SEN_FLEX);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);

        /* Grammar profile getter */
        int32_t ga = pre.get_grammar(sa), gb = src.get_grammar(sb);
        if (ga == gb && ga == LOTUSKEY_GRAMMAR_SEN_FLEX) {
            printf("  [%s] %-40s profile=%d\n", TEST_PASS, "SEN Flex profile", ga);
            g_pass++;
        } else {
            printf("  [%s] %-40s prebuilt=%d vs source=%d\n", TEST_FAIL, "SEN Flex profile", ga, gb);
            g_fail++;
        }

        /* "tiesngs" - free order tone marking */
        type_string(&pre, sa, "tiesngs"); type_string(&src, sb, "tiesngs");
        check_composing("SEN Flex 'tiesngs' free tone", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 4: Backspace handling */
    /* ============================================================ */
    printf("\n--- Backspace Handling ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_CLASSIC);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_CLASSIC);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);
        pre.set_quick(sa, false); src.set_quick(sb, false);

        /* Type "abc" then backspace */
        type_string(&pre, sa, "abc"); type_string(&src, sb, "abc");
        pre.feed_backspace(sa); src.feed_backspace(sb);
        check_composing("After 'abc' + BS", &pre, &src, sa, sb);
        check_action("BS action", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* Type Vietnamese then BS */
        type_string(&pre, sa, "tieengs"); type_string(&src, sb, "tieengs");
        pre.feed_backspace(sa); src.feed_backspace(sb);
        check_composing("After 'tieengs' + BS", &pre, &src, sa, sb);
        check_backspaces("BS backspaces count", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 5: feed_char_ex */
    /* ============================================================ */
    printf("\n--- feed_char_ex ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_CLASSIC);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_CLASSIC);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);
        pre.set_quick(sa, false); src.set_quick(sb, false);

        int32_t bs_a, bs_b;
        const char *text_a, *text_b;

        /* Feed "a" then "s" via feed_char_ex */
        pre.feed_char_ex(sa, 'a', &bs_a, &text_a);
        src.feed_char_ex(sb, 'a', &bs_b, &text_b);

        int32_t ra = pre.feed_char_ex(sa, 's', &bs_a, &text_a);
        int32_t rb = src.feed_char_ex(sb, 's', &bs_b, &text_b);

        if (ra == rb && bs_a == bs_b && strcmp(safe_str(text_a), safe_str(text_b)) == 0) {
            printf("  [%s] %-40s action=%d bs=%d text='%s'\n",
                   TEST_PASS, "feed_char_ex 'as' -> á", ra, bs_a, safe_str(text_a));
            g_pass++;
        } else {
            printf("  [%s] %-40s pre(a=%d bs=%d t='%s') vs src(a=%d bs=%d t='%s')\n",
                   TEST_FAIL, "feed_char_ex 'as' -> á",
                   ra, bs_a, safe_str(text_a), rb, bs_b, safe_str(text_b));
            g_fail++;
        }

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 6: is_composing state */
    /* ============================================================ */
    printf("\n--- Composing State ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);

        /* Fresh session should not be composing */
        bool ca = pre.is_composing(sa), cb = src.is_composing(sb);
        if (ca == cb) {
            printf("  [%s] %-40s composing=%s\n", TEST_PASS, "Fresh session", ca ? "true" : "false");
            g_pass++;
        } else {
            printf("  [%s] %-40s prebuilt=%s vs source=%s\n", TEST_FAIL, "Fresh session",
                   ca ? "true" : "false", cb ? "true" : "false");
            g_fail++;
        }

        /* After typing should be composing */
        type_string(&pre, sa, "a"); type_string(&src, sb, "a");
        ca = pre.is_composing(sa); cb = src.is_composing(sb);
        if (ca == cb) {
            printf("  [%s] %-40s composing=%s\n", TEST_PASS, "After 'a'", ca ? "true" : "false");
            g_pass++;
        } else {
            printf("  [%s] %-40s prebuilt=%s vs source=%s\n", TEST_FAIL, "After 'a'",
                   ca ? "true" : "false", cb ? "true" : "false");
            g_fail++;
        }

        /* After reset should not be composing */
        pre.reset(sa); src.reset(sb);
        ca = pre.is_composing(sa); cb = src.is_composing(sb);
        if (ca == cb) {
            printf("  [%s] %-40s composing=%s\n", TEST_PASS, "After reset", ca ? "true" : "false");
            g_pass++;
        } else {
            printf("  [%s] %-40s prebuilt=%s vs source=%s\n", TEST_FAIL, "After reset",
                   ca ? "true" : "false", cb ? "true" : "false");
            g_fail++;
        }

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 7: Quick Telex shortcuts */
    /* ============================================================ */
    printf("\n--- Quick Telex ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_CLASSIC);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_CLASSIC);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);
        pre.set_quick(sa, true); src.set_quick(sb, true);

        /* "cc" -> "ch" if Quick Telex active */
        type_string(&pre, sa, "cc"); type_string(&src, sb, "cc");
        check_composing("Quick Telex 'cc'", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        /* "gg" -> "gi" */
        type_string(&pre, sa, "gg"); type_string(&src, sb, "gg");
        check_composing("Quick Telex 'gg'", &pre, &src, sa, sb);
        pre.reset(sa); src.reset(sb);

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 8: commit_word + get_last_text */
    /* ============================================================ */
    printf("\n--- Commit Word ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);
        pre.set_grammar(sa, LOTUSKEY_GRAMMAR_CLASSIC);
        src.set_grammar(sb, LOTUSKEY_GRAMMAR_CLASSIC);
        pre.set_modern(sa, true);  src.set_modern(sb, true);
        pre.set_bilingual(sa, false); src.set_bilingual(sb, false);
        pre.set_quick(sa, false); src.set_quick(sb, false);

        type_string(&pre, sa, "tieengs"); type_string(&src, sb, "tieengs");

        int32_t ca = pre.commit_word(sa);
        int32_t cb = src.commit_word(sb);
        if (ca == cb) {
            printf("  [%s] %-40s action=%d\n", TEST_PASS, "commit_word 'tieengs'", ca);
            g_pass++;
        } else {
            printf("  [%s] %-40s prebuilt=%d vs source=%d\n", TEST_FAIL, "commit_word 'tieengs'", ca, cb);
            g_fail++;
        }

        check_text("commit text", &pre, &src, sa, sb);

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Test 9: append_context + sync_armed_word (no crash check) */
    /* ============================================================ */
    printf("\n--- Context / Armed Word (crash check) ---\n");
    {
        lotuskey_session_t sa = pre.create(), sb = src.create();
        pre.set_input(sa, LOTUSKEY_INPUT_TELEX);
        src.set_input(sb, LOTUSKEY_INPUT_TELEX);

        pre.append_context(sa, "hello");
        src.append_context(sb, "hello");
        printf("  [%s] %-40s\n", TEST_PASS, "append_context('hello') no crash");
        g_pass++;

        pre.sync_armed(sa, "world");
        src.sync_armed(sb, "world");
        printf("  [%s] %-40s\n", TEST_PASS, "sync_armed_word('world') no crash");
        g_pass++;

        pre.destroy(sa); src.destroy(sb);
    }

    /* ============================================================ */
    /* Summary */
    /* ============================================================ */
    printf("\n=== Summary: %d passed, %d failed ===\n", g_pass, g_fail);
    return g_fail > 0 ? 1 : 0;
}
