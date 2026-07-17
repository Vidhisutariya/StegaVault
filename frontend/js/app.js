/**
 * StegaVault — Frontend Application (app.js)
 * Pure vanilla JS. Zero dependencies. Connects to the Python stdlib server via fetch().
 */
"use strict";

// ═══════════════════════════════════════════════════════════
// PANEL TITLES
// ═══════════════════════════════════════════════════════════
const TITLES = {
  "p-text-enc": "Hide Text in Image",
  "p-text-dec": "Extract Hidden Text",
  "p-img-enc":  "Hide Image Inside Image",
  "p-img-dec":  "Extract Hidden Image",
  "p-dct-enc":  "Invisible DCT Watermark",
  "p-dct-dec":  "Extract DCT Watermark",
  "p-vis-text": "Visible Text Watermark",
  "p-vis-img":  "Logo / Image Watermark",
  "p-hash":     "Compute Image Hash",
  "p-verify":   "Verify Image Integrity",
  "p-diff":     "Tamper Detection Heatmap",
  "p-lsb":      "LSB Noise Analysis",
  "p-history":  "Operation History",
  "p-algo":     "Algorithm Reference",
};

// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initDropZones();
  initTheme();
  initRanges();
  initCharCounter();
  wireAllButtons();
  checkHealth();
});

// ═══════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════
function initNav() {
  document.querySelectorAll(".nav-item[data-panel]").forEach(item => {
    item.addEventListener("click", e => {
      e.preventDefault();
      switchPanel(item.dataset.panel);
      if (window.innerWidth <= 900)
        document.getElementById("sidebar").classList.remove("open");
    });
  });
  document.getElementById("sbToggle").addEventListener("click", () =>
    document.getElementById("sidebar").classList.toggle("open"));
}

function switchPanel(id) {
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const panel = document.getElementById(id);
  if (panel) panel.classList.add("active");
  const nav = document.querySelector(`[data-panel="${id}"]`);
  if (nav) nav.classList.add("active");
  document.getElementById("topTitle").textContent = TITLES[id] || "";
  if (id === "p-history") loadHistory();
  if (id === "p-algo")    loadAlgorithms();
}

// ═══════════════════════════════════════════════════════════
// THEME
// ═══════════════════════════════════════════════════════════
function initTheme() {
  let dark = true;
  const btn = document.getElementById("themeBtn");
  btn.addEventListener("click", () => {
    dark = !dark;
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    btn.textContent = dark ? "☽" : "☀";
  });
}

// ═══════════════════════════════════════════════════════════
// RANGE INPUTS  →  live display
// ═══════════════════════════════════════════════════════════
function initRanges() {
  const pairs = [
    ["dct-e-str",  "dct-e-str-v",  v => v],
    ["dct-d-str",  "dct-d-str-v",  v => v],
    ["vt-op",      "vt-op-v",      v => v],
    ["vt-fs",      "vt-fs-v",      v => v],
    ["vi-op",      "vi-op-v",      v => (v / 100).toFixed(2)],
    ["vi-sc",      "vi-sc-v",      v => v + "%"],
    ["diff-thr",   "diff-thr-v",   v => v],
  ];
  pairs.forEach(([inp, disp, fmt]) => {
    const i = g(inp), d = g(disp);
    if (!i || !d) return;
    d.textContent = fmt(i.value);
    i.addEventListener("input", () => d.textContent = fmt(i.value));
  });
}

// ═══════════════════════════════════════════════════════════
// CHAR COUNTER + CAPACITY BAR
// ═══════════════════════════════════════════════════════════
function initCharCounter() {
  const ta = g("te-msg"), cc = g("te-cc");
  if (!ta || !cc) return;
  ta.addEventListener("input", () => {
    cc.textContent = ta.value.length;
    updateCapacity();
  });
}

function updateCapacity() {
  const cover = g("fi-te-cover");
  const ta    = g("te-msg");
  if (!cover || !cover.files[0] || !ta) return;
  const img   = new Image();
  img.onload = () => {
    const cap = Math.floor(img.width * img.height * 3 / 8) - 4;
    const pct = Math.min(100, Math.round(ta.value.length / cap * 100));
    const fill = g("te-fill"), label = g("te-pct"), wrap = g("te-cap");
    if (!fill || !label || !wrap) return;
    wrap.style.display = "block";
    fill.style.width   = pct + "%";
    label.textContent  = pct + "%";
    fill.className = "cap-fill" + (pct > 90 ? " danger" : pct > 65 ? " warn" : "");
    URL.revokeObjectURL(img.src);
  };
  img.src = URL.createObjectURL(cover.files[0]);
}

// ═══════════════════════════════════════════════════════════
// DROP ZONES
// ═══════════════════════════════════════════════════════════
function initDropZones() {
  document.querySelectorAll(".dz[data-input]").forEach(zone => {
    const inputId = zone.dataset.input;
    const input   = g(inputId);
    if (!input) return;

    zone.addEventListener("click", () => input.click());
    zone.addEventListener("dragenter", e => { e.preventDefault(); zone.classList.add("over"); });
    zone.addEventListener("dragover",  e => { e.preventDefault(); });
    zone.addEventListener("dragleave", () => zone.classList.remove("over"));
    zone.addEventListener("drop", e => {
      e.preventDefault(); zone.classList.remove("over");
      const file = e.dataTransfer.files[0];
      if (file) assignFile(input, file, zone);
    });
    input.addEventListener("change", () => {
      if (input.files[0]) assignFile(input, input.files[0], zone);
    });
  });
}

function assignFile(input, file, zone) {
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;

  // Update zone label
  const p = zone.querySelector("p");
  if (p) p.textContent = "✓ " + file.name;

  // Show preview
  const zid  = zone.id;
  const iid  = input.id;
  // Derive preview IDs: dz-te-cover → pw-te-cover / pi-te-cover
  const base = iid.replace("fi-", "");
  const pw   = g("pw-" + base);
  const pi   = g("pi-" + base);

  if (pw && pi && file.type.startsWith("image/")) {
    const reader = new FileReader();
    reader.onload = e => { pi.src = e.target.result; pw.style.display = "block"; };
    reader.readAsDataURL(file);
  }

  // Trigger capacity update if text encode cover
  if (iid === "fi-te-cover") updateCapacity();
}

// ═══════════════════════════════════════════════════════════
// API HELPERS
// ═══════════════════════════════════════════════════════════
function showOverlay(msg = "Processing…") {
  g("overlay").classList.add("on");
  g("ov-msg").textContent = msg;
}
function hideOverlay() { g("overlay").classList.remove("on"); }

async function apiPost(url, formData, msg) {
  showOverlay(msg);
  try {
    const res  = await fetch(url, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok || !data.success)
      throw new Error(data.detail || data.message || "Server error " + res.status);
    return data;
  } finally {
    hideOverlay();
  }
}

async function apiGet(url) {
  const res = await fetch(url);
  return res.json();
}

// ═══════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════
function toast(msg, type = "info") {
  const icons = { ok: "✓", err: "✕", info: "ℹ" };
  const el    = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${esc(msg)}`;
  g("toasts").appendChild(el);
  setTimeout(() => {
    el.style.animation = "toastOut .3s ease forwards";
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ═══════════════════════════════════════════════════════════
// METADATA RENDERER
// ═══════════════════════════════════════════════════════════
function renderMeta(containerId, meta) {
  const el = g(containerId);
  if (!el || !meta) return;
  const skip = new Set(["operation"]);
  el.innerHTML = Object.entries(meta)
    .filter(([k]) => !skip.has(k))
    .map(([k, v]) =>
      `<div><div class="mk">${esc(k.replace(/_/g, " "))}</div>` +
      `<div class="mv">${esc(String(v))}</div></div>`
    ).join("");
}

// ═══════════════════════════════════════════════════════════
// DOWNLOAD HELPER
// ═══════════════════════════════════════════════════════════
function download(dataUri, filename) {
  const a = document.createElement("a");
  a.href = dataUri; a.download = filename; a.click();
}

// ═══════════════════════════════════════════════════════════
// UTILITY
// ═══════════════════════════════════════════════════════════
const g   = id => document.getElementById(id);
const esc = s  => String(s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

function getFile(id) {
  const el = g(id);
  return el && el.files[0] ? el.files[0] : null;
}

function requireFile(id, label) {
  const f = getFile(id);
  if (!f) { toast(`Please upload ${label}.`, "err"); return null; }
  return f;
}

function fd(...pairs) {
  // pairs: [fieldName, value] — value can be File or string
  const form = new FormData();
  for (let i = 0; i < pairs.length; i += 2)
    if (pairs[i+1] !== null && pairs[i+1] !== undefined)
      form.append(pairs[i], pairs[i+1]);
  return form;
}

function togglePwd(id) {
  const el = g(id);
  if (el) el.type = el.type === "password" ? "text" : "password";
}

function previewSrc(id) {
  const el = g(id);
  return el ? el.src : "";
}

// ═══════════════════════════════════════════════════════════
// HEALTH CHECK
// ═══════════════════════════════════════════════════════════
async function checkHealth() {
  try {
    const d = await apiGet("/api/health");
    const b = g("statusBadge");
    if (d.status === "ok") { b.textContent = "● Online"; b.className = "badge badge-g"; }
  } catch {
    const b = g("statusBadge");
    b.textContent = "● Offline"; b.style.color = "var(--danger)";
  }
}

// ═══════════════════════════════════════════════════════════
// WIRE ALL BUTTONS
// ═══════════════════════════════════════════════════════════
function wireAllButtons() {

  // ── TEXT ENCODE ────────────────────────────────────────────────────────────
  g("btn-te").addEventListener("click", async () => {
    const cover = requireFile("fi-te-cover", "a cover image"); if (!cover) return;
    const text  = (g("te-msg").value || "").trim();
    if (!text) { toast("Please enter a secret message.", "err"); return; }
    const pwd   = g("te-pwd").value;
    try {
      const data = await apiPost("/api/stego/encode-text",
        fd("cover_image", cover, "secret_text", text, "password", pwd),
        "Encoding text with LSB…");

      // Workflow steps
      ["te-s1","te-s2","te-s3"].forEach((id,i) =>
        g(id) && (g(id).className = "step" + (i===2?" active":"")));

      const res = g("res-te"); res.style.display = "block";
      g("ri-te-before").src = previewSrc("pi-te-cover");
      g("ri-te-after").src  = data.stego_image;
      g("dl-te").onclick = () => download(data.stego_image,
        "stego_" + cover.name.replace(/\.[^/.]+$/,"") + ".png");
      renderMeta("meta-te", data.metadata);
      toast("Text hidden successfully!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── TEXT DECODE ─────────────────────────────────────────────────────────────
  g("btn-td").addEventListener("click", async () => {
    const stego = requireFile("fi-td", "a stego image"); if (!stego) return;
    const pwd   = g("td-pwd").value;
    try {
      const data = await apiPost("/api/stego/decode-text",
        fd("stego_image", stego, "password", pwd),
        "Extracting hidden text…");
      const res = g("res-td"); res.style.display = "block";
      g("td-out").textContent = data.extracted_text;
      g("copy-td").onclick = () => {
        navigator.clipboard.writeText(data.extracted_text);
        toast("Copied to clipboard!", "ok");
      };
      renderMeta("meta-td", data.metadata);
      toast("Text extracted successfully!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── IMAGE ENCODE ────────────────────────────────────────────────────────────
  g("btn-ie").addEventListener("click", async () => {
    const cover  = requireFile("fi-ie-cover",  "a cover image");  if (!cover)  return;
    const secret = requireFile("fi-ie-secret", "a secret image"); if (!secret) return;
    const pwd    = g("ie-pwd").value;
    try {
      const data = await apiPost("/api/stego/encode-image",
        fd("cover_image", cover, "secret_image", secret, "password", pwd),
        "Hiding image with LSB…");
      const res = g("res-ie"); res.style.display = "block";
      g("ri-ie-cover").src  = previewSrc("pi-ie-cover");
      g("ri-ie-secret").src = previewSrc("pi-ie-secret");
      g("ri-ie-stego").src  = data.stego_image;
      g("dl-ie").onclick = () => download(data.stego_image,
        "stego_" + cover.name.replace(/\.[^/.]+$/,"") + ".png");
      renderMeta("meta-ie", data.metadata);
      toast("Image hidden successfully!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── IMAGE DECODE ────────────────────────────────────────────────────────────
  g("btn-id").addEventListener("click", async () => {
    const stego = requireFile("fi-id", "a stego image"); if (!stego) return;
    const pwd   = g("id-pwd").value;
    try {
      const data = await apiPost("/api/stego/decode-image",
        fd("stego_image", stego, "password", pwd),
        "Extracting hidden image…");
      const res = g("res-id"); res.style.display = "block";
      g("ri-id-out").src = data.extracted_image;
      g("dl-id").onclick = () => download(data.extracted_image, "extracted_secret.png");
      renderMeta("meta-id", data.metadata);
      toast("Image extracted!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── DCT EMBED ───────────────────────────────────────────────────────────────
  g("btn-dct-e").addEventListener("click", async () => {
    const img  = requireFile("fi-dct-e", "an image"); if (!img) return;
    const text = (g("dct-e-txt").value || "").trim();
    if (!text) { toast("Please enter watermark text.", "err"); return; }
    const str  = g("dct-e-str").value;
    try {
      const data = await apiPost("/api/watermark/embed-dct",
        fd("image", img, "watermark_text", text, "strength", str),
        "Embedding DCT watermark…");
      const res = g("res-dct-e"); res.style.display = "block";
      g("ri-dct-e-bef").src = previewSrc("pi-dct-e");
      g("ri-dct-e-aft").src = data.watermarked_image;
      g("dl-dct-e").onclick = () => download(data.watermarked_image, "dct_watermarked.png");
      renderMeta("meta-dct-e", data.metadata);
      toast("DCT watermark embedded!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── DCT EXTRACT ─────────────────────────────────────────────────────────────
  g("btn-dct-d").addEventListener("click", async () => {
    const img = requireFile("fi-dct-d", "a watermarked image"); if (!img) return;
    const str = g("dct-d-str").value;
    try {
      const data = await apiPost("/api/watermark/extract-dct",
        fd("image", img, "strength", str),
        "Extracting DCT watermark…");
      const res = g("res-dct-d"); res.style.display = "block";
      g("dct-d-out").textContent = data.watermark_text || "(empty)";
      renderMeta("meta-dct-d", data.metadata);
      toast("Watermark extracted: " + data.watermark_text, "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── VISIBLE TEXT WATERMARK ──────────────────────────────────────────────────
  g("btn-vt").addEventListener("click", async () => {
    const img  = requireFile("fi-vt", "an image"); if (!img) return;
    const text = (g("vt-txt").value || "").trim();
    if (!text) { toast("Please enter watermark text.", "err"); return; }
    try {
      const data = await apiPost("/api/watermark/visible-text",
        fd("image", img,
           "text", text,
           "opacity",   g("vt-op").value,
           "position",  g("vt-pos").value,
           "font_size", g("vt-fs").value),
        "Adding visible watermark…");
      const res = g("res-vt"); res.style.display = "block";
      g("ri-vt-bef").src = previewSrc("pi-vt");
      g("ri-vt-aft").src = data.watermarked_image;
      g("dl-vt").onclick = () => download(data.watermarked_image, "visible_watermarked.png");
      renderMeta("meta-vt", data.metadata);
      toast("Visible watermark applied!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── VISIBLE IMAGE WATERMARK ─────────────────────────────────────────────────
  g("btn-vi").addEventListener("click", async () => {
    const base = requireFile("fi-vi-base", "a base image"); if (!base) return;
    const logo = requireFile("fi-vi-logo", "a logo image"); if (!logo) return;
    const op   = (parseInt(g("vi-op").value) / 100).toFixed(2);
    const sc   = (parseInt(g("vi-sc").value) / 100).toFixed(2);
    try {
      const data = await apiPost("/api/watermark/visible-image",
        fd("image", base,
           "watermark_image", logo,
           "opacity",  op,
           "position", g("vi-pos").value,
           "scale",    sc),
        "Overlaying logo watermark…");
      const res = g("res-vi"); res.style.display = "block";
      g("ri-vi-bef").src = previewSrc("pi-vi-base");
      g("ri-vi-aft").src = data.watermarked_image;
      g("dl-vi").onclick = () => download(data.watermarked_image, "logo_watermarked.png");
      renderMeta("meta-vi", data.metadata);
      toast("Logo watermark applied!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── GET HASH ────────────────────────────────────────────────────────────────
  g("btn-hash").addEventListener("click", async () => {
    const img = requireFile("fi-hash", "an image"); if (!img) return;
    try {
      const data = await apiPost("/api/tamper/get-hash",
        fd("image", img), "Computing SHA-256…");
      g("hash-res-card").style.display = "block";
      g("hash-val").textContent = data.sha256_hash;
      g("copy-hash").onclick = () => {
        navigator.clipboard.writeText(data.sha256_hash);
        g("verify-hash-in").value = data.sha256_hash; // pre-fill verify panel
        toast("Hash copied + pre-filled in Verify panel!", "ok");
      };
      toast("Hash computed!", "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── VERIFY HASH ─────────────────────────────────────────────────────────────
  g("btn-verify").addEventListener("click", async () => {
    const img  = requireFile("fi-verify", "an image"); if (!img) return;
    const hash = (g("verify-hash-in").value || "").trim();
    if (!hash)        { toast("Please paste the expected hash.", "err"); return; }
    if (hash.length !== 64) { toast("Hash must be exactly 64 hex characters.", "err"); return; }
    try {
      const data = await apiPost("/api/tamper/verify-hash",
        fd("image", img, "expected_hash", hash),
        "Verifying integrity…");
      const res = g("res-verify"); res.style.display = "block";
      const ico = g("verify-icon"), vrd = g("verify-verdict");
      if (data.match) {
        ico.className = "ri-icon ok"; ico.textContent = "✓";
        vrd.textContent = "INTACT — Image has not been modified.";
        toast("Image is intact!", "ok");
      } else {
        ico.className = "ri-icon err"; ico.textContent = "✕";
        vrd.textContent = "TAMPERED — Image does not match the stored hash!";
        toast("Tampering detected!", "err");
      }
      const hg = g("verify-hash-grid");
      hg.innerHTML =
        `<div class="card"><div class="clabel">Expected Hash</div>` +
        `<div class="hash-box">${esc(data.hash_original)}</div></div>` +
        `<div class="card"><div class="clabel">Current Hash</div>` +
        `<div class="hash-box" style="${data.match ? "" : "border-color:var(--danger);color:var(--danger)"}">${esc(data.hash_current)}</div></div>`;
    } catch(e) { toast(e.message, "err"); }
  });

  // ── DIFF HEATMAP ─────────────────────────────────────────────────────────────
  g("btn-diff").addEventListener("click", async () => {
    const orig = requireFile("fi-diff-o", "the original image");  if (!orig) return;
    const susp = requireFile("fi-diff-s", "the suspect image");   if (!susp) return;
    const thr  = g("diff-thr").value;
    try {
      const data = await apiPost("/api/tamper/diff-heatmap",
        fd("original_image", orig, "suspect_image", susp, "threshold", thr),
        "Analysing pixel differences…");
      const a   = data.analysis;
      const res = g("res-diff"); res.style.display = "block";
      const ico = g("diff-icon"), vrd = g("diff-verdict");
      if (a.tampered) {
        ico.className = "ri-icon err"; ico.textContent = "✕";
        vrd.textContent =
          `TAMPERED — ${a.tampered_pixels.toLocaleString()} pixels altered (${a.tamper_ratio_pct}%)`;
        toast(`Tampering in ${a.tamper_ratio_pct}% of pixels!`, "err");
      } else {
        ico.className = "ri-icon ok"; ico.textContent = "✓";
        vrd.textContent = "CLEAN — No significant differences detected.";
        toast("Images appear identical.", "ok");
      }
      g("ri-diff-o").src = previewSrc("pi-diff-o");
      g("ri-diff-s").src = previewSrc("pi-diff-s");
      g("ri-diff-h").src = data.heatmap_image;
      g("dl-diff").onclick = () => download(data.heatmap_image, "tamper_heatmap.png");
      renderMeta("meta-diff", a);
    } catch(e) { toast(e.message, "err"); }
  });

  // ── LSB NOISE ────────────────────────────────────────────────────────────────
  g("btn-lsb").addEventListener("click", async () => {
    const img = requireFile("fi-lsb", "an image"); if (!img) return;
    try {
      const data = await apiPost("/api/tamper/lsb-noise",
        fd("image", img), "Analysing LSB distribution…");
      g("lsb-res-card").style.display = "block";
      const ratio = data.lsb_ones_ratio;
      g("lsb-ratio").textContent = (ratio * 100).toFixed(3) + "%";
      const fill = g("lsb-fill");
      fill.style.width      = (ratio * 100) + "%";
      fill.style.background = data.suspicious ? "var(--warn)" : "var(--accent)";
      const vrd = g("lsb-verdict");
      vrd.className   = "verdict mt " + (data.suspicious ? "v-suspect" : "v-clean");
      vrd.textContent = data.suspicious
        ? "⚠ Suspicious — LSB distribution may indicate hidden data."
        : "✓ Natural — LSB distribution looks normal.";
      toast(data.note, data.suspicious ? "info" : "ok");
    } catch(e) { toast(e.message, "err"); }
  });

  // ── HISTORY ──────────────────────────────────────────────────────────────────
  g("btn-hist-refresh").addEventListener("click", loadHistory);
  g("btn-hist-clear").addEventListener("click", async () => {
    await fetch("/api/history", { method: "DELETE" });
    toast("History cleared.", "info");
    loadHistory();
  });
}

// ═══════════════════════════════════════════════════════════
// HISTORY PANEL
// ═══════════════════════════════════════════════════════════
async function loadHistory() {
  const list = g("hist-list");
  try {
    const data = await apiGet("/api/history");
    if (!data.history || data.history.length === 0) {
      list.innerHTML = '<div class="empty">No operations yet.</div>';
      return;
    }
    list.innerHTML = data.history.map(e =>
      `<div class="hist-entry">
        <div class="hist-dot ${e.status}"></div>
        <div>
          <div class="hist-op">${esc(e.operation.replace(/_/g," ").toUpperCase())}</div>
          <div class="hist-file">${e.file_name ? esc(e.file_name) : "—"} · #${esc(e.id)}</div>
        </div>
        <div class="hist-time">${new Date(e.timestamp).toLocaleTimeString()}</div>
      </div>`
    ).join("");
  } catch {
    list.innerHTML = '<div class="empty">Could not load history. Is the server running?</div>';
  }
}

// ═══════════════════════════════════════════════════════════
// ALGORITHMS PANEL
// ═══════════════════════════════════════════════════════════
async function loadAlgorithms() {
  const grid = g("algo-grid");
  if (grid.querySelector(".algo-card")) return; // already loaded
  try {
    const data  = await apiGet("/api/algorithms");
    const algos = data.algorithms || {};
    grid.innerHTML = Object.values(algos).map(a =>
      `<div class="algo-card">
        <div class="algo-name">${esc(a.name)}</div>
        <div class="algo-type">${esc(a.type)}</div>
        <div class="algo-desc">${esc(a.description)}</div>
        <div class="algo-pc">
          <div class="pros">
            <div class="algo-pt">Pros</div>
            <ul class="algo-ul">${(a.pros||[]).map(p=>`<li>${esc(p)}</li>`).join("")}</ul>
          </div>
          <div class="cons">
            <div class="algo-pt">Cons</div>
            <ul class="algo-ul">${(a.cons||[]).map(c=>`<li>${esc(c)}</li>`).join("")}</ul>
          </div>
        </div>
        <div class="info" style="margin-top:12px;font-size:11px"><strong>Used for:</strong> ${esc(a.use)}</div>
      </div>`
    ).join("");
  } catch {
    grid.innerHTML = '<div class="empty">Could not load algorithm data.</div>';
  }
}
