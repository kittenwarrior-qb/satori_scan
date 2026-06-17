# SATORI v2 — Quản lý vỏ bình 5 Gallon

Phần mềm thay thế **CodeIT Enterprise 4.0**, gắn vào tủ PC/PLC dây chuyền.
Toàn bộ Python (FastAPI + Jinja2 + JS thuần + WebSocket), đóng gói thành `.exe`.

3 chức năng: **Định danh** (in mã `yyMMddCCCCC`) · **Phân loại** (quét → so giới hạn TSD → OK +1 / đẩy loại) · **Quản lý & Báo cáo** (Excel).

Thiết bị: Scanner (TCP, hỗ trợ **nhiều máy**) · IO-Box (ModBus TCP) · Laser (TCP) · Băng tải.
Mọi driver có 2 bản **Mock** (dev tại nhà) và **Real** (tại site), đổi bằng `.env`.

---

## Chạy nhanh tại nhà (mock thiết bị, SQLite)

```bash
# 1. Môi trường ảo + thư viện
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# 2. Cấu hình
copy .env.example .env           # (đã có sẵn .env dev)

# 3. Tạo DB + dữ liệu mẫu
python init_db.py
python seed.py

# 4. Chạy server
uvicorn app.main:app --reload --port 8000
#  → mở http://127.0.0.1:8000
```

### Thử nghiệm
- Mở **/classify** → bấm **Bắt đầu** → bấm **Auto 20 chai** (hoặc nhập mã + Giả lập quét).
- Hoặc chạy `python simulator.py` (backend phải đang chạy) để bắn 50 chai.
- **/identify** → chọn lô → Bắt đầu → In 1 chai (mã tăng dần, có QR).
- **/reject** → nhập/keypad mã → OK (đánh dấu loại).
- **/reports** → xuất Excel, tìm kiếm theo Lô SX / Lô NCC / Mã chai.

Dữ liệu mẫu: mã `20010800001`..`20010800010` (00008–00010 đã đủ 5 lần → bị loại).

---

## Test

```bash
pip install pytest pytest-asyncio httpx
pytest -v
```

---

## Đóng gói .exe (triển khai tủ PC)

```bash
pip install pyinstaller
build_exe.bat            # → dist\satori.exe
```

Copy `dist\satori.exe` + `.env` lên tủ PC. Double-click → mở fullscreen (kiosk).
Auto-start: bỏ shortcut vào `shell:startup` hoặc Task Scheduler. Xem `docs/implementation/I6_PACKAGING.md`.

---

## Ra site — chuyển sang thiết bị thật

Chỉ sửa `.env`, **không sửa code logic**:
```ini
USE_MOCK_DEVICES=false
SCANNER_HOSTS=192.168.1.40:51236,192.168.1.41:51236,192.168.1.42:51236   # 3 scanner
IOBOX_HOST=192.168.1.50
LASER_HOST=192.168.1.60
DATABASE_URL=postgresql://postgres:matkhau@localhost:5432/satori
```
Rồi điền địa chỉ coil ModBus thật vào `app/devices/iobox.py` (`RealIOBox.COIL_*`)
và lệnh in vào `app/devices/laser.py` (`RealLaser.print_code`). Xem `docs/implementation/I7_TESTING.md`.

---

## Cấu trúc

```
app/
  main.py            FastAPI app + WebSocket + lifespan thiết bị
  config.py          đọc .env (gồm parse nhiều scanner)
  paths.py           resource_path cho PyInstaller
  database/          connection, models, crud
  devices/           base, scanner, iobox, laser, manager (mock+real, multi-scanner)
  services/          ma_chai, classify, identify, reject, report
  routers/           pages, sessions, classify, identify, reports
  templates/ static/ UI 5 màn hình
init_db.py seed.py   tạo bảng + dữ liệu mẫu
simulator.py         giả lập dây chuyền
run.py build_exe.bat đóng gói .exe + kiosk
tests/               unit test
```

Tài liệu thiết kế đầy đủ: thư mục cha `docs/` (01–06) và `docs/implementation/` (I0–I7).
