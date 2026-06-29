// ── Màn hình PHÂN LOẠI ──
let count = 0, ok = 0, err = 0;
let activeBatchId = null;

// ── Âm thanh báo (xưởng ồn — công nhân không nhìn màn hình liên tục) ──
let _audioCtx = null;
function _ensureAudio() {
    try {
        if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (_audioCtx.state === "suspended") _audioCtx.resume();
    } catch { _audioCtx = null; }
    return _audioCtx;
}
function _beep(freq, durMs, gain = 0.25) {
    const ctx = _ensureAudio();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = "square";
    osc.frequency.value = freq;
    g.gain.value = gain;
    osc.connect(g); g.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + durMs / 1000);
}
function alarmReject() { _beep(380, 350); }                 // 1 tiếng trầm = loại
function alarmFault() {                                      // 3 tiếng gấp = sự cố
    _beep(880, 150);
    setTimeout(() => _beep(880, 150), 200);
    setTimeout(() => _beep(880, 150), 400);
}

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

// ── Cảnh báo tỉ lệ loại cao bất thường (sai lô / lệch máy quét) ──
const _recent = [];
function trackRejectRate(isOk) {
    _recent.push(isOk);
    if (_recent.length > 20) _recent.shift();
    const fails = _recent.filter(x => !x).length;
    const warn = document.getElementById("reject-warn");
    if (!warn) return;
    if (_recent.length >= 8 && fails / _recent.length >= 0.4) {
        warn.style.display = "block";
        warn.textContent =
            `⚠ Tỉ lệ loại cao bất thường (${fails}/${_recent.length} chai gần đây) — ` +
            `kiểm tra đúng lô SX và vị trí máy quét`;
    } else {
        warn.style.display = "none";
    }
}

deviceBar("device-bar");

// Đồng bộ counter từ server sau khi WS kết nối lại
async function syncCounters() {
    try {
        const sess = await api("/api/sessions/active?che_do=PHAN_LOAI");
        if (sess.active) {
            ok    = sess.tong_hop_le;
            err   = sess.tong_loi;
            count = ok + err;
            document.getElementById("count").textContent    = count;
            document.getElementById("stat-ok").textContent  = ok;
            document.getElementById("stat-err").textContent = err;
        }
    } catch {}
}

// Tải thông tin lô SX + đồng bộ counter
async function loadActiveInfo() {
    try {
        const sess = await api("/api/sessions/active?che_do=PHAN_LOAI");
        if (sess.active) {
            activeBatchId = sess.production_batch_id;
            ok    = sess.tong_hop_le;
            err   = sess.tong_loi;
            count = ok + err;
            document.getElementById("count").textContent    = count;
            document.getElementById("stat-ok").textContent  = ok;
            document.getElementById("stat-err").textContent = err;
            const batches = await api("/api/identify/batches");
            const b = batches.find(x => x.id === activeBatchId);
            if (b) {
                document.getElementById("lo-sx").textContent  = b.so_lo_san_xuat;
                document.getElementById("ngay-sx").textContent = b.ngay_san_xuat;
            }
        }
    } catch {}
}
loadActiveInfo();

// WebSocket — đồng bộ counter khi kết nối lại (onOpen)
connectWS(wsHandler, syncCounters);

function wsHandler(d) {
    if (d.event === "iobox_fault") {
        alarmFault();
        toast(`⚠ IO-Box lỗi — chai có thể không bị đẩy ra! ${d.message || ""}`, "err", 15000);
        return;
    }
    if (d.event === "error") {
        alarmReject();
        toast(d.message || "Lỗi xử lý quét", "err", 8000);
        return;
    }
    if (d.event !== "scan") return;

    const st = STATUS[d.ket_qua] || STATUS.NOREAD;

    // Cảnh báo IO-Box nếu chai loại nhưng đẩy không thành công
    if (d.iobox_fault) {
        alarmFault();
        toast(`⚠ IO-Box không đẩy được chai ${d.ma_chai || ""} — lấy ra thủ công!`, "err", 15000);
    }

    // Quét trùng: BÁO ĐỎ nhưng KHÔNG đếm, KHÔNG thêm dòng
    if (d.ket_qua === "DUPLICATE") {
        toast(`⚠ Quét trùng — bỏ qua: ${d.ma_chai}`, "err", 4000);
        const p = document.getElementById("scan-result");
        p.className = "scan-big scan-err scan-flash";
        p.innerHTML = `<div class="sb-icon">${st.icon}</div>
            <div class="sb-ma">${d.ma_chai || "—"}</div>
            <span class="sb-badge badge err">${st.label}</span>`;
        return;
    }

    count++;
    const isOk = d.ket_qua === "OK";
    if (isOk) ok++; else err++;

    // Âm thanh: chỉ kêu khi LOẠI (OK thì im để tránh nhức tai cả ca)
    if (!isOk) alarmReject();
    trackRejectRate(isOk);

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

    document.getElementById("count").textContent    = count;
    document.getElementById("stat-ok").textContent  = ok;
    document.getElementById("stat-err").textContent = err;

    const panel = document.getElementById("scan-result");
    panel.dataset.scanned = "1";
    const clsMap = { ok: "scan-ok", err: "scan-err", warn: "scan-warn" };
    // reflow để animation chạy lại mỗi lần quét
    panel.className = "scan-big";
    void panel.offsetWidth;
    panel.className = `scan-big ${clsMap[st.cls] || "scan-idle"}${isOk ? "" : " scan-flash"}`;
    panel.innerHTML = `
        <div class="sb-icon">${st.icon}</div>
        <div class="sb-ma">${d.ma_chai || "—"}</div>
        <span class="sb-badge badge ${st.cls}">${st.label}</span>`;
}

function setSessionState(running) {
    const pill     = document.getElementById("session-status");
    const btnStart = document.getElementById("btn-start");
    const btnEnd   = document.getElementById("btn-end");
    const panel    = document.getElementById("scan-result");
    if (running) {
        pill.textContent  = "⬤ Ca đang chạy";
        pill.className    = "session-pill session-running";
        btnStart.disabled = true;
        btnEnd.disabled   = false;
        // Chỉ đặt trạng thái "chờ quét" nếu chưa có kết quả nào
        if (panel && panel.dataset.scanned !== "1") {
            panel.className = "scan-big scan-idle";
            panel.innerHTML =
                `<div class="sb-icon">&#128269;</div><div class="sb-ma">Chờ quét...</div>`;
        }
    } else {
        pill.textContent  = "⬤ Chưa bắt đầu";
        pill.className    = "session-pill session-idle";
        btnStart.disabled = false;
        btnEnd.disabled   = true;
        if (panel) {
            panel.dataset.scanned = "0";
            panel.className = "scan-big scan-paused";
            panel.innerHTML =
                `<div class="sb-icon">&#9208;</div>
                 <div class="sb-ma">CHƯA BẮT ĐẦU CA</div>
                 <span class="sb-badge" style="background:#475569;color:#fff">Bấm "Bắt đầu" để quét</span>`;
        }
        const warn = document.getElementById("reject-warn");
        if (warn) warn.style.display = "none";
        _recent.length = 0;
    }
}

// Kiểm tra ca khi load trang
api("/api/sessions/active?che_do=PHAN_LOAI")
    .then(d => setSessionState(d.active)).catch(() => {});

// Bắt đầu ca — disable ngay trước await để tránh double-click
document.getElementById("btn-start").onclick = async () => {
    const btn = document.getElementById("btn-start");
    _ensureAudio();   // mở khóa âm thanh bằng cử chỉ người dùng (yêu cầu của trình duyệt)
    btn.disabled = true;
    try {
        if (!activeBatchId) {
            toast("Chưa chọn lô sản xuất — nhấn 'Cập nhật lô SX' trước", "err");
            btn.disabled = false;
            return;
        }
        await api("/api/sessions/start", "POST", {
            che_do: "PHAN_LOAI", production_batch_id: activeBatchId,
        });
        setSessionState(true);
        toast("Đã bắt đầu ca phân loại", "ok");
        loadActiveInfo();
    } catch (e) {
        if (e.message && e.message.includes("ca đang chạy")) {
            toast("⚠ Có ca đang bị treo từ trước. Liên hệ quản lý để Phục hồi ca.", "err", 10000);
        } else {
            toast(e.message, "err");
        }
        btn.disabled = false;
    }
};

// Kết thúc ca — hiển thị modal tổng kết thay vì toast
document.getElementById("btn-end").onclick = async () => {
    const btn = document.getElementById("btn-end");
    btn.disabled = true;
    try {
        const d = await api("/api/sessions/end", "POST", { che_do: "PHAN_LOAI" });
        setSessionState(false);
        count = ok = err = 0;
        _showShiftEndModal(d.tong_hop_le, d.tong_loi);
    } catch (e) {
        btn.disabled = false;
        toast(e.message, "err");
    }
};

function _showShiftEndModal(hopLe, loi) {
    const tong = hopLe + loi;
    const rate = tong ? ((loi / tong) * 100).toFixed(1) : "0.0";
    const overlay = document.createElement("div");
    overlay.className = "overlay";
    overlay.style.zIndex = "5000";
    overlay.innerHTML = `
      <div class="modal" style="min-width:300px;max-width:380px;text-align:center"
           onclick="event.stopPropagation()">
        <div class="modal-header">Kết thúc ca phân loại</div>
        <div class="modal-body" style="padding:24px 20px">
          <div style="font-size:36px;font-weight:800;color:var(--ok);line-height:1">${hopLe}</div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:16px">Chai hợp lệ</div>
          <div style="font-size:28px;font-weight:700;color:var(--err);line-height:1">${loi}</div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Chai lỗi</div>
          <div style="font-size:13px;color:var(--muted)">Tỉ lệ lỗi: <b>${rate}%</b></div>
        </div>
        <div class="modal-actions">
          <button class="btn-confirm" onclick="this.closest('.overlay').remove()">Đã ghi nhận</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
}

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
