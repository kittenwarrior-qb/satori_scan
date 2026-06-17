"""Sinh & parse mã chai yyMMddCCCCC (11 số)."""
from datetime import date
from typing import Optional


def generate_ma_chai(ngay_sx: date, counter: int) -> str:
    """Sinh mã yyMMddCCCCC. VD: 08/01/2020 + counter 9 -> 20010800009."""
    return ngay_sx.strftime("%y%m%d") + str(counter).zfill(5)


def parse_ma_chai(ma: str) -> Optional[dict]:
    """Parse mã 11 số. Trả None nếu không hợp lệ."""
    if not ma or len(ma) != 11 or not ma.isdigit():
        return None
    return {
        "nam": 2000 + int(ma[0:2]),
        "thang": int(ma[2:4]),
        "ngay": int(ma[4:6]),
        "counter": int(ma[6:11]),
    }
