/*
 * LotusKey - Universal Evdev/UInput Vietnamese Input Daemon (lotuskey-uinput)
 * Author: Victor Pham
 *
 * Works across ANY Linux Window Manager / Wayland Compositor / X11 session
 * (Hyprland, Sway, i3wm, bspwm, dwm, KDE, XFCE, GNOME, Wayfire, River)
 * without requiring toolkit IM modules.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <limits.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <linux/input.h>
#include <linux/uinput.h>

#include "lotuskey.h"
#include "lotus_charset.h"

#define MAX_KBD_DEVICES 16
#define VIRTUAL_DEV_NAME "LotusKey Virtual Keyboard"

static volatile sig_atomic_t g_running = 1;
static volatile sig_atomic_t g_reload_requested = 1;

typedef struct {
    lotuskey_session_t session;
    bool enabled;
    int input_method; /* 0: Telex, 1: VNI, 2: Telex+VNI */
    bool sen_flex;
    bool smart_bilingual;
    bool modern_orthography;
    bool quick_telex;
    bool w2u;
    bool bracket_transform;
    bool macro_enabled;
    int charset;
    bool shift_down;
    bool ctrl_down;
    bool alt_down;
    bool super_down;
    bool capslock_on;
    bool other_key_in_chord;
    char prev_composed[512];
} UInputEngineState;

static LotusMacroTable g_macros = { .count = 0 };

static void handle_sig(int sig) {
    if (sig == SIGUSR1) {
        g_reload_requested = 1;
    } else {
        g_running = 0;
    }
}

static void get_config_dir(char *out, size_t cap) {
    const char *xdg = getenv("XDG_CONFIG_HOME");
    if (xdg && xdg[0] != '\0') {
        snprintf(out, cap, "%s/LotusKey", xdg);
        return;
    }
    const char *home = getenv("HOME");
    if (home && home[0] != '\0') {
        snprintf(out, cap, "%s/.config/LotusKey", home);
        return;
    }
    snprintf(out, cap, "/tmp/LotusKey");
}

static void load_daemon_config(UInputEngineState *st) {
    char dir[PATH_MAX - 64];
    get_config_dir(dir, sizeof(dir));

    char macro_path[PATH_MAX];
    snprintf(macro_path, sizeof(macro_path), "%s/macros.conf", dir);
    lotus_macro_table_load(&g_macros, macro_path);

    char env_path[PATH_MAX];
    snprintf(env_path, sizeof(env_path), "%s/config.env", dir);
    FILE *fp = fopen(env_path, "r");
    if (!fp) return;

    char line[256];
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "ENABLED=", 8) == 0) {
            st->enabled = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "INPUT_METHOD=", 13) == 0) {
            if (strstr(line, "telex_vni")) st->input_method = 2;
            else if (strstr(line, "vni")) st->input_method = 1;
            else st->input_method = 0;
        } else if (strncmp(line, "GRAMMAR_PROFILE=", 16) == 0) {
            st->sen_flex = (strstr(line, "classic") == NULL);
        } else if (strncmp(line, "SMART_BILINGUAL=", 16) == 0) {
            st->smart_bilingual = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "MODERN_ORTHOGRAPHY=", 19) == 0) {
            st->modern_orthography = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "QUICK_TELEX=", 12) == 0) {
            st->quick_telex = (strstr(line, "true") != NULL || strstr(line, "1") != NULL);
        } else if (strncmp(line, "W2U=", 4) == 0) {
            st->w2u = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "BRACKET_TRANSFORM=", 18) == 0) {
            st->bracket_transform = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "MACRO_ENABLED=", 14) == 0) {
            st->macro_enabled = (strstr(line, "false") == NULL && strstr(line, "0") == NULL);
        } else if (strncmp(line, "CHARSET=", 8) == 0) {
            const char *p = line + 8;
            while (*p == '"' || *p == '\'' || *p == ' ') p++;
            st->charset = atoi(p);
        }
    }
    fclose(fp);

    if (st->session) {
        lotuskey_set_input_method(st->session, (st->input_method == 1) ? LOTUSKEY_INPUT_VNI : LOTUSKEY_INPUT_TELEX);
        lotuskey_set_grammar_profile(st->session, st->sen_flex ? LOTUSKEY_GRAMMAR_SEN_FLEX : LOTUSKEY_GRAMMAR_CLASSIC);
        lotuskey_set_smart_bilingual(st->session, st->smart_bilingual);
        lotuskey_set_modern_orthography(st->session, st->modern_orthography);
        lotuskey_set_quick_telex(st->session, st->quick_telex);
    }
}

static int setup_uinput_device(void) {
    int ufd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (ufd < 0) {
        ufd = open("/dev/input/uinput", O_WRONLY | O_NONBLOCK);
    }
    if (ufd < 0) return -1;

    ioctl(ufd, UI_SET_EVBIT, EV_KEY);
    ioctl(ufd, UI_SET_EVBIT, EV_SYN);
    for (int k = 1; k < 256; k++) {
        ioctl(ufd, UI_SET_KEYBIT, k);
    }

    struct uinput_setup usetup;
    memset(&usetup, 0, sizeof(usetup));
    usetup.id.bustype = BUS_USB;
    usetup.id.vendor = 0x1D6B;
    usetup.id.product = 0x1995;
    snprintf(usetup.name, UINPUT_MAX_NAME_SIZE, "%s", VIRTUAL_DEV_NAME);

    if (ioctl(ufd, UI_DEV_SETUP, &usetup) < 0 || ioctl(ufd, UI_DEV_CREATE) < 0) {
        close(ufd);
        return -1;
    }
    return ufd;
}

static void emit_uinput_event(int ufd, uint16_t type, uint16_t code, int32_t val) {
    struct input_event ie;
    memset(&ie, 0, sizeof(ie));
    ie.type = type;
    ie.code = code;
    ie.value = val;
    ssize_t r = write(ufd, &ie, sizeof(ie));
    (void)r;
}

static void emit_backspaces(int ufd, size_t count) {
    for (size_t i = 0; i < count; i++) {
        emit_uinput_event(ufd, EV_KEY, KEY_BACKSPACE, 1);
        emit_uinput_event(ufd, EV_SYN, SYN_REPORT, 0);
        emit_uinput_event(ufd, EV_KEY, KEY_BACKSPACE, 0);
        emit_uinput_event(ufd, EV_SYN, SYN_REPORT, 0);
    }
}

static void inject_utf8_text(const char *utf8_text) {
    if (!utf8_text || utf8_text[0] == '\0') return;
    /* Use wtype on Wayland or xdotool on X11 for direct Unicode string injection */
    const char *wayland_disp = getenv("WAYLAND_DISPLAY");
    char cmd[2048];
    if (wayland_disp && wayland_disp[0] != '\0') {
        snprintf(cmd, sizeof(cmd), "wtype -- '%s' 2>/dev/null || xdotool type --clearmodifiers -- '%s' 2>/dev/null &",
                 utf8_text, utf8_text);
    } else {
        snprintf(cmd, sizeof(cmd), "xdotool type --clearmodifiers -- '%s' 2>/dev/null &", utf8_text);
    }
    int rc = system(cmd);
    (void)rc;
}

static char evdev_code_to_ascii(uint16_t code, bool shift, bool caps) {
    bool upper = shift ^ caps;
    switch (code) {
        case KEY_A: return upper ? 'A' : 'a';
        case KEY_B: return upper ? 'B' : 'b';
        case KEY_C: return upper ? 'C' : 'c';
        case KEY_D: return upper ? 'D' : 'd';
        case KEY_E: return upper ? 'E' : 'e';
        case KEY_F: return upper ? 'F' : 'f';
        case KEY_G: return upper ? 'G' : 'g';
        case KEY_H: return upper ? 'H' : 'h';
        case KEY_I: return upper ? 'I' : 'i';
        case KEY_J: return upper ? 'J' : 'j';
        case KEY_K: return upper ? 'K' : 'k';
        case KEY_L: return upper ? 'L' : 'l';
        case KEY_M: return upper ? 'M' : 'm';
        case KEY_N: return upper ? 'N' : 'n';
        case KEY_O: return upper ? 'O' : 'o';
        case KEY_P: return upper ? 'P' : 'p';
        case KEY_Q: return upper ? 'Q' : 'q';
        case KEY_R: return upper ? 'R' : 'r';
        case KEY_S: return upper ? 'S' : 's';
        case KEY_T: return upper ? 'T' : 't';
        case KEY_U: return upper ? 'U' : 'u';
        case KEY_V: return upper ? 'V' : 'v';
        case KEY_W: return upper ? 'W' : 'w';
        case KEY_X: return upper ? 'X' : 'x';
        case KEY_Y: return upper ? 'Y' : 'y';
        case KEY_Z: return upper ? 'Z' : 'z';
        case KEY_1: return shift ? '!' : '1';
        case KEY_2: return shift ? '@' : '2';
        case KEY_3: return shift ? '#' : '3';
        case KEY_4: return shift ? '$' : '4';
        case KEY_5: return shift ? '%' : '5';
        case KEY_6: return shift ? '^' : '6';
        case KEY_7: return shift ? '&' : '7';
        case KEY_8: return shift ? '*' : '8';
        case KEY_9: return shift ? '(' : '9';
        case KEY_0: return shift ? ')' : '0';
        case KEY_SPACE: return ' ';
        case KEY_LEFTBRACE: return shift ? '{' : '[';
        case KEY_RIGHTBRACE: return shift ? '}' : ']';
        case KEY_SEMICOLON: return shift ? ':' : ';';
        case KEY_APOSTROPHE: return shift ? '"' : '\'';
        case KEY_GRAVE: return shift ? '~' : '`';
        case KEY_COMMA: return shift ? '<' : ',';
        case KEY_DOT: return shift ? '>' : '.';
        case KEY_SLASH: return shift ? '?' : '/';
        default: return 0;
    }
}

static bool is_keyboard_device(int fd) {
    char name[256] = {0};
    if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) >= 0) {
        if (strstr(name, VIRTUAL_DEV_NAME) != NULL) {
            return false; /* Never attach to our own virtual device */
        }
    }
    unsigned long evbit = 0;
    if (ioctl(fd, EVIOCGBIT(0, sizeof(evbit)), &evbit) < 0) return false;
    if (!(evbit & (1UL << EV_KEY))) return false;

    unsigned char keybit[KEY_MAX / 8 + 1];
    memset(keybit, 0, sizeof(keybit));
    if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(keybit)), keybit) < 0) return false;

    /* Check if device has standard letter keys KEY_Q, KEY_A, KEY_Z */
    bool has_q = (keybit[KEY_Q / 8] & (1 << (KEY_Q % 8))) != 0;
    bool has_a = (keybit[KEY_A / 8] & (1 << (KEY_A % 8))) != 0;
    bool has_z = (keybit[KEY_Z / 8] & (1 << (KEY_Z % 8))) != 0;
    return has_q && has_a && has_z;
}

static int discover_keyboards(struct pollfd *pfds, int max_devs) {
    DIR *d = opendir("/dev/input");
    if (!d) return 0;
    int count = 0;
    struct dirent *ent;
    while ((ent = readdir(d)) != NULL && count < max_devs) {
        if (strncmp(ent->d_name, "event", 5) != 0) continue;
        char path[300];
        snprintf(path, sizeof(path), "/dev/input/%s", ent->d_name);
        int fd = open(path, O_RDONLY | O_NONBLOCK);
        if (fd < 0) continue;
        if (is_keyboard_device(fd)) {
            pfds[count].fd = fd;
            pfds[count].events = POLLIN;
            count++;
        } else {
            close(fd);
        }
    }
    closedir(d);
    return count;
}

static size_t utf8_cp_len(const char *s) {
    if (!s) return 0;
    size_t n = 0;
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        if ((*p & 0xC0) != 0x80) n++;
    }
    return n;
}

int main(int argc, char **argv) {
    bool check_only = false;
    bool daemonize = false;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--check") == 0) check_only = true;
        else if (strcmp(argv[i], "--daemon") == 0 || strcmp(argv[i], "-d") == 0) daemonize = true;
        else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            printf("LotusKey Universal Evdev/UInput Daemon (v%s)\n", lotuskey_get_version());
            printf("Usage: lotuskey-uinput [--check] [--daemon|-d]\n");
            return 0;
        }
    }

    int ufd = setup_uinput_device();
    struct pollfd pfds[MAX_KBD_DEVICES];
    int n_kbds = discover_keyboards(pfds, MAX_KBD_DEVICES);

    if (check_only) {
        for (int i = 0; i < n_kbds; i++) close(pfds[i].fd);
        if (ufd >= 0) {
            ioctl(ufd, UI_DEV_DESTROY);
            close(ufd);
        }
        if (ufd >= 0 && n_kbds > 0) {
            printf("OK: uinput available, %d keyboard(s) detected.\n", n_kbds);
            return 0;
        } else {
            fprintf(stderr, "WARN: uinput_fd=%d, keyboards=%d (user may need input/uinput group permissions).\n", ufd, n_kbds);
            return 1;
        }
    }

    if (ufd < 0 || n_kbds == 0) {
        fprintf(stderr, "LotusKey UInput: Cannot open /dev/uinput or /dev/input/event* (ufd=%d, kbds=%d).\n", ufd, n_kbds);
        fprintf(stderr, "Tip: Run `sudo usermod -aG input $USER` and ensure /dev/uinput is writable.\n");
        for (int i = 0; i < n_kbds; i++) close(pfds[i].fd);
        if (ufd >= 0) close(ufd);
        return 1;
    }

    if (daemonize) {
        if (daemon(0, 0) < 0) {
            perror("daemon");
        }
    }

    signal(SIGINT, handle_sig);
    signal(SIGTERM, handle_sig);
    signal(SIGUSR1, handle_sig);

    UInputEngineState st;
    memset(&st, 0, sizeof(st));
    st.session = lotuskey_create_session();
    st.enabled = true;
    st.sen_flex = true;
    st.smart_bilingual = true;
    st.modern_orthography = true;
    st.w2u = true;
    st.bracket_transform = true;
    st.macro_enabled = true;
    load_daemon_config(&st);
    g_reload_requested = 0;

    while (g_running) {
        if (g_reload_requested) {
            load_daemon_config(&st);
            g_reload_requested = 0;
        }
        int prc = poll(pfds, (nfds_t)n_kbds, 500);
        if (prc <= 0) continue;

        for (int i = 0; i < n_kbds; i++) {
            if (!(pfds[i].revents & POLLIN)) continue;
            struct input_event ev;
            while (read(pfds[i].fd, &ev, sizeof(ev)) == sizeof(ev)) {
                if (ev.type != EV_KEY) continue;
                bool is_press = (ev.value == 1);
                bool is_release = (ev.value == 0);

                if (ev.code == KEY_LEFTSHIFT || ev.code == KEY_RIGHTSHIFT) {
                    if (is_release && st.ctrl_down && st.shift_down && !st.other_key_in_chord) {
                        st.enabled = !st.enabled;
                        lotuskey_reset_session(st.session);
                        st.prev_composed[0] = '\0';
                    }
                    st.shift_down = !is_release;
                    if (!st.ctrl_down && !st.shift_down) st.other_key_in_chord = false;
                    continue;
                }
                if (ev.code == KEY_LEFTCTRL || ev.code == KEY_RIGHTCTRL) {
                    if (is_release && st.ctrl_down && st.shift_down && !st.other_key_in_chord) {
                        st.enabled = !st.enabled;
                        lotuskey_reset_session(st.session);
                        st.prev_composed[0] = '\0';
                    }
                    st.ctrl_down = !is_release;
                    if (!st.ctrl_down && !st.shift_down) st.other_key_in_chord = false;
                    continue;
                }
                if (ev.code == KEY_LEFTALT || ev.code == KEY_RIGHTALT) {
                    st.alt_down = !is_release;
                    continue;
                }
                if (ev.code == KEY_LEFTMETA || ev.code == KEY_RIGHTMETA) {
                    st.super_down = !is_release;
                    continue;
                }
                if (ev.code == KEY_CAPSLOCK && is_press) {
                    st.capslock_on = !st.capslock_on;
                    continue;
                }

                if (!is_press) continue;
                if (st.ctrl_down || st.shift_down) st.other_key_in_chord = true;

                if (st.alt_down && ev.code == KEY_Z) {
                    st.enabled = !st.enabled;
                    lotuskey_reset_session(st.session);
                    st.prev_composed[0] = '\0';
                    continue;
                }

                if (!st.enabled || st.ctrl_down || st.alt_down || st.super_down) {
                    lotuskey_reset_session(st.session);
                    st.prev_composed[0] = '\0';
                    continue;
                }

                if (ev.code == KEY_BACKSPACE) {
                    if (lotuskey_is_composing(st.session)) {
                        lotuskey_feed_backspace(st.session);
                        const char *comp = lotuskey_get_composing_text(st.session);
                        snprintf(st.prev_composed, sizeof(st.prev_composed), "%s", comp ? comp : "");
                    } else {
                        st.prev_composed[0] = '\0';
                    }
                    continue;
                }

                char ch = evdev_code_to_ascii(ev.code, st.shift_down, st.capslock_on);
                if (ch == 0) {
                    lotuskey_reset_session(st.session);
                    st.prev_composed[0] = '\0';
                    continue;
                }

                bool is_alpha = (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z');
                bool is_digit = (ch >= '0' && ch <= '9');
                if (!is_alpha && !(st.input_method >= 1 && is_digit && lotuskey_is_composing(st.session))) {
                    if (ch == ' ' && st.macro_enabled && lotuskey_is_composing(st.session)) {
                        const char *comp = lotuskey_get_composing_text(st.session);
                        char expanded[512];
                        if (comp && lotus_macro_lookup(&g_macros, comp, expanded, sizeof(expanded))) {
                            size_t del_n = utf8_cp_len(comp) + 1; /* +1 for space */
                            emit_backspaces(ufd, del_n);
                            char final_str[520];
                            snprintf(final_str, sizeof(final_str), "%s ", expanded);
                            inject_utf8_text(final_str);
                        }
                    }
                    lotuskey_reset_session(st.session);
                    st.prev_composed[0] = '\0';
                    continue;
                }

                char prev_buf[512];
                snprintf(prev_buf, sizeof(prev_buf), "%s", st.prev_composed);

                lotuskey_feed_char(st.session, (uint32_t)(unsigned char)ch);
                const char *curr = lotuskey_get_composing_text(st.session);
                if (!curr) curr = "";

                /* Only replace if Vietnamese diacritics were formed (curr != prev_buf + ch) */
                char naive[520];
                snprintf(naive, sizeof(naive), "%s%c", prev_buf, ch);
                if (strcmp(curr, naive) != 0) {
                    size_t del_n = utf8_cp_len(prev_buf) + 1; /* +1 for raw key just typed */
                    emit_backspaces(ufd, del_n);
                    char converted[1024];
                    lotus_convert_charset(curr, st.charset, converted, sizeof(converted));
                    inject_utf8_text(converted);
                }
                snprintf(st.prev_composed, sizeof(st.prev_composed), "%s", curr);
            }
        }
    }

    lotuskey_destroy_session(st.session);
    for (int i = 0; i < n_kbds; i++) close(pfds[i].fd);
    if (ufd >= 0) {
        ioctl(ufd, UI_DEV_DESTROY);
        close(ufd);
    }
    return 0;
}
