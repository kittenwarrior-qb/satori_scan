// ── Màn hình LOẠI BỎ ──
let count = 0;
deviceBar("device-bar");

const input = document.getElementById("ma-input");

// Keypad cảm ứng
document.querySelectorAll(".keypad button").forEach(btn => {
    btn.onclick = () => {
        const k = btn.dataset.k;
        if (k === "back")  input.value = input.value.slice(0, -1);
        else if (k === "clear") input.value = "";
        else input.value += k;
        input.focus();
    };
});

async function submit() {
    const ma = input.value.trim();
    if (!ma) return;
    try {
        const d = await api("/api/reject", "POST", { ma_chai: ma });
        count++;
        const isRejected = d.ket_qua === "REJECTED";
        const row = document.createElement("div");
        row.className = `table-row reject-grid ${isRejected ? "warn" : "err"}`;
        row.innerHTML = `
            <span>${count}</span>
            <span>${ma}</span>
            <span>${new Date().toLocaleTimeString("vi-VN")}</span>
            <span class="badge ${isRejected ? "warn" : "err"}">${isRejected ? "Đã loại" : "Không tồn tại"}</span>`;
        document.getElementById("rows").prepend(row);
        document.getElementById("count").textContent = count;
        toast(isRejected ? `Đã loại: ${ma}` : `Không tìm thấy: ${ma}`, isRejected ? "ok" : "err");
        input.value = "";
        input.focus();
    } catch (e) { toast(e.message, "err"); }
}

document.getElementById("btn-ok").onclick = submit;
input.addEventListener("keydown", e => { if (e.key === "Enter") submit(); });
