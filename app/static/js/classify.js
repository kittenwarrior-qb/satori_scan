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
};

deviceBar("device-bar");

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
    if (d.event !== "scan") return;
    const st = STATUS[d.ket_qua] || STATUS.NOREAD;

    // Quét trùng: BÁO ĐỎ nhưng KHÔNG đếm, KHÔNG thêm dòng (cùng 1 chai).
    if (d.ket_qua === "DUPLICATE") {
        toast(`⚠ Quét trùng — bỏ qua: ${d.ma_chai}`, "err", 4000);
        const p = document.getElementById("scan-result");
        p.className = "scan-big scan-err";
        p.innerHTML = `<div class="sb-icon">${st.icon}</div>
            <div class="sb-ma">${d.ma_chai || "—"}</div>
            <span class="sb-badge badge err">${st.label}</span>`;
        return;
    }

    count++;
    if (d.ket_qua === "OK") ok++; else err++;

    const row = document.createElement("div");
    row.className = `table-row classify-grid ${st.cls}`;
    row.innerHTML = `
        <span>${count}</span>
        <span>${d.ma_chai || "—"}</span>
        <span>${new Date().toLocaleTimeString("vi-VN")}</span>
        <span>${d.gioi_han ?? "—"}</span>
        <span>${d.so_lan_thuc_te ?? "—"}</span>
        <span class="badge ${st.cls}">${st.label}</span>`;
    document.getElementById("rows").prepend(row);

    document.getElementById("count").textContent = count;
    document.getElementById("stat-ok").textContent = ok;
    document.getElementById("stat-err").textContent = err;

    const panel = document.getElementById("scan-result");
    const clsMap = { ok: "scan-ok", err: "scan-err", warn: "scan-warn" };
    panel.className = `scan-big ${clsMap[st.cls] || "scan-idle"}`;
    panel.innerHTML = `
        <div class="sb-icon">${st.icon}</div>
        <div class="sb-ma">${d.ma_chai || "—"}</div>
        <span class="sb-badge badge ${st.cls}">${st.label}</span>`;
});

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
        toast(`Kết thúc ca — Hợp lệ: ${d.tong_hop_le}, Lỗi: ${d.tong_loi}`, "info", 5000);
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
