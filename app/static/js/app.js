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

// ── Giữ trạng thái mật khẩu quản lý (3 phút kể từ thao tác cuối) ──
const PW_TTL_MS = 3 * 60 * 1000;
const PW_KEY = "satori_pw_until";

function isPasswordUnlocked() {
    const until = parseInt(sessionStorage.getItem(PW_KEY) || "0", 10);
    return Date.now() < until;
}

function unlockPassword() {
    sessionStorage.setItem(PW_KEY, String(Date.now() + PW_TTL_MS));
}

// Gia hạn khi còn thao tác — nhưng chỉ khi ĐANG unlock (không tự mở khoá từ thao tác thường).
["mousedown", "keydown", "touchstart"].forEach(evt => {
    document.addEventListener(evt, () => { if (isPasswordUnlocked()) unlockPassword(); },
        { passive: true });
});

// ── API helper ──
async function api(path, method = "GET", params = {}) {
    const url = new URL(path, location.origin);
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    const r = await fetch(url, { method });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || "Lỗi server");
    return body;
}

// ── Bàn phím ảo Windows (osk.exe) ──────────────────────────────────────────
let _kbOpen = false;

async function _setKeyboard(open) {
    try {
        await fetch(`/api/keyboard/${open ? "open" : "close"}`, { method: "POST" });
        _kbOpen = open;
        const btn = document.getElementById("kb-toggle");
        if (btn) btn.classList.toggle("active", _kbOpen);
    } catch { /* môi trường không hỗ trợ — im lặng bỏ qua */ }
}

const kbToggleBtn = document.getElementById("kb-toggle");
if (kbToggleBtn) kbToggleBtn.onclick = () => _setKeyboard(!_kbOpen);

// Tự động bật khi chạm vào ô nhập liệu (text/search/password/number) — debounce
// để không gọi liên tục khi Tab qua nhiều ô liền nhau.
const TEXT_INPUT_TYPES = new Set(["text", "search", "password", "number", "tel"]);
let _kbDebounce = null;
document.addEventListener("focusin", e => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (!TEXT_INPUT_TYPES.has(el.type)) return;
    clearTimeout(_kbDebounce);
    _kbDebounce = setTimeout(() => { if (!_kbOpen) _setKeyboard(true); }, 400);
});
