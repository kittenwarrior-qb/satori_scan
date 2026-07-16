// ── Chẩn đoán IO-Box tại hiện trường ──
let _diagDefaults = null;

async function loadDiagDefaults() {
    try {
        _diagDefaults = await api("/api/diag/iobox/defaults");
        document.getElementById("d-host-display").textContent =
            `${_diagDefaults.host}:${_diagDefaults.port}`;
        document.getElementById("d-address").value = _diagDefaults.coil_day_loai;
        document.getElementById("d-host").value = _diagDefaults.host;
        document.getElementById("d-port").value = _diagDefaults.port;
        document.getElementById("d-slave").value = _diagDefaults.slave_id;
        document.getElementById("d-address-adv").value = _diagDefaults.coil_day_loai;
    } catch (e) { toast(e.message, "err"); }
}

window.diagFillCoil = (which) => {
    if (!_diagDefaults) return;
    document.getElementById("d-address-adv").value =
        which === "bang_tai" ? _diagDefaults.coil_bang_tai : _diagDefaults.coil_day_loai;
};

// Còn trong phiên đã xác thực (< 3 phút, xem app.js) -> vào thẳng, không hỏi lại mật khẩu.
if (isPasswordUnlocked()) {
    document.getElementById("diag-locked").classList.add("hidden");
    document.getElementById("diag-body").classList.remove("hidden");
    loadDiagDefaults();
}

window.diagUnlock = async () => {
    const pw = document.getElementById("diag-pw").value;
    try {
        const r = await fetch("/api/verify-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: pw }),
        });
        if (!r.ok) throw new Error("Mật khẩu không đúng");
        unlockPassword();
        document.getElementById("diag-locked").classList.add("hidden");
        document.getElementById("diag-body").classList.remove("hidden");
        loadDiagDefaults();
    } catch {
        toast("Mật khẩu không đúng", "err");
        document.getElementById("diag-pw").value = "";
    }
};
document.getElementById("diag-pw").addEventListener("keydown", e => {
    if (e.key === "Enter") diagUnlock();
});

// ── Bước 1: kiểm tra kết nối ──
window.diagProbe = async () => {
    const el = document.getElementById("diag-probe-result");
    el.textContent = "Đang kiểm tra...";
    el.style.color = "var(--muted)";
    try {
        const r = await fetch("/api/diag/iobox/probe", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ host: _diagDefaults.host, port: _diagDefaults.port }),
        });
        const d = await r.json();
        el.textContent = d.message;
        el.style.color = d.ok ? "var(--ok)" : "var(--err)";
        el.style.fontWeight = "700";
    } catch (e) {
        el.textContent = e.message; el.style.color = "var(--err)";
    }
};

// ── Bước 2: dò tìm tự động ──
window.diagAutoScan = async () => {
    const btn = document.getElementById("btn-autoscan");
    const status = document.getElementById("diag-scan-status");
    const results = document.getElementById("diag-scan-results");
    const address = parseInt(document.getElementById("d-address").value, 10);

    btn.disabled = true;
    results.innerHTML = "";
    status.textContent = "⏳ Đang thử lần lượt 4 cách — theo dõi xy-lanh, khoảng 10 giây...";

    try {
        const r = await fetch("/api/diag/iobox/auto-scan", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host: _diagDefaults.host, port: _diagDefaults.port,
                address, pulse_width: _diagDefaults.pulse_width,
            }),
        });
        const d = await r.json();
        status.textContent = "Đã thử xong 4 cách. Kết quả từng lần:";
        results.innerHTML = "";
        (d.results || []).forEach((row, i) => {
            const box = document.createElement("div");
            box.style.cssText = "padding:10px 12px;border-radius:6px;font-size:13px;" +
                (row.ok ? "background:var(--ok-lt);border:1px solid #99ccaa"
                        : "background:var(--panel-bg);border:1px solid var(--border-lt)");
            if (row.ok) {
                box.innerHTML = `<b style="color:var(--ok)">Lần thử ${i + 1}: PLC đồng ý ✅</b>
                    <div style="margin:6px 0">Xy-lanh có VỪA bung ra không?</div>
                    <button class="btn-start" style="width:auto;padding:0 14px;height:32px;margin-right:8px"
                        onclick="diagConfirmCombo(${row.slave}, ${row.multi}, this)">Có, xy-lanh đã bung — Lưu cách này</button>
                    <button class="btn-secondary" style="height:32px" onclick="diagDismissCombo(this)">Không</button>`;
            } else {
                box.innerHTML = `<b style="color:var(--muted)">Lần thử ${i + 1}: PLC không đồng ý</b>
                    <div style="color:var(--muted);font-size:12px;margin-top:3px">${row.message}</div>`;
            }
            results.appendChild(box);
        });
        if (!(d.results || []).some(r => r.ok)) {
            status.textContent += " Không có cách nào được PLC chấp nhận — kiểm tra lại " +
                "địa chỉ ngõ ra ở trên, hoặc khả năng cao là vấn đề phần cứng (dây, áp suất khí).";
        }
    } catch (e) {
        status.textContent = "Lỗi: " + e.message;
    } finally {
        btn.disabled = false;
    }
};

window.diagDismissCombo = (btnEl) => {
    btnEl.disabled = true;
    btnEl.insertAdjacentHTML("afterend",
        '<div style="margin-top:6px;color:var(--muted);font-size:12px">' +
        "Đã ghi nhận — không bung ở cách này, xem các cách khác.</div>");
};

window.diagConfirmCombo = async (slave, multi, btnEl) => {
    try {
        const r = await fetch("/api/diag/save-combo", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slave, multi }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || "Lỗi lưu");
        toast(d.message, "ok", 7000);
        btnEl.disabled = true;
        btnEl.textContent = "Đã lưu ✓";
    } catch (e) { toast(e.message, "err"); }
};

// ── Nâng cao (thủ công) ──
function diagShowResult(ok, message) {
    const el = document.getElementById("diag-result");
    el.style.background = ok ? "var(--ok-lt)" : "var(--err-lt)";
    el.style.borderColor = ok ? "#99ccaa" : "#ffaaaa";
    el.style.color = ok ? "var(--ok)" : "var(--err)";
    el.style.fontWeight = "700";
    el.textContent = message;
}

function diagParams() {
    return {
        host: document.getElementById("d-host").value.trim(),
        port: parseInt(document.getElementById("d-port").value, 10),
        address: parseInt(document.getElementById("d-address-adv").value, 10),
        slave: parseInt(document.getElementById("d-slave").value, 10),
        multi: document.getElementById("d-mode").value === "multi",
    };
}

window.diagWriteCoil = async (value) => {
    const p = diagParams();
    diagShowResult(true, "Đang gửi lệnh...");
    try {
        const r = await fetch("/api/diag/iobox/write-coil", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...p, value }),
        });
        const d = await r.json();
        diagShowResult(d.ok, `[${d.method}] ${d.message}`);
    } catch (e) { diagShowResult(false, e.message); }
};

window.diagPulse = async () => {
    const p = diagParams();
    diagShowResult(true, "Đang gửi xung BẬT → giữ → TẮT...");
    try {
        const r = await fetch("/api/diag/iobox/pulse", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ host: p.host, port: p.port, address: p.address,
                                   slave: p.slave, multi: p.multi,
                                   pulse_width: _diagDefaults ? _diagDefaults.pulse_width : 0.3 }),
        });
        const d = await r.json();
        diagShowResult(d.ok, d.message);
    } catch (e) { diagShowResult(false, e.message); }
};

window.diagSaveEnv = async (key, value) => {
    if (!value) { toast("Chưa có giá trị để lưu", "err"); return; }
    try {
        const r = await fetch("/api/diag/save-env", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, value: String(value) }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || "Lỗi lưu .env");
        toast(d.message, "ok", 6000);
    } catch (e) { toast(e.message, "err"); }
};
