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
    batches = await api("/api/identify/batches");
    const sel = document.getElementById("batch-select");
    sel.innerHTML = batches.map(b =>
        `<option value="${b.id}">${b.so_lo_san_xuat} — ${b.ngay_san_xuat}</option>`
    ).join("");
    renderInfo();
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
loadBatches().catch(e => toast(e.message, "err"));

// Nhận sự kiện in qua WS
connectWS(d => {
    if (d.event === "error") { toast(d.message || "Lỗi xử lý", "err"); return; }
    if (d.event !== "print") return;
    count++; ok++;
    const row = document.createElement("div");
    row.className = "table-row identify-grid ok";
    row.innerHTML = `<span>${count}</span><span>${d.ma_chai}</span>
        <span>${new Date().toLocaleTimeString("vi-VN")}</span>`;
    document.getElementById("rows").prepend(row);
    document.getElementById("count").textContent = count;
    document.getElementById("stat-ok").textContent = ok;
    showQR(d.ma_chai);
});

async function showQR(ma) {
    try {
        const d = await api(`/api/qr?data=${encodeURIComponent(ma)}`);
        document.getElementById("qr-box").innerHTML =
            `<img src="${d.png_base64}" alt="QR">
             <div class="qr-num">${ma}</div>`;
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

api("/api/sessions/active?che_do=DINH_DANH").then(d => setSessionState(d.active)).catch(() => {});

document.getElementById("btn-start").onclick = async () => {
    try {
        await api("/api/sessions/start", "POST", {
            che_do: "DINH_DANH", production_batch_id: currentBatchId()
        });
        setSessionState(true);
        toast("Đã bắt đầu ca định danh", "ok");
    } catch (e) { toast(e.message, "err"); }
};

document.getElementById("btn-end").onclick = async () => {
    try {
        const d = await api("/api/sessions/end", "POST", { che_do: "DINH_DANH" });
        setSessionState(false);
        toast(`Kết thúc ca — Đã in: ${d.tong_hop_le}`, "info", 4000);
        loadBatches();
    } catch (e) { toast(e.message, "err"); }
};

document.getElementById("btn-print").onclick = async () => {
    try {
        await api("/api/identify/print", "POST", {
            production_batch_id: currentBatchId()
        });
    } catch (e) {
        err++;
        document.getElementById("stat-err").textContent = err;
        toast(e.message, "err");
    }
};

// Dev: giả lập scanner trigger
const _scanBtn1 = document.getElementById("btn-scan1");
const _scanBtn10 = document.getElementById("btn-scan10");
if (_scanBtn1) {
    _scanBtn1.onclick = async () => {
        try {
            await fetch("/api/identify/test", { method: "POST" });
        } catch (e) { toast(e.message, "err"); }
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
