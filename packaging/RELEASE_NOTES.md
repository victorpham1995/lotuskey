## 🪷 LotusKey v2.2.1

### Sửa lỗi / Bug fixes
- **Sửa crash `SIGSEGV` khi gõ phím**: cấu trúc `IBusEngine` lệch ABI (80 → 88 bytes) khiến `libibus` ghi đè con trỏ phiên gõ.
- **Sửa lỗi engine không kết nối được IBus sau khi khởi động lại máy**: socket `~/.config/ibus/bus/*-unix-0` cũ giờ được thay bằng symlink động + tự động dò `ibus-daemon` còn sống.
- **Sửa lỗi không mở được Cài đặt (Settings)**: xung đột `Gdk 4.0` / `Gtk 3.0` trong PyGObject.

### Bản cài đặt / Downloads

| Distro | File | Cài đặt |
|---|---|---|
| Debian / Ubuntu ≥ 22.04 / Mint / Pop!_OS / Zorin | `ibus-lotuskey_2.2.1_amd64.deb` | `sudo apt install ./ibus-lotuskey_2.2.1_amd64.deb` |
| Fedora / RHEL / Rocky / Alma | `ibus-lotuskey-2.2.1-1.x86_64.fedora.rpm` | `sudo dnf install ./ibus-lotuskey-*.fedora.rpm` |
| openSUSE Tumbleweed / Leap | `ibus-lotuskey-2.2.1-1.x86_64.opensuse.rpm` | `sudo zypper install --allow-unsigned-rpm ./ibus-lotuskey-*.opensuse.rpm` |
| Arch / Manjaro / EndeavourOS | `ibus-lotuskey-2.2.1-1-x86_64.pkg.tar.zst` | `sudo pacman -U ./ibus-lotuskey-2.2.1-1-x86_64.pkg.tar.zst` |
| Mọi distro (không cần root) | `LotusKey-2.2.1-x86_64.AppImage` | `chmod +x LotusKey-*.AppImage && ./LotusKey-*.AppImage` |
| Mọi distro (từ mã nguồn + binary dựng sẵn) | `lotuskey-2.2.1-linux-x86_64.tar.gz` | `tar xf lotuskey-*.tar.gz && cd lotuskey-*/ && ./install.sh` |

> **AppImage**: chạy lần đầu sẽ tự cài cho user hiện tại vào `~/.local/share/lotuskey/app` rồi mở Cài đặt. Dùng `--uninstall` để gỡ, `--help` để xem tuỳ chọn.
> Yêu cầu runtime: `ibus`, `python3`, `python3-gi` (PyGObject), GTK3, glibc ≥ 2.35.

Sau khi cài gói hệ thống, chạy `ibus restart` (hoặc đăng xuất/đăng nhập) rồi thêm **LotusKey** trong *Settings → Keyboard → Input Sources*.

Kiểm tra toàn vẹn file: `sha256sum -c SHA256SUMS.txt`
