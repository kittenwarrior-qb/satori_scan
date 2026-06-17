"""Test logic mã chai + phân loại (không cần DB/thiết bị)."""
from datetime import date

from app.services.ma_chai import generate_ma_chai, parse_ma_chai


def test_generate():
    assert generate_ma_chai(date(2020, 1, 8), 9) == "20010800009"
    assert generate_ma_chai(date(2018, 10, 29), 1) == "18102900001"


def test_parse_valid():
    r = parse_ma_chai("20010800009")
    assert r["nam"] == 2020
    assert r["thang"] == 1
    assert r["ngay"] == 8
    assert r["counter"] == 9


def test_parse_invalid():
    assert parse_ma_chai("NOREAD") is None
    assert parse_ma_chai("123") is None
    assert parse_ma_chai("abcdefghijk") is None
    assert parse_ma_chai("") is None
    assert parse_ma_chai("200108000099") is None  # 12 số


def test_roundtrip():
    for c in (1, 42, 99999):
        ma = generate_ma_chai(date(2020, 1, 8), c)
        assert parse_ma_chai(ma)["counter"] == c
