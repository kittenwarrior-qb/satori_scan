// ── Màn hình QUẢN LÝ & BÁO CÁO ──
function ttBadge(v) {
    if (v < 0) return `<span class="badge err">Đã loại (${v})</span>`;
    if (v === 0) return `<span class="badge gray">Mới</span>`;
    return `<span class="badge ok">Dùng ${v} lần</span>`;
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
