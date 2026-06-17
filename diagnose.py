#!/usr/bin/env python3
"""
diagnose.py — Chạy tại nhà máy để kiểm tra từng thiết bị trước khi cài chính thức.

  python diagnose.py                  # menu chọn
  python diagnose.py scanner          # sniff scanner TCP
  python diagnose.py laser <IP> <PORT>
  python diagnose.py iobox <IP> <COIL>
"""
import asyncio, socket, sys, textwrap, time


# ───────────────────────────────────────────────
# 1. SCANNER — lắng nghe TCP, in raw bytes + text
# ───────────────────────────────────────────────
async def _scanner_server(host="0.0.0.0", port=51236):
    print(f"\n[Scanner] Đang lắng nghe tại {host}:{port}  (Ctrl+C để dừng)\n"
          f"  → Để máy scan kết nối vào IP máy tính này, port {port}\n")

    async def handle(reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"  ✅ Scanner kết nối từ {addr}")
        buf = b""
        while True:
            chunk = await reader.read(256)
            if not chunk:
                print(f"  ⚠ Scanner {addr} ngắt kết nối")
                break
            buf += chunk
            # In raw hex + text để xác định framing (STX/ETX, newline, ...)
            print(f"  RAW hex : {chunk.hex()}")
            print(f"  RAW text: {chunk!r}")
            # Tìm STX/ETX
            while b"\x02" in buf and b"\x03" in buf:
                s = buf.index(b"\x02")
                e = buf.index(b"\x03", s)
                payload = buf[s+1:e].decode(errors="replace")
                print(f"  >>> MÃ  : {payload!r}")
                buf = buf[e+1:]

    srv = await asyncio.start_server(handle, host, port)
    async with srv:
        await srv.serve_forever()


def run_scanner(port=51236):
    try:
        asyncio.run(_scanner_server(port=int(port)))
    except KeyboardInterrupt:
        print("\n[Scanner] Đã dừng.")


# ───────────────────────────────────────────────
# 2. LASER — gửi lệnh thử nghiệm
# ───────────────────────────────────────────────
def run_laser(host, port, template=None):
    port = int(port)
    ma   = "TEST-" + time.strftime("%H%M%S")
    tmpl = template or "PRINT|{code}\r\n"
    cmd  = tmpl.format(code=ma).encode()

    print(f"\n[Laser] Kết nối {host}:{port}")
    print(f"        Gửi   : {cmd!r}")
    try:
        s = socket.create_connection((host, port), timeout=5)
        s.sendall(cmd)
        time.sleep(0.5)
        reply = b""
        s.settimeout(2)
        try:
            while True:
                part = s.recv(256)
                if not part:
                    break
                reply += part
        except socket.timeout:
            pass
        s.close()
        if reply:
            print(f"        Phản hồi: {reply!r}")
        else:
            print("        Không có phản hồi (bình thường với một số hãng)")
        print("  ✅ Gửi thành công — kiểm tra máy in xem có in không")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
        print(textwrap.dedent("""
  Gợi ý:
    • Kiểm tra IP và port trong .env (LASER_HOST / LASER_PORT)
    • Thử ping IP máy in từ cmd: ping <IP>
    • Xem tài liệu hãng để tìm format lệnh, rồi đặt LASER_CMD_TEMPLATE trong .env
      Ví dụ: LASER_CMD_TEMPLATE={code}\\r\\n
        """))


# ───────────────────────────────────────────────
# 3. IO-BOX — test ModBus coil
# ───────────────────────────────────────────────
async def _iobox_test(host, port, coil):
    try:
        from pymodbus.client import AsyncModbusTcpClient
    except ImportError:
        print("  ❌ Chưa cài pymodbus: pip install pymodbus")
        return

    client = AsyncModbusTcpClient(host, port=port)
    print(f"\n[IO-Box] Kết nối ModBus TCP {host}:{port}  coil={coil}")
    await client.connect()
    if not client.connected:
        print("  ❌ Không kết nối được — kiểm tra IP/port và nguồn IO-Box")
        return

    print(f"  ✅ Kết nối OK")
    print(f"  → Đang bật coil {coil}...")
    await client.write_coil(coil, True)
    await asyncio.sleep(0.5)
    r = await client.read_coils(coil, 1)
    state = r.bits[0] if not r.isError() else "ERR"
    print(f"     Đọc lại coil {coil} = {state}")
    await asyncio.sleep(0.5)
    await client.write_coil(coil, False)
    print(f"  → Đã tắt coil {coil}")
    client.close()
    print(textwrap.dedent(f"""
  Nếu thiết bị (băng tải / xy-lanh) hoạt động → đây là địa chỉ đúng.
  Cập nhật .env:
    IOBOX_COIL_BANG_TAI=<coil băng tải>
    IOBOX_COIL_DAY_LOAI=<coil đẩy loại>
    """))


def run_iobox(host, port, coil):
    asyncio.run(_iobox_test(host, int(port), int(coil)))


# ───────────────────────────────────────────────
# 4. NETWORK PING — kiểm tra IP các thiết bị
# ───────────────────────────────────────────────
def run_ping():
    import subprocess, platform
    targets = [
        ("Scanner",  "192.168.1.40"),
        ("IO-Box",   "192.168.1.50"),
        ("Laser",    "192.168.1.60"),
    ]
    flag = "-n" if platform.system() == "Windows" else "-c"
    print("\n[Ping] Kiểm tra kết nối mạng...\n")
    for name, ip in targets:
        r = subprocess.run(["ping", flag, "1", "-w", "1000", ip],
                           capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"  {'✅' if ok else '❌'} {name:10s} {ip:16s}  {'OK' if ok else 'KHÔNG PHẢN HỒI'}")
    print("\n  Nếu IP sai: đo lại từ tủ điện rồi sửa .env")


# ───────────────────────────────────────────────
# MENU
# ───────────────────────────────────────────────
def menu():
    print(textwrap.dedent("""
    ╔══════════════════════════════════════════╗
    ║   SATORI v2 — Công cụ chẩn đoán thiết bị ║
    ╚══════════════════════════════════════════╝
    Chọn:
      1) Ping tất cả thiết bị
      2) Sniff Scanner  (xem raw bytes / mã chai)
      3) Test Laser     (gửi lệnh in thử)
      4) Test IO-Box    (bật/tắt một coil)
      q) Thoát
    """))
    choice = input("Nhập lựa chọn: ").strip().lower()

    if choice == "1":
        run_ping()
    elif choice == "2":
        p = input("Port scanner [51236]: ").strip() or "51236"
        run_scanner(p)
    elif choice == "3":
        h = input("IP laser [192.168.1.60]: ").strip() or "192.168.1.60"
        p = input("Port laser [9100]: ").strip() or "9100"
        t = input("Template lệnh [{code}\\r\\n]: ").strip() or None
        run_laser(h, p, t)
    elif choice == "4":
        h = input("IP IO-Box [192.168.1.50]: ").strip() or "192.168.1.50"
        p = input("Port ModBus [502]: ").strip() or "502"
        c = input("Coil số muốn test [0]: ").strip() or "0"
        run_iobox(h, p, c)
    elif choice in ("q", ""):
        sys.exit(0)
    else:
        print("Không hợp lệ.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        menu()
    elif args[0] == "scanner":
        run_scanner(args[1] if len(args) > 1 else 51236)
    elif args[0] == "laser":
        run_laser(args[1], args[2], args[3] if len(args) > 3 else None)
    elif args[0] == "iobox":
        run_iobox(args[1], args[2], args[3])
    elif args[0] == "ping":
        run_ping()
    else:
        print(__doc__)
