// ── Màn hình QUẢN LÝ & BÁO CÁO ──
// Lý do loại theo mã trạng thái âm (khớp app/database/models.py REJECT_*).
const REJECT_REASON = {
    "-1": "Quá hạn tái sử dụng",
    "-2": "Mã lỗi/không đọc được",
    "-3": "Không đạt cảm quan",
};
function ttBadge(v) {
    if (v < 0) return `<span class="badge err">Đã loại — ${REJECT_REASON[v] || "khác"}</span>`;
    if (v === 0) return `<span class="badge gray">Mới</span>`;
    return `<span class="badge ok">Đã dùng ${v} lần</span>`;
}

async function loadBatches() {
    try {
        const rows = await api("/api/reports/batches");
        document.getElementById("batch-rows").innerHTML = rows.length
            ? rows.map(b => `
                <div class="table-row batch-grid">
                    <span>${b.so_lo_san_xuat}</span>
                    <span>${b.ngay_san_xuat}</span>
                    <span>${b.so_luong_chai}</span>
                    <span>${b.ncc_lo}</span>
                    <span>${b.ncc_tsd}</span>
                    <span>${b.ncc_sl}</span>
                </div>`).join("")
            : `<div class="table-row" style="padding:16px;color:var(--muted)">Chưa có lô sản xuất</div>`;
    } catch (e) { toast(e.message, "err"); }
}
loadBatches();

document.getElementById("btn-search").onclick = async () => {
    const q = document.getElementById("search-q").value.trim();
    const field = document.getElementById("search-field").value;
    if (!q) { toast("Nhập từ khoá tìm kiếm", "err"); return; }
    try {
        const d = await api(`/api/reports/search?q=${encodeURIComponent(q)}&field=${field}`);
        document.getElementById("search-count").textContent = d.count;
        document.getElementById("result-rows").innerHTML = d.rows.length
            ? d.rows.map(x => `
                <div class="table-row result-grid">
                    <span>${x.lo_sx}</span>
                    <span>${x.lo_ncc}</span>
                    <span>${x.ma_chai}</span>
                    <span>${x.so_lan_thuc_te}</span>
                    <span>${ttBadge(x.trang_thai)}</span>
                    <span>${x.ngay_san_xuat}</span>
                </div>`).join("")
            : `<div class="table-row" style="padding:16px;color:var(--muted)">Không có kết quả</div>`;
    } catch (e) { toast(e.message, "err"); }
};

document.getElementById("btn-export-prod").onclick = async () => {
    try {
        const d = await api("/api/reports/export/production", "POST");
        toast(`Xuất xong: ${d.filename}`, "ok");
        window.location = `/api/reports/download?filename=${encodeURIComponent(d.filename)}`;
    } catch (e) { toast(e.message, "err"); }
};

document.getElementById("btn-export-batch").onclick = async () => {
    const q = document.getElementById("search-q").value.trim();
    if (!q) { toast("Nhập Lô SX vào ô tìm kiếm trước", "err"); return; }
    try {
        const d = await api(`/api/reports/export/batch?so_lo_san_xuat=${encodeURIComponent(q)}`, "POST");
        toast(`Xuất xong: ${d.filename}`, "ok");
        window.location = `/api/reports/download?filename=${encodeURIComponent(d.filename)}`;
    } catch (e) { toast(e.message, "err"); }
};

// ── Cập nhật lô NCC (sửa TSD cho cả lô đang lưu hành) ──
let _suppliers = [];

window.closeSupModal = () => document.getElementById("sup-overlay").classList.add("hidden");

document.getElementById("btn-edit-sup").onclick = () => {
    document.getElementById("sup-step-pw").classList.remove("hidden");
    document.getElementById("sup-step-form").classList.add("hidden");
    document.getElementById("sup-pw").value = "";
    document.getElementById("sup-overlay").classList.remove("hidden");
    setTimeout(() => document.getElementById("sup-pw").focus(), 100);
};

window.supVerifyPw = async () => {
    const pw = document.getElementById("sup-pw").value;
    try {
        await api(`/api/verify-password?password=${encodeURIComponent(pw)}`, "POST");
        _suppliers = await api("/api/batches/supplier");
        if (!_suppliers.length) { toast("Chưa có lô NCC nào", "err"); return; }
        const sel = document.getElementById("sup-select");
        sel.innerHTML = _suppliers.map(s =>
            `<option value="${s.id}">${s.so_lo_ncc} — ${s.nha_cung_cap}</option>`).join("");
        sel.onchange = fillSupForm;
        fillSupForm();
        document.getElementById("sup-step-pw").classList.add("hidden");
        document.getElementById("sup-step-form").classList.remove("hidden");
    } catch {
        toast("Mật khẩu không đúng", "err");
        document.getElementById("sup-pw").value = "";
    }
};

function fillSupForm() {
    const id = parseInt(document.getElementById("sup-select").value, 10);
    const s = _suppliers.find(x => x.id === id);
    if (!s) return;
    document.getElementById("sup-ncc").value = s.nha_cung_cap || "";
    document.getElementById("sup-lo").value = s.so_lo_ncc || "";
    document.getElementById("sup-sl").value = s.so_luong_chai ?? 0;
    document.getElementById("sup-tsd").value = s.so_lan_tai_su_dung ?? 5;
}

window.supSave = async () => {
    const id = parseInt(document.getElementById("sup-select").value, 10);
    const body = {
        nha_cung_cap: document.getElementById("sup-ncc").value.trim(),
        so_lo_ncc: document.getElementById("sup-lo").value.trim(),
        so_luong_chai: parseInt(document.getElementById("sup-sl").value) || 0,
        so_lan_tai_su_dung: parseInt(document.getElementById("sup-tsd").value) || 5,
    };
    if (!body.nha_cung_cap || !body.so_lo_ncc) { toast("Nhập đủ NCC và số lô", "err"); return; }
    try {
        const r = await fetch(`/api/batches/supplier/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Lỗi cập nhật"); }
        toast(`Đã cập nhật lô ${body.so_lo_ncc} — TSD: ${body.so_lan_tai_su_dung}`, "ok");
        closeSupModal();
        loadBatches();
    } catch (e) { toast(e.message, "err"); }
};
