// ── Đồng hồ topbar ──
function tickClock() {
    const el = document.getElementById("clock");
    if (el) el.textContent = new Date().toLocaleTimeString("vi-VN");
}
setInterval(tickClock, 1000);
tickClock();

// ── Toast ──
function toast(msg, type = "info", ms = 3000) {
    const wrap = document.getElementById("toast-wrap");
    if (!wrap) return;
    const t = document.createElement("div");
    t.className = `toast ${type}`;
    t.textContent = msg;
    wrap.appendChild(t);
    setTimeout(() => t.remove(), ms);
}

// ── Device status bar — bảng 3 cột giống CodeIT ──
async function deviceBar(elId) {
    const el = document.getElementById(elId);
    if (!el) return;
    async function refresh() {
        try {
            const r = await fetch("/api/devices/status");
            const d = await r.json();
            const scLabel = d.scanner_count > 1
                ? `Scanner (${d.scanner_count})` : "Scanner";
            el.innerHTML = `
                <table class="dev-table">
                    <thead><tr><th>Thiết Bị</th><th>Kết Nối</th><th>Trạng Thái</th></tr></thead>
                    <tbody>
                        ${devRow(scLabel, d.scanner)}
                        ${devRow("IO-Box", d.iobox)}
                        ${devRow("Laser", d.laser)}
                    </tbody>
                </table>`;
        } catch {
            el.innerHTML = `<div style="padding:8px;color:var(--err);font-weight:600;font-size:12px">Không kết nối được server</div>`;
        }
    }
    function devRow(name, status) {
        const on = status === "OK";
        return `<tr class="${on ? 'dv-ok' : 'dv-err'}">
            <td>${name}</td>
            <td>${on ? "Đã kết nối" : "Mất kết nối"}</td>
            <td>${on ? "Sẵn sàng" : "—"}</td>
        </tr>`;
    }
    refresh();
    setInterval(refresh, 3000);
}

// ── WebSocket auto-reconnect ──
function connectWS(onMessage) {
    function open() {
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = e => onMessage(JSON.parse(e.data));
        ws.onclose = () => setTimeout(open, 2000);
    }
    open();
}

// ── API helper ──
async function api(path, method = "GET", params = {}) {
    const url = new URL(path, location.origin);
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    const r = await fetch(url, { method });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || "Lỗi server");
    return body;
}
