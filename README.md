# LotusKey

Bộ gõ tiếng Việt cho Linux (Wayland & X11), hỗ trợ giao diện song ngữ Việt / Anh và tương thích đa nền tảng bộ gõ (**IBus**, **Fcitx5**, **Fcitx4**, **Evdev/UInput**).

Vietnamese input method for Linux (Wayland & X11) with bilingual UI (Vietnamese / English) and multi-framework support (**IBus**, **Fcitx5**, **Fcitx4**, **Evdev/UInput**).

---

## Tính năng chính / Key Features

- **Đa hệ thống bộ gõ (Multi-Backend)**:
  - **IBus (`ibus-engine-lotuskey`)**: Engine C chạy trực tiếp trên GNOME, Ubuntu, Fedora, Cinnamon, MATE, Budgie.
  - **Fcitx5 (`fcitx5`)**: Đồng bộ cấu hình và bảng gõ tắt cho KDE Plasma, Hyprland, Sway, Cosmic, LXQt.
  - **Fcitx4 (`fcitx`)**: Hỗ trợ XFCE và các bản phân phối truyền thống.
  - **UInput Daemon (`lotuskey-uinput`)**: Daemon cấp nhân (`/dev/input` -> `/dev/uinput`) cho các Window Manager độc lập (i3wm, bspwm, dwm, Sway, Hyprland).
- **Kiểu gõ & Bảng mã (Input Methods & Charsets)**:
  - Hỗ trợ **Telex**, **VNI** và **Telex + VNI** kết hợp.
  - Xuất văn bản theo bảng mã **Unicode (UTF-8 dựng sẵn)**, **Unicode tổ hợp (NFD)**, **TCVN3 (ABC)** và **VNI Windows**.
- **Xử lý gõ ổn định trên Wayland/Electron**:
  - Chế độ **Pre-edit** chống mất chữ trên Chromium, VS Code, Electron.
  - Tự động chuyển về Pre-edit khi ứng dụng không hỗ trợ Surrounding Text.
- **Tiện ích gõ nhanh**:
  - Bảng gõ tắt (Macro) tự khớp chữ hoa/thường (`vn` -> `Việt Nam`, `VN` -> `VIỆT NAM`).
  - Gõ nhanh phụ âm (`cc=ch`, `gg=gi`, `kk=kh`, `nn=ng`, `qq=qu`, `pp=ph`, `tt=th`), `w -> ư`, `[ ] -> ơ ư`.
  - Menu nhanh (phím `` ` ``) có độ trễ chống nhiễu 220ms: bấm đơn mở menu, bấm đúp `` `` `` hoặc gõ liền `` `code` `` giữ nguyên ký tự.
- **Giao diện song ngữ (`Tiếng Việt` / `English`)**:
  - Chuyển đổi trực tiếp ngôn ngữ hiển thị trong Cài đặt, Menu nhanh và Trình cài đặt.

---

## Cài đặt / Installation

### 1. Cài đặt tự động từ mã nguồn / Build & Install
```bash
./install.sh
```

Khởi chạy trình cài đặt đồ họa (Setup Wizard):
```bash
./setup.sh
```

Cấp quyền `/dev/uinput` cho chế độ UInput Daemon (tùy chọn):
```bash
./install.sh --setup-udev
```

### 2. Đóng gói theo bản phân phối / Native Packaging
- **Debian / Ubuntu / Linux Mint (`.deb`)**:
  ```bash
  ./packaging/build_deb.sh
  sudo dpkg -i ibus-lotuskey_2.2.0_amd64.deb
  ```
- **Arch Linux / Manjaro / CachyOS (`PKGBUILD`)**:
  ```bash
  cd packaging && makepkg -si
  ```
- **Fedora / RHEL / openSUSE (`.rpm`)**:
  Sử dụng [`packaging/ibus-lotuskey.spec`](packaging/ibus-lotuskey.spec) với `rpmbuild`.

---

## Phím tắt / Shortcuts

- **Chuyển chế độ Việt / Anh**: `Ctrl + Shift`, `Alt + Z`, hoặc `Shift + Space` (tùy chọn trong cài đặt).
- **Mở Menu nhanh**: Phím `` ` `` (bấm đúp `` `` `` để nhập dấu backtick).
- **Mở Cài đặt**: Chạy lệnh `lotuskey` hoặc `lotuskey-setup`, hoặc mở từ danh sách ứng dụng.

---

## Cấu trúc thư mục / Directory Layout

```
lotuskey/
├── assets/                  # Biểu tượng trạng thái SVG (lotuskey.svg, lotuskey-off.svg)
├── bin/                     # Tệp thực thi (ibus-engine-lotuskey, lotuskey-uinput, launchers)
├── config/                  # Quản lý cấu hình, ngôn ngữ (i18n), nhận diện distro & IM backend
├── include/                 # Header C-ABI (lotuskey.h, lotus_charset.h) & IBus fallback header
├── lib/                     # Thư viện lõi C-ABI (libLotusKeyCAPI.so)
├── packaging/               # Kịch bản đóng gói (.deb, PKGBUILD, RPM spec)
├── src/                     # Mã nguồn C cho IBus Engine và UInput Daemon
├── ui/                      # Giao diện GTK (setup_panel.py, quick_menu.py, setup_wizard.py)
└── install.sh               # Kịch bản biên dịch và cài đặt
```

---

## Giấy phép / License

MIT License — Tác giả: Victor Pham.
