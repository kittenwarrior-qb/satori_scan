// ── Dialog Quản lý thông tin sản xuất ──────────────────────────────────────
// Dùng chung cho màn Định danh và Phân loại.
// Gọi: openBatchModal(onSaved) — callback nhận batch mới khi lưu thành công.

(function () {
    const HTML = `
<div id="bm-overlay" class="overlay hidden" onclick="if(event.target===this)closeBatchModal()">
  <div class="modal" style="min-width:480px;max-width:540px" onclick="event.stopPropagation()">
    <div class="modal-header">Quản lý thông tin sản xuất</div>
    <div class="modal-body">

      <!-- Bước 1: Nhập mật khẩu -->
      <div id="bm-step-pw">
        <div class="modal-row">
          <label>Mật khẩu quản lý</label>
          <input type="password" id="bm-pw" placeholder="Nhập mật khẩu..." autocomplete="off">
        </div>
        <div class="modal-actions">
          <button class="btn-confirm" onclick="bmVerifyPw()">Xác nhận</button>
          <button class="btn-cancel" onclick="closeBatchModal()">Hủy</button>
        </div>
      </div>

      <!-- Bước 2: Form thông tin -->
      <div id="bm-step-form" class="hidden">
        <div style="font-size:12px;font-weight:700;color:var(--blue);text-transform:uppercase;border-bottom:1px solid var(--border);padding-bottom:4px;margin-bottom:10px;">
          Thông tin nhà cung cấp
        </div>
        <div class="modal-row">
          <label>Nhà cung cấp</label>
          <input id="bm-ncc" placeholder="Ngọc Nghĩa...">
        </div>
        <div class="modal-row">
          <label>Số lô NCC</label>
          <input id="bm-lo-ncc" placeholder="NN2001008Q1">
        </div>
        <div class="modal-row">
          <label>Số lượng chai</label>
          <input id="bm-sl" type="number" min="1" placeholder="700">
        </div>
        <div class="modal-row">
          <label>Số lần tái sử dụng cho phép</label>
          <input id="bm-tsd" type="number" min="1" max="20" placeholder="5">
        </div>

        <div style="font-size:12px;font-weight:700;color:var(--blue);text-transform:uppercase;border-bottom:1px solid var(--border);padding-bottom:4px;margin:14px 0 10px;">
          Thông tin sản xuất
        </div>
        <div class="modal-row">
          <label>Số lô sản xuất</label>
          <input id="bm-lo-sx" placeholder="STR200108P1">
        </div>
        <div class="modal-row">
          <label>Ngày sản xuất</label>
          <input id="bm-ngay-sx" type="date">
        </div>

        <!-- Chọn hoặc tạo mới lô NCC -->
        <div class="modal-row" style="margin-top:10px">
          <label>Hoặc chọn lô NCC đã có</label>
          <select id="bm-sup-select">
            <option value="">— Tạo lô NCC mới (điền thông tin trên) —</option>
          </select>
        </div>

        <div class="modal-actions">
          <button class="btn-confirm" onclick="bmSave()">Lưu</button>
          <button class="btn-cancel" onclick="closeBatchModal()">Hủy</button>
        </div>
      </div>

    </div>
  </div>
</div>`;

    // Inject HTML khi script load
    document.addEventListener("DOMContentLoaded", function () {
        const div = document.createElement("div");
        div.innerHTML = HTML;
        document.body.appendChild(div.firstElementChild);
        // set ngay-sx default = hôm nay
        const today = new Date().toISOString().slice(0, 10);
        const el = document.getElementById("bm-ngay-sx");
        if (el) el.value = today;
    });

    let _onSaved = null;

    window.openBatchModal = function (onSaved) {
        _onSaved = onSaved || null;
        document.getElementById("bm-overlay").classList.remove("hidden");

        // Còn trong phiên đã xác thực (< 3 phút không thao tác) → bỏ qua bước mật khẩu.
        if (isPasswordUnlocked()) {
            document.getElementById("bm-step-pw").classList.add("hidden");
            bmLoadSuppliers().then(() => {
                document.getElementById("bm-step-form").classList.remove("hidden");
            });
            return;
        }

        // Reset về bước nhập pw
        document.getElementById("bm-step-pw").classList.remove("hidden");
        document.getElementById("bm-step-form").classList.add("hidden");
        document.getElementById("bm-pw").value = "";
        setTimeout(() => document.getElementById("bm-pw").focus(), 100);
    };

    window.closeBatchModal = function () {
        document.getElementById("bm-overlay").classList.add("hidden");
    };

    window.bmVerifyPw = async function () {
        const pw = document.getElementById("bm-pw").value;
        try {
            const r = await fetch("/api/verify-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password: pw }),
            });
            if (!r.ok) throw new Error("Mật khẩu không đúng");
            unlockPassword();
            // Mật khẩu đúng → load danh sách lô NCC và hiện form
            document.getElementById("bm-step-pw").classList.add("hidden");
            await bmLoadSuppliers();
            document.getElementById("bm-step-form").classList.remove("hidden");
        } catch {
            toast("Mật khẩu không đúng", "err");
            document.getElementById("bm-pw").value = "";
            document.getElementById("bm-pw").focus();
        }
    };

    async function bmLoadSuppliers() {
        try {
            const rows = await api("/api/batches/supplier");
            const sel = document.getElementById("bm-sup-select");
            sel.innerHTML = '<option value="">— Tạo lô NCC mới (điền thông tin trên) —</option>';
            rows.forEach(r => {
                const opt = document.createElement("option");
                opt.value = r.id;
                opt.textContent = `${r.so_lo_ncc} | ${r.nha_cung_cap} | TSD: ${r.so_lan_tai_su_dung}`;
                sel.appendChild(opt);
            });
        } catch { /* ignore */ }
    }

    window.bmSave = async function () {
        const loSX = document.getElementById("bm-lo-sx").value.trim();
        const ngaySX = document.getElementById("bm-ngay-sx").value;
        const supSel = document.getElementById("bm-sup-select").value;

        if (!loSX) { toast("Nhập số lô sản xuất", "err"); return; }
        if (!ngaySX) { toast("Chọn ngày sản xuất", "err"); return; }

        try {
            let supId;

            if (supSel) {
                // Chọn lô NCC có sẵn
                supId = parseInt(supSel);
            } else {
                // Tạo lô NCC mới
                const ncc = document.getElementById("bm-ncc").value.trim();
                const loNCC = document.getElementById("bm-lo-ncc").value.trim();
                const sl = parseInt(document.getElementById("bm-sl").value) || 0;
                const tsd = parseInt(document.getElementById("bm-tsd").value) || 5;
                if (!ncc || !loNCC) { toast("Nhập đủ thông tin NCC", "err"); return; }

                const r = await fetch("/api/batches/supplier", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        nha_cung_cap: ncc,
                        so_lo_ncc: loNCC,
                        so_luong_chai: sl,
                        so_lan_tai_su_dung: tsd,
                    }),
                });
                if (!r.ok) {
                    const err = await r.json();
                    throw new Error(err.detail || "Lỗi tạo lô NCC");
                }
                const supData = await r.json();
                supId = supData.id;
            }

            // Tạo lô SX
            const r2 = await fetch("/api/batches/production", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    supplier_batch_id: supId,
                    so_lo_san_xuat: loSX,
                    ngay_san_xuat: ngaySX,
                }),
            });
            if (!r2.ok) {
                const err = await r2.json();
                throw new Error(err.detail || "Lỗi tạo lô SX");
            }
            const batch = await r2.json();

            toast(`Đã tạo lô: ${loSX}`, "ok");
            closeBatchModal();
            if (_onSaved) _onSaved(batch);
        } catch (e) {
            toast(e.message, "err");
        }
    };

    // Enter trong ô password = xác nhận
    document.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            const overlay = document.getElementById("bm-overlay");
            if (!overlay || overlay.classList.contains("hidden")) return;
            if (!document.getElementById("bm-step-pw").classList.contains("hidden")) {
                bmVerifyPw();
            }
        }
    });
})();
