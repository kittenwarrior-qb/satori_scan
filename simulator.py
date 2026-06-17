"""Giả lập dây chuyền — gửi mã quét vào backend đang chạy.

Chạy backend trước (python run.py hoặc uvicorn), rồi:
    python simulator.py                 # 50 chai, 1s/chai
    python simulator.py 3000 0.05       # test chịu tải
"""
import asyncio
import random
import sys
from datetime import date

import httpx

API = "http://127.0.0.1:8000/api"


async def run(count=50, delay=1.0):
    today = date.today()
    async with httpx.AsyncClient(timeout=10) as c:
        # Bắt đầu ca phân loại
        r = await c.post(f"{API}/sessions/start",
                         params={"che_do": "PHAN_LOAI", "production_batch_id": 1})
        if r.status_code != 200:
            print("Lưu ý:", r.json().get("detail"))

        for i in range(count):
            roll = random.random()
            if roll < 0.10:
                ma = "NOREAD"
            elif roll < 0.15:
                ma = "X" + str(random.randint(1000000000, 9999999999))  # unknown
            else:
                # 70% mã seed (20010800001..10), 30% mã hôm nay (có thể UNKNOWN)
                if random.random() < 0.7:
                    ma = "200108000" + str(random.randint(1, 10)).zfill(2)
                else:
                    ma = today.strftime("%y%m%d") + str(random.randint(1, 30)).zfill(5)

            await c.post(f"{API}/classify/test", params={"ma_chai": ma})
            print(f"[{i+1}/{count}] gửi: {ma}")
            await asyncio.sleep(delay)

        print("Xong. Mở http://127.0.0.1:8000/classify để xem bảng.")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    asyncio.run(run(count, delay))
