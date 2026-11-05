# 🪷 LotusKey (ibus-LotusKey): Bộ Gõ Tiếng Việt Native Cho Ubuntu GNOME Wayland

Bộ gõ tiếng Việt thế hệ mới, tối ưu hóa 100% cho **Ubuntu GNOME Wayland**, kết hợp giữa:
1. **Lõi C-ABI đa nền tảng siêu tốc (VieLotus Core)** với cơ chế Atomic Trail Commit triệt tiêu hoàn toàn hiện tượng nuốt chữ/mất ký tự trên Electron/Chromium (VS Code, Antigravity IDE, Chrome).
2. **Kiến trúc Native C IBus Engine** (`ibus-engine-lotuskey`) trực tiếp xử lý sự kiện phím với độ trễ xấp xỉ 0ms, không phụ thuộc vào lớp bọc Python runtime hay quyền trợ năng.
3. **Cửa sổ Quick Menu Floating & Bảng điều khiển kiểu Unikey** được thiết kế hiện đại, tùy biến linh hoạt, khởi động cùng hệ thống.

---

## 🚀 Các Tính Năng Đột Phá

| Tính năng | Mô tả chi tiết |
| :--- | :--- |
| **Không bao giờ mất chữ trên Wayland** | Cơ chế **Atomic Trail Commit** gộp từ và phím kết thúc (Space/dấu câu) vào 1 gói commit duy nhất, chặn triệt để xung đột race condition giữa IBus và Electron. |
| **Hỗ trợ đầy đủ Telex & VNI** | Chuyển đổi linh hoạt giữa `lotuskey` (Telex) và `lotuskey-vni` (VNI). |
| **Khôi phục lỗi gõ stop-coda** | Tự sửa phím dấu gõ nhầm (`vieetfj` $\rightarrow$ `việt`). |
| **Whole-character Backspace** | Xóa lần lượt từng ký tự hoàn chỉnh (`việt` $\rightarrow$ `việ` $\rightarrow$ `vi` $\rightarrow$ `v`) thay vì rơi vào trạng thái gỡ dấu rườm rà. |
| **Quick Menu phím `` ` `` (Grave)** | Bấm phím `` ` `` để mở nhanh menu nổi (dark theme). Bấm nhanh 2 lần để gõ ký tự `` ` `` thô trong code markdown / terminal. |
| **Chuyển đổi ngôn ngữ kiểu Unikey** | Hỗ trợ phím tắt **`Ctrl + Shift`** hoặc **`Alt + Z`** để bật/tắt tiếng Việt nhanh. |
| **Khởi động cùng hệ thống (Autostart)** | Tự khởi động cùng OS qua XDG Autostart và GNOME Input Sources. |

---

## 🛠️ Cài Đặt & Biên Dịch Tự Động

Chỉ cần chạy tập lệnh cài đặt:
```bash
cd /home/victorpham/.gemini/antigravity/scratch/ibus-LotusKey
./install.sh
```

Tập lệnh sẽ tự động:
- Biên dịch mã nguồn C [`src/main.c`](file:///home/victorpham/.gemini/antigravity/scratch/ibus-LotusKey/src/main.c) liên kết với [`libVieLotusCAPI.so`](file:///home/victorpham/.gemini/antigravity/scratch/ibus-LotusKey/lib/libVieLotusCAPI.so).
- Cài đặt component descriptor [`engine/lotus.xml`](file:///home/victorpham/.gemini/antigravity/scratch/ibus-LotusKey/engine/lotus.xml) vào `~/.local/share/ibus/component/`.
- Cập nhật bộ đệm IBus Registry cache và kích hoạt nguồn gõ trong GNOME Shell.
- Thiết lập tự động khởi động cùng hệ thống (`~/.config/autostart/lotuskey.desktop`).

---

## ⌨️ Phím Tắt & Thao Tác Nhanh

- **Bật / Tắt Tiếng Việt:**
  - `Ctrl + Shift` (chuẩn Unikey Windows).
  - Hoặc `Alt + Z`.
  - Hoặc `Super + Space` (chuyển đổi nguồn gõ GNOME).
- **Mở Quick Menu Dialog:**
  - Bấm phím `` ` `` (grave key).
- **Mở Bảng điều khiển (Unikey Style):**
  - Chạy lệnh `lotuskey` hoặc `lotuskey-setup` trong Terminal hoặc mở ứng dụng **"LotusKey - Bảng điều khiển"** từ App Grid.

---

## 📂 Cấu Trúc Mã Nguồn

```
ibus-LotusKey/
├── bin/
│   ├── ibus-engine-lotuskey     # Binary thực thi native C chạy dưới IBus Daemon
│   ├── lotuskey-menu            # Launcher mở Floating Quick Menu
│   └── lotuskey-setup           # Launcher mở Bảng điều khiển kiểu Unikey
├── src/
│   └── main.c                   # Toàn bộ mã nguồn C IBus Engine
├── lib/
│   └── libVieLotusCAPI.so       # Thư viện C-ABI xử lý gõ tiếng Việt siêu tốc
├── include/
│   └── vielotus.h               # Header C-ABI
├── config/
│   └── config_manager.py        # Quản lý cấu hình JSON & file môi trường config.env
├── ui/
│   ├── quick_menu.py            # Cửa sổ nổi hiện đại (mở khi bấm phím `)
│   └── setup_panel.py           # Bảng điều khiển Unikey Style (GTK3)
├── engine/
│   └── lotus.xml                # IBus Component Descriptor
└── install.sh                   # Script cài đặt & đồng bộ IBus Registry cache
```
