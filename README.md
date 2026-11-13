# 🪷 LotusKey: Bộ Gõ Tiếng Việt Đa Nền Tảng Cho Linux (IBus • Fcitx5 • Fcitx4 • UInput)

Bộ gõ tiếng Việt thế hệ mới cho Linux (**Wayland & X11**), tối ưu hóa hiệu năng với kiến trúc đa Backend:
1. **Lõi C-ABI siêu tốc (`libLotusKeyCAPI`)** với cơ chế **Atomic Trail Commit** triệt tiêu hoàn toàn hiện tượng nuốt chữ/mất ký tự trên Electron/Chromium (VS Code, Antigravity IDE, Chrome, Slack).
2. **Multi-Framework Linux Adapter** tự động thích ứng với mọi môi trường Desktop và Window Manager:
   - **IBus Native Engine (`ibus-engine-lotuskey`)**: Mặc định tối ưu cho GNOME, Ubuntu, Fedora, Cinnamon, MATE, Budgie.
   - **Fcitx5 Adapter (`fcitx5` + `lotus`)**: Đồng bộ cấu hình & Macro trực tiếp cho KDE Plasma, Hyprland, Sway, Cosmic, LXQt, XFCE.
   - **Fcitx4 Legacy Adapter (`fcitx`)**: Tương thích ngược cho XFCE / Linux Mint cổ điển.
   - **Evdev / UInput Universal Daemon (`lotuskey-uinput`)**: Daemon C chạy trực tiếp ở tầng nhân (`/dev/input` $\rightarrow$ `/dev/uinput`) cho mọi Window Manager (i3wm, bspwm, dwm, Sway, Hyprland) không cần qua IM module của GTK/Qt.
3. **Zero-Syscall Keystroke Path**: Sử dụng `GFileMonitor` (inotify) và `g_unix_signal_add(SIGUSR1)` trên GLib MainLoop cùng thông báo D-Bus trực tiếp (`org.freedesktop.Notifications`), đạt **0 syscall I/O trên đường truyền phím**.

---

## 🚀 Các Tính Năng Nổi Bật

| Tính năng | Mô tả chi tiết |
| :--- | :--- |
| **Đa Hệ Thống Bộ Gõ (Multi-Backend)** | Tự động nhận diện hoặc chuyển đổi 1 chạm giữa **Auto**, **IBus**, **Fcitx5**, **Fcitx4**, và **UInput Daemon**. |
| **Không bao giờ mất chữ trên Wayland** | Cơ chế **Atomic Trail Commit** + tự động fallback từ Surrounding Text về Pre-edit khi ứng dụng (Electron/Chromium) không hỗ trợ Surrounding Text. |
| **Telex, VNI & Hybrid (Telex + VNI)** | Hỗ trợ gõ thuần Telex, thuần VNI, hoặc gõ kết hợp cả hai (**Telex + VNI**) cùng lúc. |
| **Hỗ trợ đầy đủ Bảng mã** | Xuất trực tiếp **Unicode (UTF-8 dựng sẵn)**, **Unicode Tổ hợp (NFD)**, **TCVN3 (ABC)** và **VNI Windows**. |
| **Bảng Gõ Tắt (Macro Expansion)** | Quản lý từ viết tắt trực quan trong Bảng điều khiển, tự động khớp chữ hoa/thường (`vn` $\rightarrow$ `Việt Nam`, `VN` $\rightarrow$ `VIỆT NAM`). |
| **Gõ nhanh `[` $\rightarrow$ `ơ`, `]` $\rightarrow$ `ư`** | Tích hợp trực tiếp vào âm tiết đang gõ (`h[n` $\rightarrow$ `hơn`, `t]s` $\rightarrow$ `tứ`, gõ đúp `[[` $\rightarrow$ `[`). |
| **Quick Menu phím `` ` `` thông minh** | Bấm đơn phím `` ` `` mở nhanh Floating Quick Menu; bấm đúp `` `` `` hoặc gõ liền `` `code` `` giữ nguyên ký tự `` ` `` mà không làm mất focus cửa sổ. |

---

## 🛠️ Cài Đặt & Biên Dịch Tự Động

Chỉ cần chạy tập lệnh cài đặt:
```bash
./install.sh
```
Hoặc khởi chạy trình cài đặt đồ họa (Setup Wizard):
```bash
./setup.sh
```
Để cấp quyền `/dev/uinput` không cần `root` cho chế độ **Evdev/UInput Universal Daemon**:
```bash
./install.sh --setup-udev
```

Tập lệnh sẽ tự động:
- Nhận diện bản phân phối Linux (**Ubuntu/Debian/Mint**, **Fedora/RHEL/Nobara**, **Arch/Manjaro/CachyOS**, **openSUSE**, **Alpine/Void musl**, **NixOS/Silverblue**) và kiến trúc CPU (`x86_64`, `aarch64`, `riscv64`).
- Kiểm tra tương thích ABI của [`libLotusKeyCAPI.so`](lib/libLotusKeyCAPI.so); nếu hệ thống dùng `GLIBC < 2.38`, `musl` hoặc `ARM64`, tự động biên dịch lại `libLotusKeyCAPI.so` từ mã nguồn C++20 ([`src/lotuskey_capi_fallback.cpp`](src/lotuskey_capi_fallback.cpp) + `core/*.cpp`).
- Biên dịch Native C IBus Engine ([`src/main.c`](src/main.c)) với cơ chế fallback header [`include/ibus_fallback/ibus.h`](include/ibus_fallback/ibus.h) (không bắt buộc cài `libibus-1.0-dev` / `ibus-devel`) và Universal UInput Daemon ([`src/uinput_daemon.c`](src/uinput_daemon.c)).
- Cài đặt bộ Icon SVG độc lập ([`assets/lotuskey.svg`](assets/lotuskey.svg), [`assets/lotuskey-off.svg`](assets/lotuskey-off.svg)), tạo động `lotuskey.xml` và đồng bộ sang Fcitx5 (`lotus.conf` & `bamboo.conf`).

### 📦 Đóng gói Native Package cho các Distro
- **Debian / Ubuntu / Mint (`.deb`)**: `./packaging/build_deb.sh`
- **Arch Linux / Manjaro / CachyOS (`PKGBUILD`)**: `cd packaging && makepkg -si`
- **Fedora / RHEL / openSUSE (`.rpm`)**: Dùng [`packaging/ibus-lotuskey.spec`](packaging/ibus-lotuskey.spec) với `rpmbuild`

---

## ⌨️ Phím Tắt & Thao Tác Nhanh

- **Bật / Tắt Tiếng Việt:**
  - `Ctrl + Shift` (chuẩn Unikey).
  - Hoặc `Alt + Z` / `Shift + Space`.
- **Mở Quick Menu Dialog:**
  - Bấm phím `` ` `` (grave key). Bấm đúp `` `` `` để gõ dấu backtick.
- **Mở Bảng điều khiển (Control Panel & Macro Editor):**
  - Chạy lệnh `lotuskey` hoặc `lotuskey-setup` trong Terminal, hoặc mở ứng dụng **"LotusKey - Bảng điều khiển"** từ App Grid.

---

## 📂 Cấu Trúc Mã Nguồn

```
ibus-LotusKey/
├── bin/
│   ├── ibus-engine-lotuskey     # Binary thực thi native C chạy dưới IBus Daemon
│   ├── lotuskey-uinput          # Binary thực thi Evdev/UInput Universal Daemon
│   ├── lotuskey-menu            # Launcher mở Floating Quick Menu
│   └── lotuskey-setup           # Launcher mở Bảng điều khiển & Trình sửa Gõ tắt
├── src/
│   ├── main.c                   # Mã nguồn C IBus Engine
│   └── uinput_daemon.c          # Mã nguồn C Evdev/UInput Daemon
├── include/
│   ├── lotuskey.h               # Header C-ABI lõi xử lý tiếng Việt
│   └── lotus_charset.h          # Bộ chuyển đổi Bảng mã (NFD/TCVN3/VNI) & Macro Table
├── lib/
│   └── libLotusKeyCAPI.so       # Thư viện C-ABI xử lý gõ tiếng Việt siêu tốc
├── config/
│   ├── config_manager.py        # Quản lý cấu hình JSON, config.env & macros.conf
│   └── im_framework.py          # Multi-Framework Adapter (IBus / Fcitx5 / Fcitx4 / UInput)
├── ui/
│   ├── quick_menu.py            # Cửa sổ nổi hiện đại (mở khi bấm phím `)
│   ├── setup_panel.py           # Bảng điều khiển & Quản lý Gõ tắt (GTK3)
│   └── setup_wizard.py          # Trình cài đặt đồ họa Setup Wizard
└── install.sh                   # Script biên dịch, cài đặt & đồng bộ đa bộ gõ
```
