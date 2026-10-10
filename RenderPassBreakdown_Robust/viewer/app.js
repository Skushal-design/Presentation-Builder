const allPasses = window.PASSES || [];
const passes = allPasses.filter(p => !p.hidden && !p.hide);

const SETTINGS = window.SETTINGS || {};

const PASS_ACCENTS = {
  "Lighting": "#e8b84a",
  "Diffuse": "#c4a574",
  "Global Illumination": "#5b9fd4",
  "Ambient Occlusion": "#8a9099",
  "Reflection": "#4ecdc4",
  "Refraction": "#7fdbda",
  "Specular": "#f0e6a0",
  "SSS": "#e89a9a",
  "Self Illumination": "#ff9f43",
  "Caustics": "#a29bfe",
  "Shadow": "#636e72",
  "Atmosphere": "#74b9ff",
  "Background": "#6c7a89",
  "Normals": "#55efc4",
  "Z-Depth": "#b2bec3",
  "Cryptomatte": "#fd79a8",
  "Final RGB / Beauty": "#d6aa63",
  "Sheen": "#fdcb6e",
  "Coat": "#e17055",
  "Bloom": "#ffeaa7",
  "Metallic": "#b2bec3",
};
function accentFor(name) {
  if (PASS_ACCENTS[name]) return PASS_ACCENTS[name];
  // hash fallback
  let h = 0;
  for (let i = 0; i < (name||"").length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  const hue = Math.abs(h) % 360;
  return `hsl(${hue} 55% 55%)`;
}
let index = 0, playing = true, timer = null, animationId = null, token = 0;

const $ = id => document.getElementById(id);
const layerOver = $("layerOver");
const imgBase = $("imgBase");
const stage = $("stage");
let committedStack = [];
const imgOver = $("imgOver");
const wipeEdge = $("wipeEdge");

function fitStageToImage(img) {
  const el = img || imgBase;
  const w = el && (el.naturalWidth || el.width);
  const h = el && (el.naturalHeight || el.height);
  if (w && h) {
    document.documentElement.style.setProperty("--img-aspect", (w / h).toFixed(6));
  }
}

function applyImageFit() {
  // contain (default) = no stretch; fill = stretch to stage; cover = crop-fill
  const mode = (window.SETTINGS && window.SETTINGS.image_fit) || "contain";
  document.body.classList.remove("fit-fill", "fit-cover");
  if (mode === "fill") document.body.classList.add("fit-fill");
  else if (mode === "cover") document.body.classList.add("fit-cover");
}


function edgeSettings() {
  const s = window.SETTINGS || {};
  return {
    show: s.edge_show !== false,  // default on
    color: s.edge_color || "#ffffff",
    width: Math.max(1, Number(s.edge_width || 2)),
    glow: s.edge_glow !== false,
  };
}

function styleWipeEdge(angleDeg) {
  const e = edgeSettings();
  if (!e.show || !wipeEdge) {
    if (wipeEdge) wipeEdge.style.display = "none";
    return false;
  }
  wipeEdge.style.display = "block";
  wipeEdge.style.opacity = "1";
  wipeEdge.style.background = e.color;
  // thinner, softer edge — less "hard ruler" look
  const w = Math.max(1, Math.min(6, e.width));
  wipeEdge.style.width = w + "px";
  wipeEdge.style.boxShadow = e.glow
    ? `0 0 ${6 + w}px ${e.color}66, 0 0 ${12 + w * 2}px ${e.color}33`
    : "none";
  wipeEdge.style.pointerEvents = "none";

  if (angleDeg != null) {
    wipeEdge.style.left = "50%";
    wipeEdge.style.top = "50%";
    wipeEdge.style.bottom = "auto";
    wipeEdge.style.height = "250vmax";
    const edgeRotation = Number(angleDeg) || 0;
    wipeEdge.style.transform = `translate(-50%, -50%) rotate(${edgeRotation}deg)`;
    wipeEdge.style.transformOrigin = "center center";
  } else {
    wipeEdge.style.left = "50%";
    wipeEdge.style.top = "0";
    wipeEdge.style.bottom = "0";
    wipeEdge.style.height = "auto";
    wipeEdge.style.transform = "translateX(-50%)";
    wipeEdge.style.transformOrigin = "center center";
  }
  return true;
}

function hideWipeEdge() {
  if (wipeEdge) {
    wipeEdge.style.display = "none";
    wipeEdge.style.opacity = "0";
  }
}

function moveAngledEdge(uiAngle, progress01) {
  if (!wipeEdge) return;
  const p = Math.max(0, Math.min(1, Number(progress01) || 0));
  // Hide edge at start/end so it doesn't sit as a permanent line on the frame
  if (p <= 0.02 || p >= 0.98) {
    hideWipeEdge();
    return;
  }
  if (wipeEdge.style.display === "none") {
    styleWipeEdge(uiAngle);
  }
  const cssAngle = (90 + (Number(uiAngle) || 0)) % 360;
  const W = layerOver.offsetWidth || window.innerWidth;
  const H = layerOver.offsetHeight || window.innerHeight;
  const rad = cssAngle * Math.PI / 180;
  const L = Math.abs(W * Math.sin(rad)) + Math.abs(H * Math.cos(rad));
  const distance = (p - 0.5) * L;
  const edgeRotation = Number(uiAngle) || 0;
  wipeEdge.style.display = "block";
  wipeEdge.style.opacity = "1";
  wipeEdge.style.transform = `translate(-50%, -50%) rotate(${edgeRotation}deg) translateX(${distance}px)`;
}

const progress = $("progressBar");
const app = $("app");

const BLEND_CSS = {
  normal: "normal",
  add: "plus-lighter",       // preferred additive
  plus: "plus-lighter",
  lighter: "lighter",        // fallback additive
  screen: "screen",
  multiply: "multiply",
  overlay: "overlay",
  "soft-light": "soft-light",
  "hard-light": "hard-light",
  lighten: "lighten",
  darken: "darken",
  "color-dodge": "color-dodge",
  "color-burn": "color-burn",
  difference: "difference",
};

function projectDefaults(i) {
  const p = passes[i] || {};
  return {
    blend: p.blend || "normal",
    transition: p.transition || "wipe_rl",
    wipe_angle: p.wipe_angle != null ? Number(p.wipe_angle) : 180,
  };
}
function effective(i) { return projectDefaults(i); }

function buildTimeline() {
  const tl = $("timeline");
  if (!tl) return;
  tl.innerHTML = "";
  if (!passes.length) {
    const empty = document.createElement("div");
    empty.className = "item";
    empty.style.opacity = "0.5";
    empty.innerHTML = `<div class="nodeWrap"><div class="node">—</div><div class="nodeName">No passes</div></div>`;
    tl.appendChild(empty);
    return;
  }
  passes.forEach((p, i) => {
    const item = document.createElement("div");
    item.className = "item";
    item.setAttribute("role", "button");
    item.setAttribute("tabindex", "0");
    item.setAttribute("aria-label", `Pass ${i + 1}: ${p.name || "Pass"}`);
    const full = p.name || "Pass";
    const short = full.length > 14 ? full.slice(0, 12) + "…" : full;
    item.title = full;
    item.innerHTML = `<div class="nodeWrap"><div class="node">${String(i + 1).padStart(2, "0")}</div><div class="nodeName">${esc(short)}</div></div>`;
    if (i < passes.length - 1) item.innerHTML += `<div class="connector"></div>`;
    item.onclick = () => show(i, true);
    item.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(i, true); }
    };
    tl.appendChild(item);
  });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
}
function imgSrc(p) { return (p && (p.image || p.after || p.before)) || ""; }
function blendLabel(b) { return String(b || "normal").toUpperCase().replace("-", " "); }
function transitionLabel(t, angle) {
  const map = {
    wipe_rl: "WIPE →", wipe_lr: "WIPE ←", wipe_angle: `WIPE ${Math.round(angle || 0)}°`,
    soft_wipe_rl: "SOFT WIPE →", soft_wipe_lr: "SOFT WIPE ←", soft_wipe_angle: `SOFT WIPE ${Math.round(angle || 0)}°`,
    fade: "CROSS FADE", slide_rl: "SLIDE →", slide_lr: "SLIDE ←", zoom_fade: "ZOOM + FADE",
  };
  return map[t] || "TRANSITION";
}

function setInfo(i) {
  try {
    const _p = (typeof passes !== "undefined") ? passes[i] : null;
    if (_p && typeof VO !== "undefined" && VO.enabled) speakPass(_p);
  } catch (_) {}

  if (!passes.length) {
    const counter = $("counter");
    if (counter) counter.textContent = "00 / 00";
    const pn = $("passName");
    if (pn) pn.textContent = "No passes";
    const mode = $("mode");
    if (mode) mode.textContent = "EMPTY";
    const blend = $("blendTag");
    if (blend) blend.textContent = "—";
    const opacityTag = $("opacityTag");
    if (opacityTag) opacityTag.style.display = "none";
    return;
  }
  const p = passes[i] || {};
  const eff = effective(i);
  const isFinal = !!p.final || i === passes.length - 1;
  const name = p.name || "Pass";
  const accent = accentFor(name);
  document.documentElement.style.setProperty("--accent", accent);

  // Caption text lives outside the image stage — never clipped by wipe
  const counter = $("counter");
  if (counter) {
    counter.textContent = `${String(i + 1).padStart(2, "0")} / ${String(passes.length).padStart(2, "0")}`;
  }
  const pn = $("passName");
  if (pn) {
    // Soft text crossfade only (not image wipe)
    pn.style.animation = "none";
    void pn.offsetWidth;
    pn.style.animation = "";
    pn.textContent = name;
  }
  const mode = $("mode");
  if (mode) mode.textContent = isFinal ? "FINAL BEAUTY" : transitionLabel(eff.transition, eff.wipe_angle);
  const blend = $("blendTag");
  if (blend) blend.textContent = blendLabel(eff.blend);
  const opacityTag = $("opacityTag");
  if (opacityTag) {
    const pct = passOpacityPct(p);
    opacityTag.textContent = `OPACITY ${pct}%`;
    opacityTag.style.display = pct >= 100 ? "none" : "inline-flex";
  }
  const status = $("status");
  if (status) status.textContent = isFinal ? "HOLDING" : "";

  document.querySelectorAll(".item").forEach((e, n) => {
    e.classList.toggle("active", n === i);
    e.classList.toggle("done", n < i);
  });
}

/** Apply presentation chrome visibility from SETTINGS */
function applyChromeSettings() {
  const s = window.SETTINGS || {};
  const body = document.body;
  // Defaults: show everything unless explicitly false
  body.classList.toggle("hide-topbar", s.show_topbar === false);
  body.classList.toggle("hide-counter", s.show_counter === false);
  body.classList.toggle("hide-pass-name", s.show_pass_name === false);
  body.classList.toggle("hide-tags", s.show_tags === false);
  body.classList.toggle("hide-timeline", s.show_timeline === false);
  body.classList.toggle("hide-hint", s.show_hint === false);
  body.classList.toggle("hide-caption", s.show_caption === false);
  // Optional: hide entire top brand text (eyebrow + h1) while keeping controls
  if (s.show_brand === false) {
    const brand = document.querySelector(".topbar .brand");
    if (brand) brand.style.display = "none";
  }
}

function applyBlend(mode, opacityPct) {
  const key = String(mode || "normal").toLowerCase();
  let css = BLEND_CSS[key] || key || "normal";
  layerOver.style.mixBlendMode = css;
  if (css === "plus-lighter") {
    const probe = document.createElement("div");
    probe.style.mixBlendMode = "plus-lighter";
    if (probe.style.mixBlendMode !== "plus-lighter") {
      layerOver.style.mixBlendMode = "lighter";
    }
  }
  if (opacityPct != null && opacityPct !== undefined && opacityPct !== "") {
    let a = Number(opacityPct);
    if (Number.isNaN(a)) a = 100;
    if (a > 1) a = a / 100; // 0–100 → 0–1
    a = Math.max(0, Math.min(1, a));
    layerOver.style.opacity = String(a);
  }
}

function hardResetOver() {
  layerOver.style.transition = "none";
  wipeEdge.style.transition = "none";
  layerOver.style.opacity = "0";
  layerOver.style.clipPath = "none";
  layerOver.style.transform = "none";
  layerOver.style.filter = "none";
  layerOver.style.maskImage = "none";
  layerOver.style.webkitMaskImage = "none";
  layerOver.style.maskSize = "";
  layerOver.style.webkitMaskSize = "";
  layerOver.style.maskPosition = "";
  layerOver.style.webkitMaskPosition = "";
  layerOver.style.maskRepeat = "";
  layerOver.style.webkitMaskRepeat = "";
  layerOver.style.mixBlendMode = "normal";
  wipeEdge.style.display = "none";
  wipeEdge.style.opacity = "0";
}

/** Running composite for additive beauty rebuild (Lighting + GI + Reflection …) */
let compositeDataUrl = null;

function cssBlendToCanvasOp(mode) {
  const m = String(mode || "normal").toLowerCase();
  const map = {
    "normal": "source-over",
    "add": "lighter",
    "plus": "lighter",
    "lighter": "lighter",
    "screen": "screen",
    "multiply": "multiply",
    "overlay": "overlay",
    "soft-light": "soft-light",
    "hard-light": "hard-light",
    "lighten": "lighten",
    "darken": "darken",
    "color-dodge": "color-dodge",
    "color-burn": "color-burn",
    "difference": "difference",
  };
  return map[m] || "source-over";
}

function shouldAccumulate(blend, toP) {
  // Every non-final pass belongs to the running composite.  Even NORMAL
  // passes must use source-over so an earlier AO/lighting/reflection/etc.
  // is not removed when the next pass is revealed.
  // The final pass is normally a complete beauty plate, so it replaces the
  // running stack unless the project explicitly asks for accumulation.
  if (window.SETTINGS && window.SETTINGS.accumulate === false) return false;
  if (toP && toP.final) return false;
  return true;
}

function bakeComposite(baseEl, overEl, blendMode) {
  try {
    const bw = baseEl.naturalWidth || baseEl.width;
    const bh = baseEl.naturalHeight || baseEl.height;
    const ow = overEl.naturalWidth || overEl.width;
    const oh = overEl.naturalHeight || overEl.height;
    const w = Math.max(bw || 0, ow || 0);
    const h = Math.max(bh || 0, oh || 0);
    if (!w || !h) return null;
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d");
    ctx.clearRect(0, 0, w, h);
    if (bw && bh) ctx.drawImage(baseEl, 0, 0, w, h);
    if (overEl && overEl.src && ow && oh) {
      const opacity = arguments.length > 3 && arguments[3] != null
        ? Math.max(0, Math.min(1, Number(arguments[3])))
        : 1;
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.globalCompositeOperation = cssBlendToCanvasOp(blendMode);
      ctx.drawImage(overEl, 0, 0, w, h);
      ctx.restore();
    }
    return c.toDataURL("image/png");
  } catch (e) {
    console.warn("bakeComposite failed", e);
    return null;
  }
}

/** Load a URL into a temporary Image, then resolve. */
function loadImage(src, timeoutMs = 10000) {
  return new Promise((resolve) => {
    if (!src) return resolve(null);
    const im = new Image();
    let finished = false;
    const finish = (value) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      resolve(value);
    };
    const timer = setTimeout(() => finish(null), Math.max(500, Number(timeoutMs) || 10000));
    im.onload = () => finish(im.naturalWidth ? im : null);
    im.onerror = () => finish(null);
    im.src = src;
  });
}

/** Pre-bake composite of baseSrc + overSrc with blendMode → data URL. */
async function bakeCompositeSrc(baseSrc, overSrc, blendMode) {
  const [baseIm, overIm] = await Promise.all([loadImage(baseSrc), loadImage(overSrc)]);
  if (!baseIm || !overIm) return null;
  return bakeComposite(baseIm, overIm, blendMode);
}

function waitImg(img, timeoutMs = 8000) {
  return new Promise((resolve) => {
    if (!img || !img.src) return resolve(false);
    if (img.complete) return resolve(!!img.naturalWidth);
    let finished = false;
    const finish = (ok) => {
      if (finished) return;
      finished = true;
      clearTimeout(timeout);
      img.removeEventListener("load", onLoad);
      img.removeEventListener("error", onError);
      resolve(ok);
    };
    const onLoad = () => finish(!!img.naturalWidth);
    const onError = () => finish(false);
    const timeout = setTimeout(() => finish(false), Math.max(250, Number(timeoutMs) || 8000));
    img.addEventListener("load", onLoad, { once: true });
    img.addEventListener("error", onError, { once: true });
  });
}


/** Opacity 0–1 from pass data */
function passOpacity(p) {
  let v = p && p.opacity != null ? Number(p.opacity) : 100;
  if (!Number.isFinite(v)) v = 100;
  // Project data is stored as 0–100. Accept 0–1 too for backward compatibility.
  if (v > 1) v = v / 100;
  return Math.max(0, Math.min(1, v));
}

function passOpacityPct(p) {
  return Math.round(passOpacity(p) * 100);
}

/**
 * Persistent compositing state.
 *
 * Completed passes stay as real DOM layers.  The currently revealed pass is
 * kept separately in #layerOver during its transition.  This is deliberately
 * not flattened into a temporary bitmap: flattening was the reason the last
 * revealed effect could disappear when the transition layer was removed.
 */
function clearCommittedStack() {
  committedStack = [];
  if (stage) {
    stage.querySelectorAll('.committed-layer').forEach(el => el.remove());
  }
}

function createCommittedLayer(pass, passIndex) {
  const layer = document.createElement('div');
  layer.className = 'layer committed-layer';
  layer.dataset.passIndex = String(passIndex);
  layer.style.zIndex = String(10 + passIndex);
  layer.style.opacity = String(passOpacity(pass));
  layer.style.mixBlendMode = canvasOpToCssBlend(pass.blend || 'normal');
  const img = document.createElement('img');
  img.alt = pass.name || `Pass ${passIndex + 1}`;
  img.src = imgSrc(pass);
  layer.appendChild(img);
  stage.insertBefore(layer, layerOver);
  return { pass, passIndex, layer, img };
}

function canvasOpToCssBlend(mode) {
  const key = String(mode || 'normal').toLowerCase();
  const css = BLEND_CSS[key] || key || 'normal';
  // CSS supports "plus-lighter" in current Chromium. Keep the fallback
  // consistent with the existing viewer behavior for older engines.
  if (css === 'plus-lighter') return 'plus-lighter';
  if (css === 'lighter') return 'plus-lighter';
  return css;
}

async function rebuildCommittedThrough(upto, myToken = token) {
  clearCommittedStack();
  if (upto < 0 || !passes.length) return false;

  const wanted = [];
  for (let i = 0; i <= upto && i < passes.length; i++) {
    const p = passes[i];
    if (!p || p.hidden || p.hide || !imgSrc(p)) continue;
    wanted.push([p, i]);
  }
  if (!wanted.length) return false;

  // Create every permanent layer first, but keep it transparent until its
  // image is confirmed loaded. This prevents a flash of an unready layer.
  const entries = wanted.map(([p, i]) => createCommittedLayer(p, i));
  const results = await Promise.all(entries.map(e => waitImg(e.img)));
  if (myToken !== token) return false;

  let firstGood = null;
  entries.forEach((e, n) => {
    const ok = results[n];
    e.layer.style.visibility = ok ? 'visible' : 'hidden';
    if (ok && !firstGood) firstGood = e.img;
  });
  committedStack = entries.filter((e, n) => results[n]);
  if (!firstGood) return false;

  fitStageToImage(firstGood);
  imgBase.src = '';
  imgBase.style.opacity = '0';
  return true;
}

function commitPass(passIndex) {
  const p = passes[passIndex];
  if (!p || !imgSrc(p)) return null;
  const entry = createCommittedLayer(p, passIndex);
  entry.layer.style.visibility = 'visible';
  committedStack.push(entry);
  return entry;
}

function resetTransitionLayer() {
  imgOver.src = '';
  layerOver.style.opacity = '0';
  layerOver.style.mixBlendMode = 'normal';
  layerOver.style.clipPath = 'none';
  layerOver.style.webkitMaskImage = 'none';
  layerOver.style.maskImage = 'none';
  layerOver.style.transform = 'none';
  layerOver.style.transition = 'none';
}

function setStageLoading(on) {
  const el = $("stageLoader");
  if (el) el.hidden = !on;
  const err = $("stageError");
  if (err && on) err.hidden = true;
}
function showImageError(message) {
  const status = $("status");
  if (status) status.textContent = message || "IMAGE ERROR";
  if (progress) progress.style.width = "0%";
  setStageLoading(false);
  const err = $("stageError");
  const msg = $("errMsg");
  if (err) {
    err.hidden = false;
    if (msg) msg.textContent = message || "Image missing or failed to load";
  }
}
function clearStageError() {
  const err = $("stageError");
  if (err) err.hidden = true;
}

function showInstant(i) {
  if (!passes.length) return;
  cancelAnimationFrame(animationId);
  clearTimeout(timer);
  token++;
  const my = token;
  index = (i + passes.length) % passes.length;
  const p = passes[index];
  progress.style.width = "0%";
  setInfo(index);
  hardResetOver();
  resetTransitionLayer();
  applyBlend("normal");
  clearStageError();
  setStageLoading(true);

  (async () => {
    const ok = await rebuildCommittedThrough(index, my);
    if (my !== token) return;
    setStageLoading(false);
    if (!ok) {
      showImageError("IMAGE NOT FOUND");
      return;
    }
    const top = committedStack[committedStack.length - 1];
    fitStageToImage(top ? top.img : null);
    const isFinal = !!p.final || index === passes.length - 1;
    if (isFinal) startHold(p, my);
    else startPauseThenAdvance(p, my);
  })();
}

function show(i, instant) {
  if (!passes.length) return;
  if (instant) { showInstant(i); return; }
  const next = (i + passes.length) % passes.length;
  if (next === index) return;

  cancelAnimationFrame(animationId);
  clearTimeout(timer);
  const my = ++token;
  const fromIndex = index;
  const toP = passes[next];
  const eff = effective(next);
  const dur = Math.max(300, Number(toP.slide_ms != null ? toP.slide_ms : 1200));
  const blend = String(toP.blend || eff.blend || "normal").toLowerCase();
  const targetOpacity = passOpacity(toP);

  index = next;
  setInfo(index);
  $("status").textContent = "TRANSITION";
  progress.style.width = "0%";
  clearStageError();

  (async () => {
    // The committed stack is the complete state BEFORE the incoming pass.
    // Rebuilding it here also makes the logic safe after manual jumps.
    const baseOk = await rebuildCommittedThrough(fromIndex, my);
    if (my !== token) return;
    if (!baseOk) {
      showImageError("IMAGE NOT FOUND");
      return;
    }

    resetTransitionLayer();
    imgOver.src = imgSrc(toP);
    const targetOk = await waitImg(imgOver);
    if (my !== token) return;
    if (!targetOk) {
      showImageError("IMAGE NOT FOUND");
      if (playing) timer = setTimeout(() => show(index + 1), 1200);
      return;
    }

    fitStageToImage(imgOver);
    // The incoming pass is never in the committed stack before this point.
    // Its own blend + opacity are active throughout the transition.
    applyBlend(blend, targetOpacity * 100);
    layerOver.style.zIndex = String(10 + fromIndex + 1);
    layerOver.style.opacity = "0";
    void layerOver.offsetWidth;

    const start = performance.now();
    function prog(now) {
      if (my !== token) return;
      const q = Math.min(1, (now - start) / dur);
      progress.style.width = (q * 40) + "%";
      if (q < 1) animationId = requestAnimationFrame(prog);
    }
    animationId = requestAnimationFrame(prog);

    const finish = async () => {
      if (my !== token) return;
      cancelAnimationFrame(animationId);

      // CRITICAL: commit the exact incoming pass as a permanent layer BEFORE
      // hiding/removing the transition layer. This makes the final transition
      // frame and the post-transition frame identical and preserves its blend
      // mode and opacity. No flattening/baking is required.
      const committed = commitPass(next);
      if (!committed) {
        showImageError("IMAGE NOT FOUND");
        return;
      }

      resetTransitionLayer();
      layerOver.style.zIndex = "2";
      const top = committedStack[committedStack.length - 1];
      fitStageToImage(top ? top.img : null);
      progress.style.width = "40%";

      const isFinal = !!toP.final || index === passes.length - 1;
      if (isFinal) startHold(toP, my);
      else startPauseThenAdvance(toP, my);
    };

    // The overlay is hidden until runTransition explicitly reveals it.
    layerOver.style.opacity = "0";
    runTransition(eff.transition, dur, eff.wipe_angle, finish, my, targetOpacity);
  })();
}


function runAngledWipe(dur, uiAngle, soft, onDone, my, targetOpacity = 1) {
  // uiAngle 0 = L→R, 90 = T→B, 180 = R→L, 270 = B→T
  const cssAngle = (90 + (Number(uiAngle) || 0)) % 360;
  const feather = soft ? 14 : 0.5;
  const showEdge = styleWipeEdge(Number(uiAngle) || 0);
  if (showEdge) {
    wipeEdge.style.transition = "none";
    moveAngledEdge(Number(uiAngle) || 0, 0);
  }
  const ease = t => 1 - Math.pow(1 - t, 3);
  function applyMask(pct) {
    // black = show OVER (composite effect), transparent = show BASE (previous)
    const p = Math.max(0, Math.min(100, pct));
    const a = Math.max(0, p - feather);
    const b = Math.min(100, p + feather);
    const grad = `linear-gradient(${cssAngle}deg, black 0%, black ${a}%, transparent ${b}%, transparent 100%)`;
    layerOver.style.webkitMaskImage = grad;
    layerOver.style.maskImage = grad;
    layerOver.style.webkitMaskSize = "100% 100%";
    layerOver.style.maskSize = "100% 100%";
    layerOver.style.webkitMaskRepeat = "no-repeat";
    layerOver.style.maskRepeat = "no-repeat";
  }
  // CRITICAL: mask fully hidden BEFORE making layer visible (no flash of final image).
  // Respect the pass opacity for the entire angled-wipe transition.
  applyMask(0);
  layerOver.style.opacity = String(Math.max(0, Math.min(1, Number(targetOpacity) || 0)));
  void layerOver.offsetWidth;
  const start = performance.now();
  function frame(now) {
    if (my !== token) return;
    const t = Math.min(1, (now - start) / dur);
    const e = ease(t);
    applyMask(e * 100);
    if (showEdge) moveAngledEdge(Number(uiAngle) || 0, e);
    if (t < 1) animationId = requestAnimationFrame(frame);
    else {
      applyMask(100);
      if (showEdge) hideWipeEdge();
      onDone();
    }
  }
  animationId = requestAnimationFrame(frame);
}

function runTransition(trans, dur, angle, onDone, my, targetOpacity = 1) {
  targetOpacity = Math.max(0, Math.min(1, Number(targetOpacity) || 0));
  const easeCss = "cubic-bezier(0.4, 0.0, 0.2, 1)";
  let ended = false;
  const done = () => { if (ended || my !== token) return; ended = true; onDone(); };
  const safety = setTimeout(done, dur + 120);
  const afterTransition = (el, prop) => {
    const handler = (e) => {
      if (prop && e.propertyName && e.propertyName !== prop && !String(e.propertyName).includes(prop)) return;
      el.removeEventListener("transitionend", handler);
      clearTimeout(safety);
      done();
    };
    el.addEventListener("transitionend", handler);
  };
  function showHEdge(fromPct, toPct) {
    if (!styleWipeEdge(null)) return;
    wipeEdge.style.transition = "none";
    wipeEdge.style.opacity = "1";
    wipeEdge.style.left = fromPct;
    void wipeEdge.offsetWidth;
    wipeEdge.style.transition = `left ${dur}ms ${easeCss}, opacity 120ms ease`;
    wipeEdge.style.left = toPct;
    // Fade edge out as the wipe finishes so no permanent line remains
    setTimeout(() => {
      if (wipeEdge) wipeEdge.style.opacity = "0";
    }, Math.max(0, dur - 80));
    setTimeout(() => { hideWipeEdge(); }, dur + 140);
  }
  switch (trans) {
    case "wipe_angle": clearTimeout(safety); runAngledWipe(dur, angle, false, done, my, targetOpacity); break;
    case "soft_wipe_angle": clearTimeout(safety); runAngledWipe(dur, angle, true, done, my, targetOpacity); break;
    case "wipe_lr":
      layerOver.style.clipPath = "inset(0 100% 0 0)"; layerOver.style.opacity = String(targetOpacity);
      showHEdge("0%", "100%"); void layerOver.offsetWidth;
      layerOver.style.transition = `clip-path ${dur}ms ${easeCss}`;
      layerOver.style.clipPath = "inset(0 0% 0 0)"; afterTransition(layerOver, "clip-path"); break;
    case "soft_wipe_rl": case "soft_wipe_lr": {
      wipeEdge.style.display = "none"; layerOver.style.opacity = String(targetOpacity); clearTimeout(safety);
      const dir = trans === "soft_wipe_lr" ? "right" : "left";
      const start = performance.now(); const ease = t => 1 - Math.pow(1 - t, 3);
      function frame(now) {
        if (my !== token) return;
        const t = Math.min(1, (now - start) / dur); const p = ease(t) * 100;
        const grad = `linear-gradient(to ${dir}, black 0%, black ${p}%, transparent ${Math.min(100, p + 25)}%, transparent 100%)`;
        layerOver.style.webkitMaskImage = grad; layerOver.style.maskImage = grad;
        if (t < 1) animationId = requestAnimationFrame(frame); else done();
      }
      animationId = requestAnimationFrame(frame); break;
    }
    case "fade":
      wipeEdge.style.display = "none"; layerOver.style.opacity = "0"; void layerOver.offsetWidth;
      layerOver.style.transition = `opacity ${dur}ms ${easeCss}`; layerOver.style.opacity = String(targetOpacity);
      afterTransition(layerOver, "opacity"); break;
    case "slide_rl": case "slide_lr": {
      wipeEdge.style.display = "none"; layerOver.style.opacity = String(targetOpacity);
      layerOver.style.transform = trans === "slide_rl" ? "translateX(100%)" : "translateX(-100%)";
      void layerOver.offsetWidth;
      layerOver.style.transition = `transform ${dur}ms ${easeCss}`; layerOver.style.transform = "translateX(0)";
      afterTransition(layerOver, "transform"); break;
    }
    case "zoom_fade":
      wipeEdge.style.display = "none"; layerOver.style.opacity = "0"; layerOver.style.transform = "scale(1.08)";
      void layerOver.offsetWidth;
      layerOver.style.transition = `opacity ${dur}ms ${easeCss}, transform ${dur}ms ${easeCss}`;
      layerOver.style.opacity = String(targetOpacity); layerOver.style.transform = "scale(1)";
      afterTransition(layerOver, "opacity"); break;
    default:
      layerOver.style.clipPath = "inset(0 0 0 100%)"; layerOver.style.opacity = String(targetOpacity);
      showHEdge("100%", "0%"); void layerOver.offsetWidth;
      layerOver.style.transition = `clip-path ${dur}ms ${easeCss}`;
      layerOver.style.clipPath = "inset(0 0 0 0%)"; afterTransition(layerOver, "clip-path"); break;
  }
}

function startPauseThenAdvance(p, my) {
  if (my !== undefined && my !== token) return;
  $("status").textContent = "";
  const pauseMs = Math.max(0, Number(p.pause_ms || 800));
  const start = performance.now();
  function tick(now) {
    if (my !== undefined && my !== token) return;
    if (!playing) return;
    const q = Math.min(1, (now - start) / Math.max(1, pauseMs));
    progress.style.width = (40 + q * 60) + "%";
    if (q < 1) animationId = requestAnimationFrame(tick);
    else { progress.style.width = "100%"; if (playing) timer = setTimeout(() => show(index + 1), 50); }
  }
  if (pauseMs <= 0) { progress.style.width = "100%"; if (playing) timer = setTimeout(() => show(index + 1), 50); }
  else animationId = requestAnimationFrame(tick);
}

function startHold(p, my) {
  if (my !== undefined && my !== token) return;
  $("status").textContent = "HOLDING";
  $("mode").textContent = "FINAL BEAUTY";
  const holdSec = Math.max(1, Number(p.hold || 10));
  const dur = holdSec * 1000;
  const start = performance.now();
  function tick(now) {
    if (my !== undefined && my !== token) return;
    if (!playing) return;
    const q = Math.min(1, (now - start) / dur);
    progress.style.width = (q * 100) + "%";
    if (q < 1) animationId = requestAnimationFrame(tick);
    else if (playing) timer = setTimeout(() => show(0, true), 50);
  }
  animationId = requestAnimationFrame(tick);
}

function toggle() {
  playing = !playing;
  $("play").textContent = playing ? "PAUSE" : "PLAY";
  if (playing) showInstant(index);
  else { cancelAnimationFrame(animationId); clearTimeout(timer); }
}

let uiTimer = null;
function pokeUi() {
  if (!app.classList.contains("fs")) return;
  app.classList.add("showUi");
  clearTimeout(uiTimer);
  uiTimer = setTimeout(() => app.classList.remove("showUi"), 2200);
}
async function toggleFs() {
  if (app.classList.contains("fs")) {
    app.classList.remove("fs", "showUi");
    try {
      if (document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen();
    } catch (_) {}
    return;
  }
  app.classList.add("fs");
  try {
    if (document.documentElement.requestFullscreen && !document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    }
    pokeUi();
  } catch (_) {
    app.classList.remove("fs", "showUi");
  }
}
function showAb(on) {
  const flash = $("abFlash");
  const img = $("abImg");
  if (!flash) return;
  if (on) {
    const prev = passes[(index - 1 + passes.length) % passes.length];
    img.src = imgSrc(prev);
    flash.hidden = false;
    $("ab").classList.add("active");
    $("status").textContent = "A/B PREV";
  } else {
    flash.hidden = true;
    $("ab").classList.remove("active");
    $("status").textContent = "";
  }
}

function togglePresentation() {
  document.body.classList.toggle("presentation");
  const on = document.body.classList.contains("presentation");
  try { localStorage.setItem("rpb-presentation", on ? "1" : "0"); } catch (_) {}
  const hint = $("hint");
  if (hint) hint.textContent = on
    ? "Presentation mode · P = exit · ? help"
    : "Space play · ← → · B hold A/B · F fullscreen · T theme · P presentation · ? help · 1–9 jump";
}

function toggleTheme() {
  document.body.classList.toggle("light");
  try {
    localStorage.setItem("rpb-theme", document.body.classList.contains("light") ? "light" : "dark");
  } catch (_) {}
}

function setHelpOpen(on) {
  const overlay = $("helpOverlay");
  if (!overlay) return;
  overlay.hidden = !on;
  if (on) {
    const closeBtn = $("helpClose");
    if (closeBtn) closeBtn.focus();
  }
}
function toggleHelp() {
  const overlay = $("helpOverlay");
  if (!overlay) return;
  setHelpOpen(overlay.hidden);
}

$("prev").onclick = () => show(index - 1, true);
$("next").onclick = () => show(index + 1, true);
$("restart").onclick = () => show(0, true);
$("play").onclick = toggle;
$("fs").onclick = toggleFs;
$("theme").onclick = toggleTheme;
if ($("help")) $("help").onclick = toggleHelp;
if ($("helpClose")) $("helpClose").onclick = () => setHelpOpen(false);
if ($("helpOverlay")) {
  $("helpOverlay").addEventListener("click", (e) => {
    if (e.target === $("helpOverlay")) setHelpOpen(false);
  });
}
if ($("ab")) {
  const ab = $("ab");
  ab.onpointerdown = (e) => { e.preventDefault(); showAb(true); };
  ab.onpointerup = () => showAb(false);
  ab.onpointercancel = () => showAb(false);
  ab.onpointerleave = () => showAb(false);
}
document.addEventListener("mousemove", pokeUi, { passive: true });
document.addEventListener("touchstart", pokeUi, { passive: true });

document.addEventListener("keydown", e => {
  if (e.target && (e.target.tagName === "SELECT" || e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
  // Help panel open: only Esc / ? close it
  if ($("helpOverlay") && !$("helpOverlay").hidden) {
    if (e.key === "Escape" || e.key === "?" || e.key === "/") {
      e.preventDefault();
      setHelpOpen(false);
    }
    return;
  }
  if (e.key === "ArrowRight") show(index + 1, true);
  if (e.key === "v" || e.key === "V") toggleVO();
  if (e.key === "m" || e.key === "M") toggleBed();
  if (e.key === "ArrowLeft") show(index - 1, true);
  if (e.key === "Home") show(0, true);
  if (e.key === " ") { e.preventDefault(); toggle(); }
  if (e.key === "f" || e.key === "F") toggleFs();
  if (e.key === "b" || e.key === "B") { if (e.type === "keydown") showAb(true); }
  if (e.key === "t" || e.key === "T") toggleTheme();
  if (e.key === "p" || e.key === "P") togglePresentation();
  if (e.key === "?" || (e.shiftKey && e.key === "/")) { e.preventDefault(); toggleHelp(); }
  if (e.key >= "1" && e.key <= "9") {
    const n = parseInt(e.key, 10) - 1;
    if (n < passes.length) show(n, true);
  }
  if (e.key === "Escape" && app.classList.contains("fs")) toggleFs();
});

document.addEventListener("keyup", e => {
  if (e.key === "b" || e.key === "B") showAb(false);
});

// ---------- Presenter VO (Web Speech API) + optional soundtrack ----------
const VO = {
  enabled: false,
  rate: 1,
  voiceURI: "",
  bed: null,
  bedVolume: 0.25,
};

function getVoices() {
  try { return window.speechSynthesis ? speechSynthesis.getVoices() : []; }
  catch (_) { return []; }
}

function pickFemaleVoice() {
  const voices = getVoices();
  if (!voices.length) return null;
  const prefer = [
    /zira/i, /hazel/i, /susan/i, /samantha/i, /victoria/i, /karen/i,
    /moira/i, /tessa/i, /fiona/i, /female/i, /woman/i,
    /google uk english female/i, /microsoft.*(zira|hazel|susan)/i,
  ];
  for (const re of prefer) {
    const v = voices.find(x => re.test(x.name) || re.test(x.voiceURI || ""));
    if (v) return v;
  }
  const en = voices.filter(x => (x.lang || "").toLowerCase().startsWith("en"));
  return en.find(x => !/male|david|mark|james|george|daniel/i.test(x.name)) || en[0] || voices[0] || null;
}

function duckBed(on) {
  if (!VO.bed) return;
  try {
    VO.bed.volume = on
      ? Math.min(0.08, Number((window.SETTINGS && window.SETTINGS.soundtrack_volume) || VO.bedVolume) * 0.25)
      : Number((window.SETTINGS && window.SETTINGS.soundtrack_volume) || VO.bedVolume);
  } catch (_) {}
}

function speakText(text) {
  if (!VO.enabled || !text || !window.speechSynthesis) return;
  try {
    speechSynthesis.cancel();
    duckBed(true);
    const u = new SpeechSynthesisUtterance(String(text));
    u.rate = VO.rate || 0.95;
    u.pitch = 1.05;
    const voices = getVoices();
    let v = null;
    if (VO.voiceURI) {
      v = voices.find(x => x.voiceURI === VO.voiceURI || x.name === VO.voiceURI);
    }
    if (!v) v = pickFemaleVoice();
    if (v) u.voice = v;
    u.onend = () => duckBed(false);
    u.onerror = () => duckBed(false);
    speechSynthesis.speak(u);
  } catch (_) { duckBed(false); }
}


function buildChapters() {
  const custom = (window.SETTINGS && window.SETTINGS.chapters) || [];
  if (Array.isArray(custom) && custom.length) return custom;
  const keys = [
    { re: /beauty|final/i, label: "Beauty" },
    { re: /\bao\b|ambient|occlusion|shadow/i, label: "AO / Shadow" },
    { re: /reflect|specular|gloss/i, label: "Reflection" },
    { re: /light|gi|illum|diffuse/i, label: "Lighting" },
    { re: /sss|subsurface|skin/i, label: "SSS" },
  ];
  const out = [];
  const seen = new Set();
  (passes || []).forEach((p, i) => {
    const n = String(p.name || "");
    for (const k of keys) {
      if (k.re.test(n) && !seen.has(k.label)) {
        seen.add(k.label);
        out.push({ label: k.label, index: i });
        break;
      }
    }
  });
  return out;
}

function renderChapters() {
  let bar = document.getElementById("chapterBar");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "chapterBar";
    bar.className = "chapterBar";
    const host = document.querySelector(".passBar") || document.getElementById("app") || document.body;
    host.appendChild(bar);
  }
  const chapters = buildChapters();
  if (!chapters.length) { bar.style.display = "none"; return; }
  bar.style.display = "flex";
  bar.innerHTML = chapters.map(c =>
    `<button type="button" data-i="${c.index}" class="chapterBtn">${c.label}</button>`
  ).join("");
  bar.querySelectorAll("button").forEach(btn => {
    btn.onclick = () => {
      const i = parseInt(btn.getAttribute("data-i"), 10);
      if (!isNaN(i)) show(i, true);
    };
  });
}

function speakPass(pass) {
  if (!pass) return;
  const name = pass.name || "Pass";
  const desc = (pass.description || "").trim();
  speakText(desc ? `${name}. ${desc}` : name);
}

function toggleVO(force) {
  VO.enabled = force != null ? !!force : !VO.enabled;
  const btn = document.getElementById("voBtn");
  if (btn) {
    btn.classList.toggle("active", VO.enabled);
    btn.textContent = VO.enabled ? "VO On" : "VO";
    btn.title = VO.enabled ? "Voice-over on (V)" : "Voice-over off (V)";
  }
  try { localStorage.setItem("rpb-vo", VO.enabled ? "1" : "0"); } catch (_) {}
  if (!VO.enabled && window.speechSynthesis) {
    try { speechSynthesis.cancel(); } catch (_) {}
  } else if (VO.enabled) {
    // Confirm engine works with a short cue
    const p = (typeof passes !== "undefined" && passes[typeof index === "number" ? index : 0]) || null;
    if (p) speakPass(p);
    else speakText("Voice over on");
  }
}

function setupSoundtrack() {
  const src = (window.SETTINGS && window.SETTINGS.soundtrack) || "";
  if (!src) return;
  try {
    if (VO.bed) { VO.bed.pause(); VO.bed = null; }
    const a = new Audio(src);
    a.loop = true;
    a.volume = Number((window.SETTINGS && window.SETTINGS.soundtrack_volume) || VO.bedVolume);
    a.addEventListener("error", () => {
      console.warn("Soundtrack failed to load:", src);
    });
    VO.bed = a;
  } catch (e) {
    console.warn("Soundtrack setup error", e);
  }
}

function toggleBed() {
  if (!VO.bed) setupSoundtrack();
  if (!VO.bed) return;
  if (VO.bed.paused) VO.bed.play().catch(() => {});
  else VO.bed.pause();
}

// Hook: speak when pass changes — wrap showInstant if present

document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement) app.classList.remove("fs");
});

// Logo burn-in
if (SETTINGS.logo) {
  const logo = $("logoBurn");
  logo.src = SETTINGS.logo;
  logo.hidden = false;
}
try {
  if (localStorage.getItem("rpb-theme") === "light") document.body.classList.add("light");
  if (localStorage.getItem("rpb-presentation") === "1") document.body.classList.add("presentation");
  if (localStorage.getItem("rpb-vo") === "1") toggleVO(true);
} catch (_) {}
setupSoundtrack();
// Chrome loads voices async
if (window.speechSynthesis) {
  try { speechSynthesis.onvoiceschanged = () => {}; } catch (_) {}
}

$("projectTitle").textContent = window.PROJECT_TITLE || "Render Pass Breakdown";
if ($("introTitle")) $("introTitle").textContent = window.PROJECT_TITLE || "Render Pass Breakdown";
applyChromeSettings();
buildTimeline();

// Empty project guard
if (!passes.length) {
  const intro = $("intro");
  if (intro) intro.classList.add("hide");
  setInfo(0);
  showImageError("No visible passes — open the editor and import images");
  $("play").textContent = "PLAY";
  playing = false;
} else {
  const intro = $("intro");
  if (intro && !sessionStorage.getItem("rpb-skip-intro")) {
    setTimeout(() => {
      intro.classList.add("hide");
      showInstant(0);
    }, 1600);
  } else {
    if (intro) intro.classList.add("hide");
    showInstant(0);
  }
}