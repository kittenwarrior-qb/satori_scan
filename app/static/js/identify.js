// ── Màn hình ĐỊNH DANH ──
let count = 0, ok = 0, err = 0;
let batches = [];

deviceBar("device-bar");

// Hiện dev-bar nếu đang mock
api("/api/is-mock").then(d => {
    if (d.mock) {
        const bar = document.getElementById("dev-bar-id");
        if (bar) bar.style.display = "flex";
    }
}).catch(() => {});

function currentBatchId() {
    return parseInt(document.getElementById("batch-select").value, 10);
}

async function loadBatches() {
    try {
        batches = await api("/api/identify/batches");
        const sel = document.getElementById("batch-select");
        if (!batches.length) {
            sel.innerHTML = '<option value="">— Chưa có lô SX —</option>';
            toast("Chưa có lô sản xuất — hãy tạo lô trước khi bắt đầu", "err", 8000);
            return;
        }
        sel.innerHTML = batches.map(b =>
            `<option value="${b.id}">${b.so_lo_san_xuat} — ${b.ngay_san_xuat}</option>`
        ).join("");
        renderInfo();
    } catch (e) {
        toast(`Không tải được danh sách lô: ${e.message}`, "err", 8000);
    }
}

function renderInfo() {
    const b = batches.find(x => x.id === currentBatchId());
    if (!b) return;
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? "—"; };
    set("f-nha-cc",    b.nha_cung_cap);
    set("f-lo-ncc",    b.so_lo_ncc);
    set("f-so-luong",  b.so_luong_chai);
    set("f-so-lan",    b.so_lan_tai_su_dung);
    set("f-lo-sx-val", b.so_lo_san_xuat);
    set("f-ngay-sx",   b.ngay_san_xuat);
}

document.getElementById("batch-select").onchange = renderInfo;
loadBatches();

// Đồng bộ counter từ server khi WS kết nối lại
async function syncCounters() {
    try {
        const sess = await api("/api/sessions/active?che_do=DINH_DANH");
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

// Nhận sự kiện in qua WS
connectWS(wsHandler, syncCounters);

function wsHandler(d) {
    if (d.event === "error") {
        toast(d.message || "Lỗi xử lý", "err", 8000);
        return;
    }
    if (d.event === "print_failed") {
        err++;
        document.getElementById("stat-err").textContent = err;
        const ma = d.ma_chai || "?";
        toast(`⚠ Laser lỗi — mã ${ma} chưa được in! Bấm "In lại" để thử lại.`, "err", 0);
        _showReprintPrompt(ma);
        return;
    }
    if (d.event !== "print") return;
    count++; ok++;
    const row = document.createElement("div");
    row.className = "table-row identify-grid ok";
    row.innerHTML = `<span>${count}</span><span>${d.ma_chai}</span>
        <span>${new Date().toLocaleTimeString("vi-VN")}</span>`;
    document.getElementById("rows").prepend(row);
    document.getElementById("count").textContent   = count;
    document.getElementById("stat-ok").textContent = ok;
    showQR(d.ma_chai);
}

function _showReprintPrompt(ma) {
    // Xóa prompt cũ nếu có
    const old = document.getElementById("reprint-prompt");
    if (old) old.remove();

    const div = document.createElement("div");
    div.id = "reprint-prompt";
    div.style.cssText =
        "position:fixed;bottom:80px;right:20px;z-index:4000;" +
        "background:#1e293b;color:#fff;padding:16px 20px;border-radius:8px;" +
        "border:2px solid #dc2626;min-width:280px;box-shadow:0 4px 16px rgba(0,0,0,.4)";
    div.innerHTML = `
        <div style="font-weight:700;color:#fca5a5;margin-bottom:8px">⚠ Laser lỗi — cần in lại</div>
        <div style="font-size:12px;margin-bottom:12px">Mã: <b>${ma}</b></div>
        <div style="display:flex;gap:8px">
            <button onclick="doReprint('${ma}')"
                style="flex:1;background:#16a34a;color:#fff;border:0;border-radius:4px;padding:8px;font-weight:700;cursor:pointer">
                In lại
            </button>
            <button onclick="document.getElementById('reprint-prompt').remove()"
                style="flex:1;background:#374151;color:#fff;border:0;border-radius:4px;padding:8px;cursor:pointer">
                Bỏ qua
            </button>
        </div>`;
    document.body.appendChild(div);
}

window.doReprint = async function(ma) {
    const btn = document.querySelector("#reprint-prompt button");
    if (btn) { btn.disabled = true; btn.textContent = "Đang in..."; }
    try {
        await api(`/api/identify/reprint?ma_chai=${encodeURIComponent(ma)}`, "POST");
        toast(`Đã in lại mã ${ma}`, "ok");
        document.getElementById("reprint-prompt")?.remove();
    } catch (e) {
        toast(`In lại thất bại: ${e.message}`, "err", 8000);
        if (btn) { btn.disabled = false; btn.textContent = "In lại"; }
    }
};

async function showQR(ma) {
    try {
        const d = await api(`/api/qr?data=${encodeURIComponent(ma)}`);
        document.getElementById("qr-box").innerHTML =
            `<img src="${d.png_base64}" alt="QR">
             <div class="qr-large"><div class="qr-num">${ma}</div></div>`;
    } catch {}
}

function setSessionState(running) {
    const pill     = document.getElementById("session-status");
    const btnStart = document.getElementById("btn-start");
    const btnEnd   = document.getElementById("btn-end");
    const btnPrint = document.getElementById("btn-print");
    if (running) {
        pill.textContent  = "⬤ Ca đang chạy";
        pill.className    = "session-pill session-running";
        btnStart.disabled = true;
        btnEnd.disabled   = false;
        btnPrint.disabled = false;
    } else {
        pill.textContent  = "⬤ Chưa bắt đầu";
        pill.className    = "session-pill session-idle";
        btnStart.disabled = false;
        btnEnd.disabled   = true;
        btnPrint.disabled = true;
    }
}

api("/api/sessions/active?che_do=DINH_DANH")
    .then(d => { setSessionState(d.active); if (d.active) syncCounters(); })
    .catch(() => {});

// Bắt đầu ca — disable ngay trước await
document.getElementById("btn-start").onclick = async () => {
    const btn = document.getElementById("btn-start");
    btn.disabled = true;
    try {
        await api("/api/sessions/start", "POST", {
            che_do: "DINH_DANH", production_batch_id: currentBatchId(),
        });
        setSessionState(true);
        syncCounters();
        toast("Đã bắt đầu ca định danh", "ok");
    } catch (e) {
        if (e.message && e.message.includes("ca đang chạy")) {
            toast("⚠ Có ca đang bị treo. Liên hệ quản lý để Phục hồi ca.", "err", 10000);
        } else {
            toast(e.message, "err");
        }
        btn.disabled = false;
    }
};

document.getElementById("btn-end").onclick = async () => {
    const btn = document.getElementById("btn-end");
    btn.disabled = true;
    try {
        const d = await api("/api/sessions/end", "POST", { che_do: "DINH_DANH" });
        setSessionState(false);
        count = ok = err = 0;
        toast(`Kết thúc ca — Đã in: ${d.tong_hop_le}`, "info", 5000);
        loadBatches();
    } catch (e) {
        btn.disabled = false;
        toast(e.message, "err");
    }
};

// Nút in thủ công — disable trong khi đang gửi
document.getElementById("btn-print").onclick = async () => {
    const btn = document.getElementById("btn-print");
    btn.disabled = true;
    try {
        await api("/api/identify/print", "POST", {
            production_batch_id: currentBatchId(),
        });
        // Kết quả đến qua WS
    } catch (e) {
        err++;
        document.getElementById("stat-err").textContent = err;
        toast(e.message, "err", 6000);
    } finally {
        btn.disabled = false;
    }
};

// Dev: giả lập scanner trigger
const _scanBtn1 = document.getElementById("btn-scan1");
const _scanBtn10 = document.getElementById("btn-scan10");
if (_scanBtn1) {
    _scanBtn1.onclick = async () => {
        try { await fetch("/api/identify/test", { method: "POST" }); }
        catch (e) { toast(e.message, "err"); }
    };
}
if (_scanBtn10) {
    _scanBtn10.onclick = async () => {
        toast("Đang giả lập 10 chai...", "info");
        for (let i = 0; i < 10; i++) {
            try { await fetch("/api/identify/test", { method: "POST" }); } catch {}
            await new Promise(r => setTimeout(r, 300));
        }
    };
}
