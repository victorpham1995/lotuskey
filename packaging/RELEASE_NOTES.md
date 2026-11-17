## 🪷 LotusKey v2.3.0

### Điểm nổi bật phiên bản 2.3.0 / Release Highlights
- **Hỗ trợ toàn diện kiến trúc ARM64 (`aarch64`)**: Tích hợp source engine C-ABI di động (`src/capi/lotuskey_capi.c`) cho phép tự động biên dịch `libLotusKeyCAPI.so` native trên bất kỳ vi kiến trúc nào (x86_64, aarch64, riscv64, v.v.).
- **Đạt 100% Behavioral Parity Test**: Toàn bộ 28 bài kiểm thử C-ABI (Telex, VNI, SEN Flex free tone, Quick Telex, Modern Orthography, Backspace, Charset) đều vượt qua và khớp chuẩn xác giữa bản biên dịch mã nguồn và binary gốc.
- **Tự động nhận diện kiến trúc & Fallback thông minh**: `distro_adapter.py` và `build_binaries.sh` tự động kiểm tra ELF Machine type, nếu kiến trúc không khớp sẽ tự biên dịch mã nguồn trong vài giây.
- **Hệ thống Menu 2 tầng chuẩn mực (Submenu & Dropdown UX)**: Thu gọn khay hệ thống SNI và IBus Property Menu thành 9 mục chính với 5 menu phụ tiện dụng.
- **Thiết kế biểu tượng cờ phẳng (Flat Flag Design)**: Bộ 9 biểu tượng SVG phẳng không uốn lượn, tối ưu hiển thị trên GNOME, KDE Plasma, XFCE, Hyprland, Sway.
- **Tự động khởi chạy & hỗ trợ đa nền tảng**: Tự nhận diện và tương thích tất cả bản phân phối Linux phổ biến với các định dạng: `.deb`, `.rpm`, `.pkg.tar.zst`, `.AppImage`, `.run`, `.tar.gz`, `flake.nix`.

### Bản cài đặt / Downloads

| Distro | File (`x86_64` / `aarch64`) | Cài đặt |
|---|---|---|
| Debian / Ubuntu ≥ 22.04 / Mint / Pop!_OS / Zorin | `ibus-lotuskey_2.3.0_amd64.deb` / `ibus-lotuskey_2.3.0_arm64.deb` | `sudo apt install ./ibus-lotuskey_2.3.0_*.deb` |
| Fedora / RHEL / Rocky / Alma / Nobara | `ibus-lotuskey-2.3.0-1.x86_64.fedora.rpm` | `sudo dnf install ./ibus-lotuskey-*.fedora.rpm` |
| openSUSE Tumbleweed / Leap | `ibus-lotuskey-2.3.0-1.x86_64.opensuse.rpm` | `sudo zypper install --allow-unsigned-rpm ./ibus-lotuskey-*.opensuse.rpm` |
| Arch / Manjaro / EndeavourOS / CachyOS | `ibus-lotuskey-2.3.0-1-x86_64.pkg.tar.zst` | `sudo pacman -U ./ibus-lotuskey-2.3.0-1-*.pkg.tar.zst` |
| Mọi distro (Gói tự giải nén độc lập, không cần FUSE) | `LotusKey-2.3.0-linux-x86_64.run` / `LotusKey-2.3.0-linux-aarch64.run` | `chmod +x LotusKey-*.run && ./LotusKey-*.run` |
| Mọi distro (AppImage di động) | `LotusKey-2.3.0-x86_64.AppImage` / `LotusKey-2.3.0-aarch64.AppImage` | `chmod +x LotusKey-*.AppImage && ./LotusKey-*.AppImage` |
| Mọi distro (Mã nguồn + binary dựng sẵn) | `lotuskey-2.3.0-linux-x86_64.tar.gz` / `lotuskey-2.3.0-linux-aarch64.tar.gz` | `tar xf lotuskey-*.tar.gz && cd lotuskey-*/ && ./install.sh` |
| NixOS / Nix Flakes | `flake.nix` (`x86_64-linux`, `aarch64-linux`) | `nix run github:victorpham1995/lotuskey` |

> **Gói `.run` & `AppImage`**: chạy lần đầu sẽ tự cài cho user hiện tại vào `~/.local/share/lotuskey/app` rồi mở Cài đặt. Dùng `--wizard` để mở trình cài đặt đồ họa, `--silent` để cài ngầm, `--system` (với `.run`) để cài toàn hệ thống, `--uninstall` để gỡ, `--help` để xem tuỳ chọn.
> Yêu cầu runtime: `ibus`, `python3`, `python3-gi` (PyGObject), GTK3, `librsvg`, glibc ≥ 2.35.

Sau khi cài gói hệ thống, chạy `ibus restart` (hoặc đăng xuất/đăng nhập) rồi thêm **LotusKey** trong *Settings → Keyboard → Input Sources*.

Kiểm tra toàn vẹn file: `sha256sum -c SHA256SUMS.txt`
