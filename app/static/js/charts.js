// ── Biểu đồ canvas thuần JS (không phụ thuộc CDN — máy kiosk có thể offline) ──

function _cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
}

const CHART_PALETTE = [
    _cssVar("--blue", "#166C94"),
    _cssVar("--orange", "#f7941d"),
    _cssVar("--ok", "#2e9e2e"),
    _cssVar("--err", "#cc2200"),
    _cssVar("--warn", "#cc6600"),
    _cssVar("--satori-teal", "#00adc5"),
];

function _prepCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || canvas.width;
    const h = canvas.clientHeight || canvas.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
}

// data: [{label, value}]
function drawBarChart(canvas, data, opts = {}) {
    const { ctx, w, h } = _prepCanvas(canvas);
    if (!data.length) {
        ctx.fillStyle = _cssVar("--muted", "#888");
        ctx.font = "12px sans-serif";
        ctx.fillText("Chưa có dữ liệu", 10, h / 2);
        return;
    }
    const padL = 30, padB = 26, padT = 10, padR = 10;
    const plotW = w - padL - padR, plotH = h - padT - padB;
    const maxVal = Math.max(1, ...data.map(d => d.value));
    const barW = plotW / data.length;
    const color = opts.color || CHART_PALETTE[0];

    // trục
    ctx.strokeStyle = _cssVar("--border", "#ccc");
    ctx.beginPath();
    ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + plotH); ctx.lineTo(padL + plotW, padT + plotH);
    ctx.stroke();

    ctx.font = "11px sans-serif";
    data.forEach((d, i) => {
        const barH = (d.value / maxVal) * (plotH - 10);
        const x = padL + i * barW + barW * 0.15;
        const bw = barW * 0.7;
        const y = padT + plotH - barH;
        ctx.fillStyle = color;
        ctx.fillRect(x, y, bw, barH);
        ctx.fillStyle = _cssVar("--text", "#222");
        ctx.textAlign = "center";
        ctx.fillText(String(d.value), x + bw / 2, y - 4 < padT ? padT + 10 : y - 4);
        ctx.fillStyle = _cssVar("--muted", "#666");
        ctx.fillText(String(d.label), x + bw / 2, padT + plotH + 16);
    });
    ctx.textAlign = "start";
}

// data: [{label, value}]
function drawDonutChart(canvas, data, opts = {}) {
    const { ctx, w, h } = _prepCanvas(canvas);
    const total = data.reduce((s, d) => s + d.value, 0);
    const cx = w * 0.32, cy = h / 2, rOuter = Math.min(cx, cy) - 6, rInner = rOuter * 0.55;

    if (!total) {
        ctx.fillStyle = _cssVar("--muted", "#888");
        ctx.font = "12px sans-serif";
        ctx.fillText("Chưa có dữ liệu", 10, h / 2);
        return;
    }

    let start = -Math.PI / 2;
    data.forEach((d, i) => {
        const frac = d.value / total;
        const end = start + frac * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, rOuter, start, end);
        ctx.closePath();
        ctx.fillStyle = d.color || CHART_PALETTE[i % CHART_PALETTE.length];
        ctx.fill();
        start = end;
    });
    // lỗ giữa (donut)
    ctx.fillStyle = _cssVar("--panel", "#fff");
    ctx.beginPath();
    ctx.arc(cx, cy, rInner, 0, Math.PI * 2);
    ctx.fill();

    // chú giải
    ctx.font = "11px sans-serif";
    ctx.textAlign = "start";
    let ly = 14;
    const lx = cx + rOuter + 16;
    data.forEach((d, i) => {
        const color = d.color || CHART_PALETTE[i % CHART_PALETTE.length];
        ctx.fillStyle = color;
        ctx.fillRect(lx, ly - 8, 10, 10);
        ctx.fillStyle = _cssVar("--text", "#222");
        const pct = total ? Math.round(d.value / total * 100) : 0;
        ctx.fillText(`${d.label} (${d.value} — ${pct}%)`, lx + 14, ly + 1);
        ly += 18;
    });
}
