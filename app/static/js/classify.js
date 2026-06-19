// ── Màn hình PHÂN LOẠI ──
let count = 0, ok = 0, err = 0;
let activeBatchId = 1;

// Hiện dev-bar nếu đang mock
api("/api/is-mock").then(d => {
    const bar = document.getElementById("dev-bar");
    if (bar) bar.style.display = d.mock ? "flex" : "none";
}).catch(() => {});

const STATUS = {
    OK:         { label: "Hợp lệ",           cls: "ok",   icon: "✅" },
    NOREAD:     { label: "Không đọc được",    cls: "err",  icon: "❌" },
    UNKNOWN:    { label: "Mã không tồn tại",  cls: "err",  icon: "❌" },
    OVER_LIMIT: { label: "Vượt giới hạn",     cls: "warn", icon: "⚠️" },
    REJECTED:   { label: "Đã loại trước đó",  cls: "err",  icon: "❌" },
    DUPLICATE:  { label: "QUÉT TRÙNG",        cls: "err",  icon: "🔁" },
    ALREADY_UPDATED: { label: "Mã chai đã được cập nhật", cls: "err", icon: "🔁" },
};

deviceBar("device-bar");

// Đồng bộ mọi nơi hiển thị tổng (panel phải + chân bảng + dòng đếm)
function syncTotals() {
    document.getElementById("count").textContent = count;
    document.getElementById("stat-ok").textContent = ok;
    document.getElementById("stat-err").textContent = err;
    document.getElementById("total-count").textContent = count;
    document.getElementById("total-ok").textContent = ok;
    document.getElementById("total-err").textContent = err;
}

// Tạo 1 dòng kết quả quét (dùng chung cho realtime và khi nạp lại)
function makeRow(num, data, ts) {
    const st = STATUS[data.ket_qua] || STATUS.NOREAD;
    const row = document.createElement("div");
    row.className = `table-row classify-grid ${st.cls}`;
    row.innerHTML = `
        <span>${num}</span>
        <span>${data.ma_chai || "NoRead"}</span>
        <span>${ts}</span>
        <span>${data.gioi_han ?? "—"}</span>
        <span>${data.so_lan_thuc_te ?? "—"}</span>
        <span class="badge ${st.cls}">${st.label}</span>`;
    return row;
}

// Nạp lại danh sách đã quét của ca đang chạy (sau khi chuyển tab quay lại)
async function restoreScans() {
    try {
        const d = await api("/api/classify/scans", "GET", { limit: 200 });
        if (!d.active) return;
        count = d.count; ok = d.tong_hop_le; err = d.tong_loi;
        syncTotals();
        // d.scans: mới → cũ. Append theo thứ tự đó ⇒ mới nhất nằm trên cùng.
        const rowsEl = document.getElementById("rows");
        let n = count;
        for (const s of d.scans) {
            const ts = s.scanned_at
                ? new Date(s.scanned_at).toLocaleTimeString("vi-VN") : "—";
            rowsEl.appendChild(makeRow(n, s, ts));
            n--;
        }
    } catch {}
}
restoreScans();

// Tải thông tin lô SX đang chạy
async function loadActiveInfo() {
    try {
        const sess = await api("/api/sessions/active?che_do=PHAN_LOAI");
        if (sess.active) {
            activeBatchId = sess.production_batch_id;
            const batches = await api("/api/identify/batches");
            const b = batches.find(x => x.id === activeBatchId);
            if (b) {
                document.getElementById("lo-sx").textContent = b.so_lo_san_xuat;
                document.getElementById("ngay-sx").textContent = b.ngay_san_xuat;
            }
        }
    } catch {}
}
loadActiveInfo();

// WebSocket nhận kết quả quét realtime
connectWS(d => {
    if (d.event === "error") { toast(d.message || "Lỗi xử lý quét", "err"); return; }
    // Có quét nhưng chưa bấm "Bắt đầu" ca → cảnh báo, không đếm/không lưu
    if (d.event === "scan_no_session") {
        toast(`⚠️ Có quét (${d.ma_chai || "?"}) nhưng CHƯA bấm "Bắt đầu" ca`,
              "err", 4000);
        const p = document.getElementById("scan-result");
        if (p) {
            p.className = "scan-big scan-warn";
            p.innerHTML = `<div class="sb-icon">⚠️</div>
                <div class="sb-ma">${d.ma_chai || "NoRead"}</div>
                <span class="sb-badge badge warn">Chưa bắt đầu ca</span>`;
        }
        return;
    }
    if (d.event !== "scan") return;
    const st = STATUS[d.ket_qua] || STATUS.NOREAD;

    // Quét trùng: BÁO ĐỎ nhưng KHÔNG đếm, KHÔNG thêm dòng (cùng 1 chai).
    if (d.ket_qua === "DUPLICATE") {
        toast(`⚠ Quét trùng — bỏ qua: ${d.ma_chai}`, "err", 4000);
        const p = document.getElementById("scan-result");
        p.className = "scan-big scan-err";
        p.innerHTML = `<div class="sb-icon">${st.icon}</div>
            <div class="sb-ma">${d.ma_chai || "NoRead"}</div>
            <span class="sb-badge badge err">${st.label}</span>`;
        return;
    }

    count++;
    if (d.ket_qua === "OK") ok++; else err++;

    const ts = new Date().toLocaleTimeString("vi-VN");
    document.getElementById("rows").prepend(makeRow(count, d, ts));
    syncTotals();

    const panel = document.getElementById("scan-result");
    const clsMap = { ok: "scan-ok", err: "scan-err", warn: "scan-warn" };
    panel.className = `scan-big ${clsMap[st.cls] || "scan-idle"}`;
    panel.innerHTML = `
        <div class="sb-icon">${st.icon}</div>
        <div class="sb-ma">${d.ma_chai || "NoRead"}</div>
        <span class="sb-badge badge ${st.cls}">${st.label}</span>`;
});

// Xóa sạch dữ liệu hiển thị (data ca đã lưu trong DB) — về trạng thái trống.
function clearScreen() {
    count = 0; ok = 0; err = 0;
    syncTotals();
    document.getElementById("rows").innerHTML = "";
    const p = document.getElementById("scan-result");
    if (p) {
        p.className = "scan-big scan-idle";
        p.innerHTML = `<div class="sb-icon">&#128269;</div>
            <div class="sb-ma">Chờ quét...</div>`;
    }
}

function setSessionState(running) {
    const pill = document.getElementById("session-status");
    const btnStart = document.getElementById("btn-start");
    const btnEnd   = document.getElementById("btn-end");
    if (running) {
        pill.textContent = "⬤ Ca đang chạy";
        pill.className   = "session-pill session-running";
        btnStart.disabled = true;
        btnEnd.disabled   = false;
    } else {
        pill.textContent = "⬤ Chưa bắt đầu";
        pill.className   = "session-pill session-idle";
        btnStart.disabled = false;
        btnEnd.disabled   = true;
    }
}

// Kiểm tra ca hiện tại khi load trang
api("/api/sessions/active?che_do=PHAN_LOAI").then(d => setSessionState(d.active)).catch(() => {});

// Bắt đầu ca
document.getElementById("btn-start").onclick = async () => {
    try {
        await api("/api/sessions/start", "POST", {
            che_do: "PHAN_LOAI", production_batch_id: activeBatchId
        });
        clearScreen();              // ca mới → bắt đầu lại từ đầu
        setSessionState(true);
        toast("Đã bắt đầu ca phân loại", "ok");
        loadActiveInfo();
    } catch (e) { toast(e.message, "err"); }
};

// Kết thúc ca
document.getElementById("btn-end").onclick = async () => {
    try {
        const d = await api("/api/sessions/end", "POST", { che_do: "PHAN_LOAI" });
        setSessionState(false);
        toast(`Kết thúc ca — Hợp lệ: ${d.tong_hop_le}, Lỗi: ${d.tong_loi} `
              + `(đã lưu vào báo cáo)`, "info", 5000);
        clearScreen();              // xóa hết hiển thị — data ca đã lưu DB
    } catch (e) { toast(e.message, "err"); }
};

// Dev tools — giả lập quét
document.getElementById("btn-test").onclick = async () => {
    const ma = document.getElementById("test-ma").value.trim();
    if (!ma) return;
    await fetch(`/api/classify/test?ma_chai=${encodeURIComponent(ma)}`, { method: "POST" });
};
document.getElementById("btn-auto").onclick = async () => {
    toast("Đang gửi 20 chai...", "info");
    for (let i = 1; i <= 20; i++) {
        const roll = Math.random();
        let ma;
        if (roll < 0.15) ma = "NOREAD";
        else if (roll < 0.25) ma = "29991200099";
        else ma = "200108000" + String(Math.floor(Math.random() * 10) + 1).padStart(2, "0");
        await fetch(`/api/classify/test?ma_chai=${encodeURIComponent(ma)}`, { method: "POST" });
        await new Promise(r => setTimeout(r, 220));
    }
};
