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

// ── Banner mất kết nối WS (persistent, không tự tắt) ──
function _showWsBanner(show) {
    let banner = document.getElementById("ws-banner");
    if (!banner) {
        banner = document.createElement("div");
        banner.id = "ws-banner";
        banner.style.cssText =
            "position:fixed;top:0;left:0;right:0;z-index:9999;" +
            "background:#dc2626;color:#fff;text-align:center;" +
            "padding:10px 16px;font-weight:700;font-size:14px;display:none";
        banner.textContent = "⚠ Mất kết nối server — đang kết nối lại...";
        document.body.prepend(banner);
    }
    banner.style.display = show ? "block" : "none";
}

// ── Device status bar ──
const _prevDevStatus = {};
async function deviceBar(elId) {
    const el = document.getElementById(elId);
    if (!el) return;

    function devRow(key, name, status) {
        const on = status === "OK";
        // Phát hiện chuyển từ OK → OFFLINE: alert ngay
        if (_prevDevStatus[key] === "OK" && !on) {
            const label = { scanner: "Máy scan", iobox: "IO-Box (băng tải)", laser: "Máy laser" }[key] || key;
            toast(`⚠ ${label} mất kết nối — dừng kiểm tra ngay!`, "err", 12000);
        }
        _prevDevStatus[key] = status;
        return `<tr class="${on ? "dv-ok" : "dv-err"}">
            <td>${name}</td>
            <td>${on ? "Đã kết nối" : "Mất kết nối"}</td>
            <td>${on ? "Sẵn sàng" : "Gọi kỹ thuật"}</td>
        </tr>`;
    }

    async function refresh() {
        try {
            const r = await fetch("/api/devices/status");
            const d = await r.json();
            const scLabel = d.scanner_count > 1 ? `Scanner (${d.scanner_count})` : "Scanner";
            el.innerHTML = `
                <table class="dev-table">
                    <thead><tr><th>Thiết Bị</th><th>Kết Nối</th><th>Trạng Thái</th></tr></thead>
                    <tbody>
                        ${devRow("scanner", scLabel, d.scanner)}
                        ${devRow("iobox", "IO-Box", d.iobox)}
                        ${devRow("laser", "Laser", d.laser)}
                    </tbody>
                </table>`;
        } catch {
            el.innerHTML = `<div style="padding:8px;color:var(--err);font-weight:600;font-size:12px">Không kết nối được server</div>`;
        }
    }
    refresh();
    setInterval(refresh, 3000);
}

// ── WebSocket auto-reconnect + heartbeat watchdog ──
function connectWS(onMessage, onOpen) {
    let lastMsg = Date.now();
    let ws;

    function open() {
        ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onopen = () => {
            _showWsBanner(false);
            lastMsg = Date.now();
            if (onOpen) onOpen();
        };
        ws.onmessage = e => {
            lastMsg = Date.now();
            const d = JSON.parse(e.data);
            if (d.event === "heartbeat") return;  // chỉ reset timer
            // Device change từ server monitor
            if (d.event === "device_change") {
                if (d.status === "OFFLINE") {
                    const label = { scanner: "Máy scan", iobox: "IO-Box (băng tải)", laser: "Máy laser" }[d.device] || d.device;
                    toast(`⚠ ${label} mất kết nối — dừng kiểm tra ngay!`, "err", 12000);
                }
                return;
            }
            onMessage(d);
        };
        ws.onerror = () => _showWsBanner(true);
        ws.onclose = () => {
            _showWsBanner(true);
            setTimeout(open, 2000);
        };
    }

    // Watchdog: nếu không nhận bất kỳ tin nào trong 20s → đóng để kích reconnect
    setInterval(() => {
        if (Date.now() - lastMsg > 20000 && ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    }, 5000);

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
