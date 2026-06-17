"""Cấu hình toàn hệ thống, đọc từ .env (xem .env.example)."""
from typing import List, Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/satori.db"
    use_mock_devices: bool = True

    # Hỗ trợ nhiều scanner: "host:port,host:port,..."
    scanner_hosts: str = "192.168.1.40:51236"

    iobox_host: str = "192.168.1.50"
    iobox_port: int = 502
    laser_host: str = "192.168.1.60"
    laser_port: int = 9100

    web_host: str = "0.0.0.0"
    web_port: int = 8000
    admin_password: str = "stradmin"

    # ── Sao lưu DB tự động (chỉ SQLite; Postgres dùng pg_dump bên ngoài) ──
    backup_enabled: bool = True
    backup_interval_hours: float = 6.0   # chu kỳ sao lưu
    backup_keep: int = 30                # giữ lại N bản mới nhất
    backup_dir: str = "data/backups"

    # Chống quét trùng: cùng 1 mã quét lại trong khoảng (giây) này coi là 1 lần
    # (nhiễu băng tải / cảm biến kích 2 lần / quét tay lặp). 0 = tắt.
    classify_debounce_sec: float = 2.0

    # ── IO-Box coil addresses (lấy từ bảng I/O tủ điện) ──
    iobox_coil_bang_tai: int = 0    # coil bật/tắt băng tải
    iobox_coil_day_loai: int = 1    # coil kích xy-lanh đẩy loại
    iobox_pulse_width: float = 0.3  # giây giữ xung đẩy loại

    # ── Laser printer command format ──
    # Dùng {code} làm placeholder cho mã chai
    # Ví dụ: "PRINT|{code}\r\n"  hoặc  "{code}\r\n"  hoặc  "P{code}\n"
    laser_cmd_template: str = "PRINT|{code}\r\n"

    @property
    def scanner_list(self) -> List[Tuple[str, int]]:
        """Parse SCANNER_HOSTS thành danh sách (host, port)."""
        result: List[Tuple[str, int]] = []
        for item in self.scanner_hosts.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" in item:
                host, port = item.rsplit(":", 1)
                result.append((host.strip(), int(port)))
            else:
                result.append((item, 51236))
        return result


settings = Settings()
