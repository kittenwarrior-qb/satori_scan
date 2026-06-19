#!/usr/bin/env python3
"""
diagnose.py - Chay tai nha may de kiem tra tung thiet bi truoc khi cai chinh thuc.

  diagnose.exe                  # menu chon
  diagnose.exe scanner          # sniff scanner TCP
  diagnose.exe laser <IP> <PORT>
  diagnose.exe iobox <IP> <COIL>

LUU Y: Khong chay diagnose VA satori cung luc - ca hai deu dung cong 51236,
chi mot ben giu duoc. Test scanner xong phai DONG diagnose roi moi chay satori.
"""
import asyncio, socket, sys, textwrap, time


# ---------------------------------------------------------------
# 1. SCANNER - lang nghe TCP, in raw bytes + text
# ---------------------------------------------------------------
async def _scanner_server(host="0.0.0.0", port=51236):
    print(f"\n[Scanner] Dang lang nghe tai {host}:{port}  (Ctrl+C de dung)\n"
          f"  -> De may scan ket noi vao IP may tinh nay, port {port}\n"
          f"  -> Nho: dong CodeIT va satori.exe truoc, neu khong se ket noi nham!\n")

    async def handle(reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"  [OK] Scanner ket noi tu {addr}")
        buf = b""
        while True:
            chunk = await reader.read(256)
            if not chunk:
                print(f"  [!] Scanner {addr} ngat ket noi")
                break
            buf += chunk
            # In raw hex + text de xac dinh framing (STX/ETX, newline, ...)
            print(f"  RAW hex : {chunk.hex()}")
            print(f"  RAW text: {chunk!r}")
            # Tim STX/ETX
            while b"\x02" in buf and b"\x03" in buf:
                s = buf.index(b"\x02")
                e = buf.index(b"\x03", s)
                payload = buf[s+1:e].decode(errors="replace")
                print(f"  >>> MA  : {payload!r}")
                buf = buf[e+1:]

    srv = await asyncio.start_server(handle, host, port)
    async with srv:
        await srv.serve_forever()


def run_scanner(port=51236):
    try:
        asyncio.run(_scanner_server(port=int(port)))
    except KeyboardInterrupt:
        print("\n[Scanner] Da dung.")
    except OSError as e:
        print(f"\n[Scanner] LOI mo cong {port}: {e}")
        print("  -> Cong dang bi chiem. Dong CodeIT / satori.exe roi thu lai.")


def run_scanclient(host, port):
    """KET NOI TOI scanner (scanner la SERVER) va in byte tho khi quet."""
    port = int(port)
    print(f"\n[ScanClient] Ket noi toi scanner {host}:{port} ... (Ctrl+C de dung)")
    try:
        s = socket.create_connection((host, port), timeout=5)
    except Exception as e:
        print(f"  [LOI] Khong ket noi duoc: {e}")
        return
    s.settimeout(None)   # sau khi noi, CHO VO HAN de ban co thoi gian quet
    print("  [OK] Da ket noi. Hay QUET 1 chai that de xem du lieu:\n")
    buf = b""
    try:
        while True:
            chunk = s.recv(256)
            if not chunk:
                print("  [!] Scanner dong ket noi.")
                break
            print(f"  RAW hex : {chunk.hex()}")
            print(f"  RAW text: {chunk!r}")
            buf += chunk
            while b"\x02" in buf and b"\x03" in buf:
                a = buf.index(b"\x02")
                b = buf.index(b"\x03", a)
                print(f"  >>> MA  : {buf[a+1:b].decode(errors='replace')!r}")
                buf = buf[b+1:]
    except KeyboardInterrupt:
        print("\n[ScanClient] Da dung.")
    finally:
        s.close()


# ---------------------------------------------------------------
# 2. LASER - gui lenh thu nghiem
# ---------------------------------------------------------------
def run_laser(host, port, template=None):
    port = int(port)
    ma   = "TEST-" + time.strftime("%H%M%S")
    tmpl = template or "PRINT|{code}\r\n"
    cmd  = tmpl.format(code=ma).encode()

    print(f"\n[Laser] Ket noi {host}:{port}")
    print(f"        Gui   : {cmd!r}")
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
            print(f"        Phan hoi: {reply!r}")
        else:
            print("        Khong co phan hoi (binh thuong voi mot so hang)")
        print("  [OK] Gui thanh cong - kiem tra may in xem co in khong")
    except Exception as e:
        print(f"  [LOI] {e}")
        print(textwrap.dedent("""
  Goi y:
    - Kiem tra IP va port trong .env (LASER_HOST / LASER_PORT)
    - Thu ping IP may in tu cmd: ping <IP>
    - Xem tai lieu hang de tim format lenh, roi dat LASER_CMD_TEMPLATE trong .env
      Vi du: LASER_CMD_TEMPLATE={code}\\r\\n
        """))


# ---------------------------------------------------------------
# 3. IO-BOX - test ModBus coil
# ---------------------------------------------------------------
async def _iobox_test(host, port, coil):
    try:
        from pymodbus.client import AsyncModbusTcpClient
    except ImportError:
        print("  [LOI] Chua cai pymodbus: pip install pymodbus")
        return

    client = AsyncModbusTcpClient(host, port=port)
    print(f"\n[IO-Box] Ket noi ModBus TCP {host}:{port}  coil={coil}")
    await client.connect()
    if not client.connected:
        print("  [LOI] Khong ket noi duoc - kiem tra IP/port va nguon IO-Box")
        return

    print(f"  [OK] Ket noi OK")
    print(f"  -> Dang bat coil {coil}...")
    await client.write_coil(coil, True)
    await asyncio.sleep(0.5)
    r = await client.read_coils(coil, 1)
    state = r.bits[0] if not r.isError() else "ERR"
    print(f"     Doc lai coil {coil} = {state}")
    await asyncio.sleep(0.5)
    await client.write_coil(coil, False)
    print(f"  -> Da tat coil {coil}")
    client.close()
    print(textwrap.dedent(f"""
  Neu thiet bi (bang tai / xy-lanh) hoat dong -> day la dia chi dung.
  Cap nhat .env:
    IOBOX_COIL_BANG_TAI=<coil bang tai>
    IOBOX_COIL_DAY_LOAI=<coil day loai>
    """))


def run_iobox(host, port, coil):
    asyncio.run(_iobox_test(host, int(port), int(coil)))


# ---------------------------------------------------------------
# 5. DB PROBE - do xem database 10.1.1.106 la loai gi
# ---------------------------------------------------------------
def run_dbprobe(host):
    ports = [
        (1433, "Microsoft SQL Server"),
        (1434, "SQL Server Browser"),
        (3306, "MySQL / MariaDB"),
        (5432, "PostgreSQL"),
        (1521, "Oracle"),
        (27017, "MongoDB"),
    ]
    print(f"\n[DBProbe] Kiem tra database tren {host}:\n")
    found = []
    for p, name in ports:
        try:
            s = socket.create_connection((host, p), timeout=3)
            s.close()
            print(f"  [MO  ] cong {p:5} - {name}   <== co ve la DB nay")
            found.append((p, name))
        except Exception:
            print(f"  [dong] cong {p:5} - {name}")
    print()
    if found:
        print("  -> Loai DB:", ", ".join(n for _, n in found))
        print("  -> Bao lai cong nao MO de viet script keo toan bo data.")
    else:
        print("  -> Khong cong DB nao mo. Co the DB chay cuc bo, hoac sai IP.")
        print("     Thu xem file cau hinh cua CodeIT (connection string).")


# ---------------------------------------------------------------
# 4. NETWORK PING - kiem tra IP cac thiet bi
# ---------------------------------------------------------------
def run_ping():
    import subprocess, platform
    targets = [
        ("Scanner",  "192.168.1.40"),
        ("IO-Box",   "192.168.1.50"),
        ("Laser",    "192.168.1.60"),
    ]
    flag = "-n" if platform.system() == "Windows" else "-c"
    print("\n[Ping] Kiem tra ket noi mang...\n")
    for name, ip in targets:
        r = subprocess.run(["ping", flag, "1", "-w", "1000", ip],
                           capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"  {'[OK]' if ok else '[--]'} {name:10s} {ip:16s}  "
              f"{'OK' if ok else 'KHONG PHAN HOI'}")
    print("\n  Neu IP sai: do lai tu tu dien roi sua .env")


# ---------------------------------------------------------------
# MENU
# ---------------------------------------------------------------
def menu():
    print(textwrap.dedent("""
    ============================================
       SATORI v2 - Cong cu chan doan thiet bi
    ============================================
    Chon:
      1) Ping tat ca thiet bi
      2) Test Scanner (KET NOI TOI scanner - scanner la SERVER)
      3) Test Laser     (gui lenh in thu)
      4) Test IO-Box    (bat/tat mot coil)
      5) Sniff Scanner  (CHO scanner goi vao - kieu cu)
      6) DB Probe       (do database CodeIT la loai gi)
      q) Thoat
    """))
    choice = input("Nhap lua chon: ").strip().lower()

    if choice == "6":
        h = input("IP database [10.1.1.106]: ").strip() or "10.1.1.106"
        run_dbprobe(h)
    elif choice == "1":
        run_ping()
    elif choice == "2":
        h = input("IP scanner [10.1.1.126]: ").strip() or "10.1.1.126"
        p = input("Port scanner [51236]: ").strip() or "51236"
        run_scanclient(h, p)
    elif choice == "5":
        p = input("Port scanner [51236]: ").strip() or "51236"
        run_scanner(p)
    elif choice == "3":
        h = input("IP laser [192.168.1.60]: ").strip() or "192.168.1.60"
        p = input("Port laser [9100]: ").strip() or "9100"
        t = input("Template lenh [{code}\\r\\n]: ").strip() or None
        run_laser(h, p, t)
    elif choice == "4":
        h = input("IP IO-Box [192.168.1.50]: ").strip() or "192.168.1.50"
        p = input("Port ModBus [502]: ").strip() or "502"
        c = input("Coil so muon test [0]: ").strip() or "0"
        run_iobox(h, p, c)
    elif choice in ("q", ""):
        sys.exit(0)
    else:
        print("Khong hop le.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        menu()
    elif args[0] == "scanner":
        run_scanner(args[1] if len(args) > 1 else 51236)
    elif args[0] == "scanclient":
        run_scanclient(args[1], args[2] if len(args) > 2 else 51236)
    elif args[0] == "laser":
        run_laser(args[1], args[2], args[3] if len(args) > 3 else None)
    elif args[0] == "iobox":
        run_iobox(args[1], args[2], args[3])
    elif args[0] == "ping":
        run_ping()
    elif args[0] == "dbprobe":
        run_dbprobe(args[1] if len(args) > 1 else "10.1.1.106")
    else:
        print(__doc__)
