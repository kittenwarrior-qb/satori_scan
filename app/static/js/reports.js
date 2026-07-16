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
                    <span><button class="btn-detail" onclick="viewBatchDetail('${b.so_lo_san_xuat}')">Xem chi tiết</button></span>
                </div>`).join("")
            : `<div class="table-row" style="padding:16px;color:var(--muted)">Chưa có lô sản xuất</div>`;
    } catch (e) { toast(e.message, "err"); }
}
loadBatches();

async function runSearch(q, field) {
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
}

document.getElementById("btn-search").onclick = () => {
    runSearch(document.getElementById("search-q").value.trim(),
              document.getElementById("search-field").value);
};

// "Xem chi tiết" trên bảng Báo cáo sản xuất — tra cứu lại theo lô SX (mục
// 2.3-#2 tài liệu gốc), tái dùng logic tìm kiếm sẵn có.
window.viewBatchDetail = (soLoSanXuat) => {
    document.getElementById("search-field").value = "lo_sx";
    document.getElementById("search-q").value = soLoSanXuat;
    runSearch(soLoSanXuat, "lo_sx");
    document.getElementById("search-q").closest(".section-block").scrollIntoView({ behavior: "smooth" });
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

// ── Báo cáo theo ca / ngày ──
const CHE_DO_LABEL = { DINH_DANH: "Định danh", PHAN_LOAI: "Phân loại", LOAI_BO: "Loại bỏ" };

function _today() { return new Date().toISOString().slice(0, 10); }
function _firstOfMonth() {
    const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10);
}
document.getElementById("shift-from").value = _firstOfMonth();
document.getElementById("shift-to").value = _today();

function shiftQS() {
    const f = document.getElementById("shift-from").value;
    const t = document.getElementById("shift-to").value;
    const m = document.getElementById("shift-mode").value;
    const p = new URLSearchParams();
    if (f) p.set("from_date", f);
    if (t) p.set("to_date", t);
    if (m) p.set("che_do", m);
    return p.toString();
}

async function loadShifts() {
    try {
        const d = await api(`/api/reports/shifts?${shiftQS()}`);
        document.getElementById("shift-total-ok").textContent = d.totals.tong_hop_le;
        document.getElementById("shift-total-err").textContent = d.totals.tong_loi;
        document.getElementById("shift-total-rate").textContent = d.totals.ty_le_loi;
        document.getElementById("shift-rows").innerHTML = d.rows.length
            ? d.rows.map(r => {
                const rateCls = r.ty_le_loi >= 10 ? "err" : (r.ty_le_loi > 0 ? "warn" : "ok");
                return `<div class="table-row shift-grid">
                    <span>${r.ngay}</span>
                    <span>${CHE_DO_LABEL[r.che_do] || r.che_do}</span>
                    <span>${r.operator || "—"}</span>
                    <span>${r.bat_dau}–${r.ket_thuc}</span>
                    <span>${r.tong_hop_le}</span>
                    <span>${r.tong_loi}</span>
                    <span class="badge ${rateCls}">${r.ty_le_loi}%</span>
                </div>`;
            }).join("")
            : `<div class="table-row" style="padding:16px;color:var(--muted)">Không có ca nào trong khoảng này</div>`;
    } catch (e) { toast(e.message, "err"); }
}
loadShifts();
document.getElementById("btn-shift").onclick = loadShifts;

document.getElementById("btn-export-shift").onclick = async () => {
    try {
        const d = await api(`/api/reports/export/shifts?${shiftQS()}`, "POST");
        toast(`Xuất xong: ${d.filename}`, "ok");
        window.location = `/api/reports/download?filename=${encodeURIComponent(d.filename)}`;
    } catch (e) { toast(e.message, "err"); }
};

// ── Báo cáo theo NGÀY (toàn bộ chai, chạy được trên data cũ CodeIT) ──
document.getElementById("bd-from").value = _firstOfMonth();
document.getElementById("bd-to").value = _today();

function bdQS() {
    const f = document.getElementById("bd-from").value;
    const t = document.getElementById("bd-to").value;
    const p = new URLSearchParams();
    if (f) p.set("from_date", f);
    if (t) p.set("to_date", t);
    return p.toString();
}

async function loadByDate() {
    try {
        const d = await api(`/api/reports/by-date?${bdQS()}`);
        document.getElementById("bd-total").textContent = d.total;
        document.getElementById("bd-ok").textContent = d.ok;
        document.getElementById("bd-err").textContent = d.err;
        document.getElementById("bd-note").textContent = d.total > d.shown
            ? ` — hiển thị ${d.shown} dòng đầu, bấm "Xuất Excel" để lấy đủ ${d.total}`
            : "";
        document.getElementById("bd-rows").innerHTML = d.rows.length
            ? d.rows.map(x => `
                <div class="table-row result-grid">
                    <span>${x.lo_sx}</span>
                    <span>${x.lo_ncc}</span>
                    <span>${x.ma_chai}</span>
                    <span>${x.so_lan_thuc_te}</span>
                    <span>${ttBadge(x.trang_thai)}</span>
                    <span>${x.ngay_san_xuat}</span>
                </div>`).join("")
            : `<div class="table-row" style="padding:16px;color:var(--muted)">Không có chai trong khoảng ngày này</div>`;
    } catch (e) { toast(e.message, "err"); }
}
document.getElementById("btn-bydate").onclick = loadByDate;

document.getElementById("btn-export-bydate").onclick = async () => {
    try {
        toast("Đang xuất... (data lớn có thể mất vài giây)", "info");
        const d = await api(`/api/reports/export/by-date?${bdQS()}`, "POST");
        toast(`Xuất xong: ${d.filename}`, "ok");
        window.location = `/api/reports/download?filename=${encodeURIComponent(d.filename)}`;
    } catch (e) { toast(e.message, "err"); }
};

document.getElementById("btn-backup").onclick = async () => {
    try {
        const d = await api("/api/reports/backup", "POST");
        toast(`Đã sao lưu DB: ${d.filename}`, "ok", 4000);
    } catch (e) { toast(e.message, "err"); }
};

// ── Cập nhật lô NCC (sửa TSD cho cả lô đang lưu hành) ──
let _suppliers = [];

window.closeSupModal = () => document.getElementById("sup-overlay").classList.add("hidden");

document.getElementById("btn-edit-sup").onclick = async () => {
    document.getElementById("sup-overlay").classList.remove("hidden");

    // Còn trong phiên đã xác thực (< 3 phút không thao tác) → bỏ qua bước mật khẩu.
    if (isPasswordUnlocked()) {
        _suppliers = await api("/api/batches/supplier");
        if (!_suppliers.length) { toast("Chưa có lô NCC nào", "err"); return; }
        const sel = document.getElementById("sup-select");
        sel.innerHTML = _suppliers.map(s =>
            `<option value="${s.id}">${s.so_lo_ncc} — ${s.nha_cung_cap}</option>`).join("");
        sel.onchange = fillSupForm;
        fillSupForm();
        document.getElementById("sup-step-pw").classList.add("hidden");
        document.getElementById("sup-step-form").classList.remove("hidden");
        return;
    }

    document.getElementById("sup-step-pw").classList.remove("hidden");
    document.getElementById("sup-step-form").classList.add("hidden");
    document.getElementById("sup-pw").value = "";
    setTimeout(() => document.getElementById("sup-pw").focus(), 100);
};

window.supVerifyPw = async () => {
    const pw = document.getElementById("sup-pw").value;
    try {
        const r = await fetch("/api/verify-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: pw }),
        });
        if (!r.ok) throw new Error("Mật khẩu không đúng");
        unlockPassword();
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

// ── Dashboard tổng quan ──
async function loadDashboard() {
    try {
        const d = await api("/api/reports/dashboard");
        document.getElementById("dk-total-bottles").textContent = d.total_bottles;
        document.getElementById("dk-total-batches").textContent = d.total_batches;
        document.getElementById("dk-rate").textContent = `${d.ty_le_loi}%`;
        document.getElementById("dk-cycle").textContent =
            d.avg_cycle_days == null ? "—" : d.avg_cycle_days;

        drawBarChart(document.getElementById("chart-reuse"),
            d.by_reuse.map(r => ({ label: r.so_lan, value: r.count })));

        drawDonutChart(document.getElementById("chart-reject"),
            d.by_reject_reason.map(r => ({ label: r.reason, value: r.count })));

        document.getElementById("dash-sup-rows").innerHTML = d.by_supplier.length
            ? d.by_supplier.map(s => {
                const rateCls = s.ty_le_loi >= 10 ? "err" : (s.ty_le_loi > 0 ? "warn" : "ok");
                return `<div class="table-row sup-grid">
                    <span>${s.nha_cung_cap}</span>
                    <span>${s.so_lo_ncc}</span>
                    <span>${s.tong}</span>
                    <span>${s.loi}</span>
                    <span class="badge ${rateCls}">${s.ty_le_loi}%</span>
                </div>`;
            }).join("")
            : `<div class="table-row" style="padding:16px;color:var(--muted)">Chưa có dữ liệu</div>`;
    } catch (e) { toast(e.message, "err"); }
}
loadDashboard();

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
