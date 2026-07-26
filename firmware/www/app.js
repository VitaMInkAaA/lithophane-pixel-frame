// Panel LED Lampki. Bez frameworków - wszystko na czystym JS.
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const PALETTE = ['#ffffff', '#ffd18c', '#ff8a2b', '#ff2b2b', '#ff2bb0',
                 '#8a2bff', '#2b6bff', '#2bd7ff', '#2bff88', '#c8ff2b'];

let ST = null;
let W = 7, H = 9;
let brush = 0xff0000;
let painting = false;

// edytowana animacja: lista klatek {px: [63 liczb], ms: int}
let AN = [];
let cur = 0;
let playing = false, playT = null;

// ------------------------------------------------------------------ narzędzia
async function api(name, body) {
  const opt = body
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    : {};
  try {
    const r = await fetch('/api/' + name, opt);
    return await r.json();
  } catch (e) {
    toast('brak łączności z lampką');
    return { ok: false };
  }
}

let toastT = null;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.remove('on'), 2400);
}

function debounce(fn, ms) {
  let t = null;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

const hex = (v) => '#' + v.toString(16).padStart(6, '0');
const num = (h) => parseInt(String(h).slice(1), 16) || 0;
const toHexStr = (px) => px.map((v) => v.toString(16).padStart(6, '0')).join('');
function fromHexStr(s) {
  const out = [];
  for (let i = 0; i + 6 <= s.length; i += 6) out.push(parseInt(s.substr(i, 6), 16) || 0);
  while (out.length < W * H) out.push(0);
  return out.slice(0, W * H);
}
function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// --------------------------------------------------------------------- zakładki
$$('.tab').forEach((b) => b.onclick = () => {
  $$('.tab').forEach((x) => x.classList.toggle('on', x === b));
  $$('.panel').forEach((p) => p.classList.toggle('on', p.id === 'tab-' + b.dataset.tab));
  if (b.dataset.tab !== 'edit') stopPlay(false);
  if (b.dataset.tab === 'gal') loadGallery();
});

// ----------------------------------------------------------------------- stan
function apply(st) {
  if (!st || !st.ok) return;
  ST = st;
  if (st.w !== W || st.h !== H || !AN.length) {
    W = st.w; H = st.h;
    buildGrid();
    if (!AN.length) { AN = [blankFrame()]; cur = 0; renderStrip(); redraw(); }
  }

  $('#power').classList.toggle('on', st.on);
  const sta = st.net.mode.indexOf('sta') === 0;
  const dot = $('#dot');
  dot.className = 'dot ' + (!st.on ? 'off' : sta ? 'up' : 'ap');
  $('#netinfo').textContent = sta
    ? (st.net.host ? st.net.host + '.local · ' + st.net.ip : st.net.ip)
    : 'tryb AP · ' + st.net.ip;

  setSlider('#br', '#brOut', st.brightness, '%');
  setSlider('#sp', '#spOut', st.speed, '%');
  amps(st.brightness);
  if (document.activeElement !== $('#col')) $('#col').value = st.color;
  markSwatches('#swatches', st.color);
  const colOff = !st.color_ok;
  $('#colCard').classList.toggle('off', colOff);
  $('#colHint').textContent = colOff
    ? 'Ten tryb maluje własnymi kolorami — wybór działa tylko w trybach „Kolor stały" i „Oddech".'
    : 'Kolor, którym świeci ten tryb.';

  renderAnims(st);
  renderSeq(st);

  $('#ao').checked = st.auto_off;
  if (document.activeElement !== $('#aoMin')) $('#aoMin').value = st.auto_off_min;
  $('#aoLeft').textContent = st.auto_off_left == null
    ? 'Wyłączone.'
    : 'Zgaśnie za ' + Math.ceil(st.auto_off_left / 60) + ' min.';

  $('#origin').value = st.origin;
  $('#rows').value = st.rows ? '1' : '0';
  $('#snake').checked = st.serpentine;
  $('#btnLogic').value = st.btn_active_high ? '1' : '0';
  $('#showIp').checked = st.show_ip;
  $('#logFile').checked = st.log_file;
  $('#wifiPm').checked = st.wifi_powersave;

  if (document.activeElement !== $('#host')) $('#host').value = st.hostname;
  $('#hostUrl').textContent = 'http://' + st.hostname + '.local/';
  $('#apAlways').checked = st.ap_always;
  $('#captive').checked = st.captive;
  $('#apName').textContent = st.ap_ssid;

  const r = st.net.rssi;
  const sig = r == null ? '' :
    ' Sygnał <b>' + r + ' dBm</b> — ' +
    (r >= -60 ? 'dobry' : r >= -70 ? 'wystarczający'
     : r >= -78 ? 'słaby' : 'za słaby, panel może być nieosiągalny') + '.';
  $('#wifiState').innerHTML = sta
    ? 'Połączona z <b>' + esc(st.net.ssid) + '</b>.' + sig
    : 'Tryb Access Point — lampka nie jest w żadnej sieci. '
      + 'Wpisz dane swojej sieci, żeby dołączyła do domowego WiFi.';
  const errBox = $('#wifiErr');
  if (st.net.trying) {
    errBox.className = 'err wait';
    errBox.textContent = 'Łączę się z „' + st.net.ssid + '"… to potrwa do ~45 s.';
  } else if (st.net.err) {
    errBox.className = 'err';
    errBox.textContent = 'Nie udało się połączyć: ' + st.net.err;
  } else {
    errBox.className = 'err';
    errBox.textContent = '';
  }
  if (document.activeElement !== $('#country')) $('#country').value = st.country || '';
  renderAddrs(st);
  if (sta && !$('#ssid').value) $('#ssid').value = st.net.ssid;
}

function setSlider(sel, out, val, unit) {
  const el = $(sel);
  if (document.activeElement !== el) el.value = val;
  $(out).textContent = val + unit;
}

function amps(br) {
  const a = (0.06 * W * H * br / 100).toFixed(1);
  $('#brHint').textContent = 'Pobór przy pełnej bieli: około ' + a + ' A.';
}

async function refresh() { apply(await api('state')); }

// ------------------------------------------------------------------ animacje
function renderAnims(st) {
  const box = $('#anims');
  const want = st.anims.map((a) => a.id + (a.seq ? '+' : '-')).join('|');
  if (box.dataset.k !== want) {
    box.dataset.k = want;
    box.innerHTML = '';
    st.anims.forEach((a) => {
      const b = document.createElement('button');
      b.className = 'abtn';
      b.textContent = a.label;
      b.dataset.id = a.id;
      b.onclick = async () => apply(await api('anim', { id: a.id }));
      box.appendChild(b);
    });
  }
  $$('#anims .abtn').forEach((b) => b.classList.toggle('on', b.dataset.id === st.anim));
}

const sendSet = debounce((body) => api('set', body), 180);

$('#br').oninput = (e) => {
  $('#brOut').textContent = e.target.value + '%';
  amps(+e.target.value);
  sendSet({ brightness: +e.target.value });
};
$('#sp').oninput = (e) => {
  $('#spOut').textContent = e.target.value + '%';
  sendSet({ speed: +e.target.value });
};
$('#col').oninput = (e) => {
  markSwatches('#swatches', e.target.value);
  sendSet({ color: e.target.value });
};
$('#power').onclick = async () => apply(await api('toggle', {}));

function buildSwatches(sel, cb) {
  const box = $(sel);
  PALETTE.forEach((c) => {
    const b = document.createElement('button');
    b.className = 'sw';
    b.style.background = c;
    b.dataset.c = c;
    b.onclick = () => cb(c);
    box.appendChild(b);
  });
}
function markSwatches(sel, c) {
  $$(sel + ' .sw').forEach((b) => b.classList.toggle('on', b.dataset.c === String(c).toLowerCase()));
}
buildSwatches('#swatches', (c) => {
  $('#col').value = c;
  markSwatches('#swatches', c);
  api('set', { color: c });
});
buildSwatches('#brushSw', (c) => {
  brush = num(c);
  $('#brush').value = c;
  markSwatches('#brushSw', c);
});

// ============================================================ EDYTOR KLATEK
// Wszystkie efekty liczy przeglądarka i zapieka wynik w piksele. Pico dostaje
// gotowe klatki i robi dokładnie to samo co wcześniej — jeden blit na klatkę.
// Dzięki temu można dowolnie kombinować z efektami bez obciążania lampki.
const blankFrame = () => ({ px: new Array(W * H).fill(0), ms: 200 });

const R = (v) => (v >> 16) & 255;
const G = (v) => (v >> 8) & 255;
const B = (v) => v & 255;
const cl = (v) => (v < 0 ? 0 : v > 255 ? 255 : Math.round(v));
const mk = (r, g, b) => (cl(r) << 16) | (cl(g) << 8) | cl(b);

// ---- historia (dwa stosy: co było przedtem / co cofnięto) -------------------
const HIST_MAX = 40;
let UNDO = [], REDO = [];

const cloneAN = (a) => a.map((f) => ({ px: f.px.slice(), ms: f.ms }));
const snapState = () => ({ an: cloneAN(AN), cur: cur });

/** Wołane PRZED każdą zmianą - zapamiętuje stan sprzed niej. */
function snapshot() {
  UNDO.push(snapState());
  if (UNDO.length > HIST_MAX) UNDO.shift();
  REDO = [];                      // nowa gałąź zmian kasuje to, co cofnięte
  histBtns();
}

function useState(st) {
  AN = cloneAN(st.an);
  cur = Math.min(st.cur, AN.length - 1);
  renderStrip(); redraw(); liveSend();
  histBtns();
}

function histBtns() {
  $('#undo').disabled = !UNDO.length;
  $('#redo').disabled = !REDO.length;
}

$('#undo').onclick = () => {
  if (!UNDO.length) { toast('nie ma czego cofać'); return; }
  REDO.push(snapState());
  useState(UNDO.pop());
};
$('#redo').onclick = () => {
  if (!REDO.length) { toast('nie ma czego ponawiać'); return; }
  UNDO.push(snapState());
  useState(REDO.pop());
};

function afterEdit() {
  renderStrip(); redraw(); liveSend();
}

function buildGrid() {
  const g = $('#pixgrid');
  g.style.gridTemplateColumns = 'repeat(' + W + ', 1fr)';
  g.innerHTML = '';
  for (let i = 0; i < W * H; i++) {
    const d = document.createElement('div');
    d.className = 'px';
    d.dataset.i = i;
    g.appendChild(d);
  }
}

function frame() { return AN[cur] || (AN[cur] = blankFrame()); }

// Tlo pustej komorki. Przy wlaczonym "duchu" pokazujemy slad poprzedniej
// klatki - bez tego rysowanie ruchu klatka po klatce to zgadywanka.
const CELL_BG = [0x14, 0x16, 0x1c];
function ghostBg(v) {
  const k = 0.26;
  const r = Math.round(CELL_BG[0] + (R(v) - CELL_BG[0]) * k);
  const g = Math.round(CELL_BG[1] + (G(v) - CELL_BG[1]) * k);
  const b = Math.round(CELL_BG[2] + (B(v) - CELL_BG[2]) * k);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}

function redraw() {
  const px = frame().px;
  const ghost = (!playing && $('#onion').checked && cur > 0) ? AN[cur - 1].px : null;
  $$('#pixgrid .px').forEach((el, i) => {
    if (px[i]) el.style.background = hex(px[i]);
    else if (ghost && ghost[i]) el.style.background = ghostBg(ghost[i]);
    else el.style.background = '';
  });
  $('#fMs').value = frame().ms;
  info();
}

function info() {
  const total = AN.reduce((s, f) => s + f.ms, 0);
  const lim = ST && ST.limits ? ST.limits.frames : 40;
  $('#fPos').textContent = (cur + 1) + ' / ' + AN.length;
  $('#animInfo').textContent = 'Klatka ' + (cur + 1) + ' z ' + AN.length
    + ' · cała pętla ' + (total / 1000).toFixed(1) + ' s · maksymalnie ' + lim + ' klatek.';
}

function drawThumb(cv, px) {
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#05060a';
  ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < px.length; i++) {
    if (!px[i]) continue;
    ctx.fillStyle = hex(px[i]);
    ctx.fillRect(i % W, Math.floor(i / W), 1, 1);
  }
}

/** Samo przesunięcie zaznaczenia. Przy odtwarzaniu wołane po kilkanaście razy
 *  na sekundę, więc NIE przebudowuje pasków klatek - na telefonie ciągłe
 *  tworzenie kilkudziesięciu <canvas> od nowa dławiło animację. */
/** Przesuwa pasek klatek w POZIOMIE, nie ruszając strony.
 *  scrollIntoView przewijał całą stronę - przy odtwarzaniu wołane kilkanaście
 *  razy na sekundę, więc nie dało się przewinąć panelu do góry. */
function scrollStrip() {
  const box = $('#strip');
  const el = box.children[cur];
  if (!el || !box.clientWidth) return;
  const want = el.offsetLeft - (box.clientWidth - el.offsetWidth) / 2;
  const max = box.scrollWidth - box.clientWidth;
  box.scrollLeft = Math.max(0, Math.min(want, max > 0 ? max : 0));
}

function markStrip() {
  const box = $('#strip');
  const kids = box.children;
  for (let i = 0; i < kids.length; i++) kids[i].classList.toggle('on', i === cur);
  scrollStrip();
  info();
}

function renderStrip() {
  const box = $('#strip');
  box.innerHTML = '';
  AN.forEach((f, i) => {
    const d = document.createElement('div');
    d.className = 'fr' + (i === cur ? ' on' : '');
    const cv = document.createElement('canvas');
    drawThumb(cv, f.px);
    const lab = document.createElement('i');
    lab.textContent = f.ms;
    d.append(cv, lab);
    d.onclick = () => { stopPlay(false); cur = i; markStrip(); redraw(); };
    box.appendChild(d);
  });
  scrollStrip();
  info();
}

function touchFrame() {
  const cv = $('#strip').children[cur];
  if (cv) {
    drawThumb(cv.querySelector('canvas'), frame().px);
    cv.querySelector('i').textContent = frame().ms;
  }
  info();
}

// ---- malowanie -------------------------------------------------------------
// Kolor pociągnięcia ustalamy RAZ, przy dotknięciu pierwszego piksela. Gdyby
// każdy piksel przełączał się osobno, przeciągnięcie palcem po już
// pomalowanym fragmencie zgasiłoby go w połowie ruchu.
let strokeColor = 0;

function pickStroke(el) {
  if (!el || !el.classList.contains('px')) return brush;
  const same = frame().px[+el.dataset.i] === brush;
  return ($('#tog').checked && same && brush !== 0) ? 0 : brush;
}

function paintCell(el, color) {
  if (!el || !el.classList.contains('px')) return;
  const i = +el.dataset.i;
  const px = frame().px;
  if (px[i] === color) return;
  px[i] = color;
  el.style.background = color ? hex(color) : '';
  touchFrame();
  liveSend();
}

const liveSend = debounce(() => {
  if ($('#live').checked) api('preview', { px: toHexStr(frame().px) });
}, 220);

let tool = 'brush';
$$('.tool').forEach((b) => b.onclick = () => {
  tool = b.dataset.tool;
  $$('.tool').forEach((x) => x.classList.toggle('on', x === b));
});

// Wypelnianie obszaru: zwykly rozlew po sasiadach. Na 63 pikselach to nic,
// ale i tak trzymamy kolejke zamiast rekurencji, zeby nie przepelnic stosu.
function floodFill(start) {
  const px = frame().px;
  const from = px[start];
  if (from === brush) return false;
  const q = [start];
  const seen = new Set([start]);
  while (q.length) {
    const i = q.pop();
    if (px[i] !== from) continue;
    px[i] = brush;
    const x = i % W, y = Math.floor(i / W);
    const nb = [];
    if (x > 0) nb.push(i - 1);
    if (x < W - 1) nb.push(i + 1);
    if (y > 0) nb.push(i - W);
    if (y < H - 1) nb.push(i + W);
    nb.forEach((j) => { if (!seen.has(j) && px[j] === from) { seen.add(j); q.push(j); } });
  }
  return true;
}

const grid = $('#pixgrid');
grid.addEventListener('pointerdown', (e) => {
  stopPlay(false);
  if (!e.target.classList || !e.target.classList.contains('px')) return;
  const i = +e.target.dataset.i;

  if (tool === 'pick') {
    const v = frame().px[i];
    brush = v;
    $('#brush').value = hex(v);
    markSwatches('#brushSw', hex(v));
    toast(v ? 'pobrany kolor ' + hex(v) : 'pobrany: czarny (gumka)');
    return;
  }
  if (tool === 'fill') {
    snapshot();
    if (floodFill(i)) { redraw(); touchFrame(); liveSend(); }
    return;
  }

  snapshot();
  painting = true;
  grid.setPointerCapture(e.pointerId);
  strokeColor = pickStroke(e.target);
  paintCell(e.target, strokeColor);
});
grid.addEventListener('pointermove', (e) => {
  if (!painting) return;
  paintCell(document.elementFromPoint(e.clientX, e.clientY), strokeColor);
});
grid.addEventListener('pointerup', () => { painting = false; });
grid.addEventListener('pointercancel', () => { painting = false; });

$('#brush').oninput = (e) => { brush = num(e.target.value); markSwatches('#brushSw', e.target.value); };
$('#tErase').onclick = () => { brush = 0; $('#brush').value = '#000000'; markSwatches('#brushSw', ''); toast('pędzel: gumka'); };
$('#tAll').onclick = () => { snapshot(); frame().px.fill(brush); afterEdit(); };
$('#tClear').onclick = () => { snapshot(); frame().px.fill(0); afterEdit(); };
$('#tCopy').onclick = () => {
  if (cur === 0) { toast('to pierwsza klatka'); return; }
  snapshot();
  AN[cur].px = AN[cur - 1].px.slice();
  afterEdit();
};
$('#onion').onchange = redraw;

// Przewijanie klatek tuż pod siatką - najwygodniejszy sposób sprawdzenia,
// jak animacja wygląda krok po kroku. Zawija się, bo animacja to pętla.
function gotoFrame(i) {
  if (AN.length < 2) return;
  stopPlay(false);
  cur = ((i % AN.length) + AN.length) % AN.length;
  markStrip();
  redraw();
  liveSend();
}
$('#fPrev').onclick = () => gotoFrame(cur - 1);
$('#fNext').onclick = () => gotoFrame(cur + 1);

// ---- efekty ----------------------------------------------------------------
/** Klatki, na które działa efekt - wg wyboru „Działaj na". */
function scopeFrames() {
  const mode = $('#scope').value;
  if (mode === 'all') return AN;
  if (mode === 'rest') return AN.slice(cur);
  return [frame()];
}

/** Przepuszcza każdy piksel wybranych klatek przez funkcję. */
function mapPixels(fn) {
  snapshot();
  scopeFrames().forEach((f) => {
    for (let i = 0; i < f.px.length; i++) f.px[i] = fn(f.px[i], i);
  });
  afterEdit();
}

/** Skalowanie jasności. Przy przyciemnianiu pilnujemy, żeby każda składowa
 *  naprawdę zeszła w dół: samo zaokrąglanie zacina się na małych wartościach
 *  (round(2 * 0.8) = 2), więc piksel zostawałby na zawsze ledwo zapalony. */
const scaleV = (v, k) => {
  if (k >= 1) return mk(R(v) * k, G(v) * k, B(v) * k);
  const d = (c) => {
    const n = Math.round(c * k);
    return (n >= c && c > 0) ? c - 1 : n;
  };
  return mk(d(R(v)), d(G(v)), d(B(v)));
};
const lumaV = (v) => 0.299 * R(v) + 0.587 * G(v) + 0.114 * B(v);

function satV(v, k) {
  const y = lumaV(v);
  return mk(y + (R(v) - y) * k, y + (G(v) - y) * k, y + (B(v) - y) * k);
}

function scopeName() {
  return { one: 'tej klatce', rest: 'klatkach od tej do końca', all: 'wszystkich klatkach' }[$('#scope').value];
}

$('#fxBr').oninput = (e) => { $('#fxOut').textContent = e.target.value + '%'; };
$('#fxApply').onclick = () => {
  const k = +$('#fxBr').value / 100;
  mapPixels((v) => scaleV(v, k));
  toast('jasność ' + $('#fxBr').value + '% na ' + scopeName());
};
$('#fxDark').onclick = () => { mapPixels((v) => scaleV(v, 0.8)); toast('ciemniej o 20%'); };
$('#fxLight').onclick = () => {
  // rozjaśnianie samego mnożenia nie ruszy czerni, więc dokładamy stały dodatek
  mapPixels((v) => (v ? mk(R(v) * 1.25 + 6, G(v) * 1.25 + 6, B(v) * 1.25 + 6) : 0));
  toast('jaśniej o 25%');
};

$$('[data-fx]').forEach((b) => b.onclick = () => {
  const t = b.dataset.fx;
  if (t === 'invert') { mapPixels((v) => mk(255 - R(v), 255 - G(v), 255 - B(v))); toast('negatyw'); }
  else if (t === 'gray') { mapPixels((v) => satV(v, 0)); toast('odbarwione'); }
  else if (t === 'sat') { mapPixels((v) => satV(v, 1.6)); toast('mocniejsze kolory'); }
  else if (t === 'contrast') {
    mapPixels((v) => mk((R(v) - 128) * 1.35 + 128, (G(v) - 128) * 1.35 + 128, (B(v) - 128) * 1.35 + 128));
    toast('większy kontrast');
  } else if (t === 'tint') {
    const c = brush;
    if (!c) { toast('wybierz kolor pędzla (nie gumkę)'); return; }
    // barwimy tylko to, co świeci - czerń ma zostać czernią
    mapPixels((v) => (v ? mk((R(v) + R(c)) / 2, (G(v) + G(c)) / 2, (B(v) + B(c)) / 2) : 0));
    toast('zabarwione kolorem pędzla');
  }
});

// ---- przekształcenia --------------------------------------------------------
function remapPixels(idxOf) {
  snapshot();
  scopeFrames().forEach((f) => {
    const src = f.px.slice();
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) f.px[y * W + x] = src[idxOf(x, y)];
    }
  });
  afterEdit();
}

const wrapX = (x) => ((x % W) + W) % W;
const wrapY = (y) => ((y % H) + H) % H;

$$('[data-mv]').forEach((b) => b.onclick = () => {
  const t = b.dataset.mv;
  if (t === 'up') remapPixels((x, y) => wrapY(y + 1) * W + x);
  else if (t === 'down') remapPixels((x, y) => wrapY(y - 1) * W + x);
  else if (t === 'left') remapPixels((x, y) => y * W + wrapX(x + 1));
  else if (t === 'right') remapPixels((x, y) => y * W + wrapX(x - 1));
  else if (t === 'mirh') remapPixels((x, y) => y * W + (W - 1 - x));
  else if (t === 'mirv') remapPixels((x, y) => (H - 1 - y) * W + x);
  else if (t === 'rot') remapPixels((x, y) => (H - 1 - y) * W + (W - 1 - x));
});

// ---- generowanie klatek -----------------------------------------------------
function genN() {
  const n = parseInt($('#genN').value, 10);
  return isNaN(n) ? 6 : Math.max(1, Math.min(20, n));
}

/** Ile klatek jeszcze się zmieści - limit pilnuje pamięci Pico. */
function room() { return limitFrames() - AN.length; }

function needRoom(n) {
  const free = room();
  if (free <= 0) {
    toast('masz już ' + limitFrames() + ' klatek — to maksimum');
    return 0;
  }
  if (n > free) toast('dołożyłem ' + free + ' klatek zamiast ' + n + ' (limit ' + limitFrames() + ')');
  return Math.min(n, free);
}

function insertAfter(list) {
  AN.splice(cur + 1, 0, ...list);
  cur += list.length;
}

const fadedFrame = (px, k, ms) => ({ px: px.map((v) => scaleV(v, k)), ms: ms });

$$('[data-gen]').forEach((b) => b.onclick = () => {
  const t = b.dataset.gen;
  const base = frame();

  if (t === 'reverse') {
    snapshot(); AN.reverse(); cur = AN.length - 1 - cur; afterEdit();
    toast('kolejność odwrócona'); return;
  }
  if (t === 'faster' || t === 'slower') {
    snapshot();
    const lo = ST && ST.limits ? ST.limits.ms_min : 40;
    const hi = ST && ST.limits ? ST.limits.ms_max : 10000;
    AN.forEach((f) => {
      f.ms = Math.max(lo, Math.min(hi, Math.round(t === 'faster' ? f.ms / 2 : f.ms * 2)));
    });
    afterEdit(); toast(t === 'faster' ? 'dwa razy szybciej' : 'dwa razy wolniej'); return;
  }
  if (t === 'pingpong') {
    const extra = AN.length - 2;
    if (extra < 1) { toast('potrzebne co najmniej 3 klatki'); return; }
    const n = needRoom(extra);
    if (!n) return;
    snapshot();
    const back = AN.slice(1, AN.length - 1).reverse().slice(0, n)
      .map((f) => ({ px: f.px.slice(), ms: f.ms }));
    AN.push(...back);
    afterEdit(); toast('animacja wraca do początku'); return;
  }

  const n = needRoom(genN());
  if (!n) return;
  snapshot();

  if (t === 'fadeout') {
    const list = [];
    for (let i = 1; i <= n; i++) list.push(fadedFrame(base.px, 1 - i / n, base.ms));
    insertAfter(list);
    toast('ściemnianie w ' + n + ' klatkach');

  } else if (t === 'fadein') {
    const list = [];
    for (let i = 0; i < n; i++) list.push(fadedFrame(base.px, i / n, base.ms));
    AN.splice(cur, 0, ...list);      // rozjaśnianie wchodzi PRZED klatką
    cur += list.length;
    toast('rozjaśnianie w ' + n + ' klatkach');

  } else if (t === 'cross') {
    const next = AN[cur + 1];
    if (!next) { UNDO.pop(); histBtns(); toast('to ostatnia klatka — nie ma do czego przenikać'); return; }
    const list = [];
    for (let i = 1; i <= n; i++) {
      const k = i / (n + 1);
      list.push({
        px: base.px.map((v, j) => {
          const w = next.px[j];
          return mk(R(v) + (R(w) - R(v)) * k, G(v) + (G(w) - G(v)) * k, B(v) + (B(w) - B(v)) * k);
        }),
        ms: base.ms,
      });
    }
    insertAfter(list);
    toast('przenikanie w ' + n + ' klatkach');

  } else if (t === 'blink') {
    const list = [];
    for (let i = 0; i < n; i++) {
      list.push(i % 2 === 0
        ? { px: new Array(W * H).fill(0), ms: base.ms }
        : { px: base.px.slice(), ms: base.ms });
    }
    insertAfter(list);
    toast('miganie: ' + n + ' klatek');

  } else if (t === 'move') {
    const d = $('#genDir').value;
    const list = [];
    let px = base.px.slice();
    for (let i = 0; i < n; i++) {
      const src = px.slice();
      px = new Array(W * H).fill(0);
      for (let y = 0; y < H; y++) {
        for (let x = 0; x < W; x++) {
          const sx = d === 'left' ? wrapX(x + 1) : d === 'right' ? wrapX(x - 1) : x;
          const sy = d === 'up' ? wrapY(y + 1) : d === 'down' ? wrapY(y - 1) : y;
          px[y * W + x] = src[sy * W + sx];
        }
      }
      list.push({ px: px.slice(), ms: base.ms });
    }
    insertAfter(list);
    toast('przesuwanie: ' + n + ' klatek');
  }
  afterEdit();
});

// ---- operacje na klatkach --------------------------------------------------
function limitFrames() { return ST && ST.limits ? ST.limits.frames : 40; }

$('#fAdd').onclick = () => {
  if (AN.length >= limitFrames()) { toast('maksymalnie ' + limitFrames() + ' klatek'); return; }
  stopPlay(false); snapshot();
  AN.splice(cur + 1, 0, { px: new Array(W * H).fill(0), ms: frame().ms });
  cur++;
  renderStrip(); redraw();
};
$('#fDup').onclick = () => {
  if (AN.length >= limitFrames()) { toast('maksymalnie ' + limitFrames() + ' klatek'); return; }
  stopPlay(false); snapshot();
  AN.splice(cur + 1, 0, { px: frame().px.slice(), ms: frame().ms });
  cur++;
  renderStrip(); redraw();
};
$('#fDel').onclick = () => {
  if (AN.length <= 1) { toast('musi zostać przynajmniej jedna klatka'); return; }
  stopPlay(false); snapshot();
  AN.splice(cur, 1);
  if (cur >= AN.length) cur = AN.length - 1;
  renderStrip(); redraw();
};
$('#fLeft').onclick = () => {
  if (cur === 0) return;
  stopPlay(false);
  [AN[cur - 1], AN[cur]] = [AN[cur], AN[cur - 1]];
  cur--;
  renderStrip(); redraw();
};
$('#fRight').onclick = () => {
  if (cur >= AN.length - 1) return;
  stopPlay(false);
  [AN[cur + 1], AN[cur]] = [AN[cur], AN[cur + 1]];
  cur++;
  renderStrip(); redraw();
};
$('#fMs').onchange = (e) => {
  const lo = ST && ST.limits ? ST.limits.ms_min : 40;
  const hi = ST && ST.limits ? ST.limits.ms_max : 10000;
  let v = parseInt(e.target.value, 10);
  if (isNaN(v)) v = 200;
  v = Math.max(lo, Math.min(hi, v));
  frame().ms = v;
  e.target.value = v;
  touchFrame();
};
$('#fWipe').onclick = () => {
  if (AN.length === 1 && frame().px.every((v) => !v)) { toast('nie ma czego usuwać'); return; }
  if (!confirm('Usunąć wszystkie ' + AN.length + ' klatek i zacząć od pustej?')) return;
  stopPlay(false);
  snapshot();
  AN = [blankFrame()];
  cur = 0;
  renderStrip();
  redraw();
  liveSend();
  toast('wyczyszczone — cofnij, jeśli to pomyłka');
};

$('#fMsAll').onclick = () => {
  snapshot();
  const v = frame().ms;
  AN.forEach((f) => { f.ms = v; });
  renderStrip();
  toast('wszystkie klatki po ' + v + ' ms');
};

// ---- podgląd: siatka i lampka grają to samo --------------------------------
// Zapamiętujemy, na czym stanęliśmy przed podglądem: klatkę w edytorze i tryb
// lampki. Stop przywraca jedno i drugie, więc podgląd niczego nie gubi.
let playPrev = null;

function playLabel(txt) {
  $('#play').textContent = txt;
  $('#playTop').textContent = txt;
}

function stopPlay(restore) {
  if (!playing) return;
  playing = false;
  clearTimeout(playT);
  playLabel('▶ Podgląd');
  const prev = playPrev;
  playPrev = null;
  if (!restore || !prev) return;      // przerwane rysowaniem - zostajemy gdzie jesteśmy

  cur = Math.min(prev.cur, AN.length - 1);
  markStrip();
  redraw();
  if (!prev.lamp) return;           // lampka nie brala udzialu - nie ma czego cofac
  if (prev.anim && prev.anim.indexOf('px:*') !== 0) {
    // lampka grała normalny tryb - wracamy do niego
    api('anim', { id: prev.anim }).then(apply);
  } else {
    // lampka pokazywała malowaną klatkę - pokazujemy ją znowu
    api('preview', { px: toHexStr(frame().px) });
  }
}

function startPlay() {
  if (AN.length < 2) { toast('dodaj więcej klatek'); return; }
  // czy lampka bierze udzial, decydujemy RAZ na starcie - inaczej przelaczenie
  // checkboxa w trakcie zostawiloby lampke w stanie podgladu
  const onLamp = $('#playLamp').checked && $('#live').checked;
  playPrev = { cur: cur, anim: ST ? ST.anim : null, lamp: onLamp };
  playing = true;
  playLabel('■ Stop');
  if (onLamp) api('preview', { frames: payload() });

  const tick = () => {
    if (!playing) return;
    cur = (cur + 1) % AN.length;
    markStrip();                      // sam podświetlenie, bez przebudowy pasków
    redraw();
    playT = setTimeout(tick, frame().ms);
  };
  playT = setTimeout(tick, frame().ms);
}
const togglePlay = () => (playing ? stopPlay(true) : startPlay());
$('#play').onclick = togglePlay;
$('#playTop').onclick = togglePlay;

// ---- wysyłka i zapis -------------------------------------------------------
const payload = () => AN.map((f) => ({ px: toHexStr(f.px), ms: f.ms }));

$('#send').onclick = async () => {
  const r = await api('preview', { frames: payload() });
  toast(r.ok ? 'gra na lampce (nie zapisane)' : (r.err || 'nie udało się'));
};

$('#save').onclick = async () => {
  const name = $('#fname').value.trim();
  if (!name) { toast('podaj nazwę animacji'); return; }
  const r = await api('gallery/save', { name: name, frames: payload() });
  if (r.ok) {
    $('#fname').value = '';
    apply(r);
    loadGallery();
    toast('zapisane w galerii: „' + name + '"');
  } else toast(r.err || 'nie zapisano');
};

// =================================================================== GALERIA
// Miniatury sa ciezkie, wiec nie jada w /api/state odpytywanym co 8 s -
// dociagamy je raz, przy wejsciu w zakladkę i po każdej zmianie galerii.
let GAL = [];
async function loadGallery() {
  const r = await api('gallery');
  if (r.ok) { GAL = r.items || []; $('#galList').dataset.k = ''; renderGallery(); }
}

function renderGallery() {
  const box = $('#galList');
  const items = GAL;
  const want = items.map((e) => e.slug + ':' + e.n).join('|');
  if (box.dataset.k === want) return;
  box.dataset.k = want;
  box.innerHTML = '';
  if (!items.length) {
    box.innerHTML = '<p class="hint">Pusto. Narysuj coś w Edytorze i zapisz.</p>';
    return;
  }
  items.forEach((e) => {
    const row = document.createElement('div');
    row.className = 'fitem gitem';
    const cv = document.createElement('canvas');
    drawThumb(cv, fromHexStr(e.thumb || ''));
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerHTML = '<b>' + esc(e.name) + '</b><span class="rssi">'
      + e.n + (e.n === 1 ? ' klatka' : e.n < 5 ? ' klatki' : ' klatek') + '</span>';

    const show = document.createElement('button');
    show.textContent = 'pokaż';
    show.onclick = async () => apply(await api('anim', { id: 'px:' + e.slug }));

    const edit = document.createElement('button');
    edit.textContent = 'edytuj';
    edit.onclick = async () => {
      const r = await api('gallery/get', { slug: e.slug });
      if (!r.ok) { toast(r.err || 'nie wczytano'); return; }
      stopPlay(false);
      AN = r.frames.map((f) => ({ px: fromHexStr(f.px), ms: f.ms }));
      if (!AN.length) AN = [blankFrame()];
      cur = 0;
      UNDO = []; REDO = []; histBtns();
      $('#fname').value = r.name;
      renderStrip(); redraw();
      $$('.tab').find((t) => t.dataset.tab === 'edit').click();
      toast('wczytane do edytora');
    };

    const del = document.createElement('button');
    del.textContent = 'usuń';
    del.className = 'danger';
    del.onclick = async () => {
      if (!confirm('Usunąć animację „' + e.name + '"?')) return;
      apply(await api('gallery/del', { slug: e.slug }));
      loadGallery();
    };

    row.append(cv, meta, show, edit, del);
    box.appendChild(row);
  });
}

function renderSeq(st) {
  const box = $('#seqList');
  const want = st.anims.map((a) => a.id + (a.seq ? '1' : '0')).join('|');
  if (box.dataset.k === want) return;
  box.dataset.k = want;
  box.innerHTML = '';
  const inSeq = st.anims.filter((a) => a.seq).length;
  st.anims.forEach((a) => {
    const row = document.createElement('label');
    row.className = 'fitem seqrow';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = a.seq;
    cb.onchange = async () => {
      if (!cb.checked && inSeq <= 1) {
        cb.checked = true;
        toast('przynajmniej jeden tryb musi zostać w sekwencji');
        return;
      }
      apply(await api('seq', { id: a.id, on: cb.checked }));
    };
    const nm = document.createElement('span');
    nm.className = 'nm';
    nm.innerHTML = esc(a.label)
      + (a.own ? ' <span class="tagi">· własna</span>' : '');
    row.append(cb, nm);
    box.appendChild(row);
  });
}

// ------------------------------------------------------------------- adresy
function renderAddrs(st) {
  const box = $('#addrList');
  const rows = [];
  if (st.net.mode.indexOf('sta') === 0) {
    rows.push(['http://' + st.hostname + '.local/', 'nazwa hosta — bez rutera']);
    rows.push(['http://' + st.net.ip + '/', 'adres w domowej sieci']);
  }
  if (st.net.ap_ip) {
    rows.push(['http://' + st.net.ap_ip + '/',
               'sieć „' + st.ap_ssid + '", hasło ' + st.ap_pass]);
  }
  const want = rows.map((r) => r[0]).join('|');
  if (box.dataset.k === want) return;
  box.dataset.k = want;
  box.innerHTML = '';
  rows.forEach(([url, note]) => {
    const d = document.createElement('div');
    d.className = 'fitem';
    d.innerHTML = '<span class="nm"><a href="' + url + '">' + url + '</a><br>'
      + '<span class="rssi">' + esc(note) + '</span></span>';
    box.appendChild(d);
  });
}

// ---------------------------------------------------------------- ustawienia
$('#aoSave').onclick = async () => {
  apply(await api('settings', { auto_off: $('#ao').checked, auto_off_min: +$('#aoMin').value }));
  toast($('#ao').checked ? 'auto-wyłączanie po ' + $('#aoMin').value + ' min' : 'auto-wyłączanie wyłączone');
};
$('#geoSave').onclick = async () => {
  apply(await api('settings', {
    origin: $('#origin').value,
    rows: $('#rows').value === '1',
    serpentine: $('#snake').checked,
  }));
  toast('geometria zapisana');
};
$('#calib').onclick = async () => apply(await api('anim', { id: 'kalibracja' }));

// --- kreator geometrii: pyta o to, co widać na ramce, i sam liczy ustawienia
const WIZ = { origin: null, rows: null };
const rawSet = (leds) => api('rawtest', { leds: leds });

function wizBox(krok, pytanie, opts) {
  const box = $('#wizard');
  box.innerHTML = '<div class="krok">' + krok + '</div><p>' + pytanie + '</p>';
  const d = document.createElement('div');
  d.className = 'opts';
  opts.forEach(([label, fn]) => {
    const b = document.createElement('button');
    b.innerHTML = label;
    b.onclick = fn;
    d.appendChild(b);
  });
  box.appendChild(d);
}

async function wizStart() {
  await rawSet([{ i: 0, c: '#ffffff' }, { i: 1, c: '#0040ff' }, { i: 2, c: '#0040ff' }]);
  wizBox('Krok 1 z 3',
    'Na ramce świecą trzy diody: jedna <b>biała</b> i obok dwie <b>niebieskie</b>. '
    + 'W którym rogu jest biała?',
    [['lewy górny', () => wizCorner('TL')], ['prawy górny', () => wizCorner('TR')],
     ['lewy dolny', () => wizCorner('BL')], ['prawy dolny', () => wizCorner('BR')]]);
}

function wizCorner(o) {
  WIZ.origin = o;
  wizBox('Krok 2 z 3', 'W którą stronę biegną od białej te dwie niebieskie?',
    [['w poziomie →', () => wizDir(true)], ['w pionie ↓', () => wizDir(false)]]);
}

async function wizDir(rows) {
  WIZ.rows = rows;
  await rawSet([{ i: 0, c: '#ffffff' }, { i: rows ? W : H, c: '#0040ff' }]);
  const gdzie = rows ? 'z tej samej strony (lewo / prawo)' : 'na tym samym końcu (góra / dół)';
  wizBox('Krok 3 z 3',
    'Teraz świecą dwie diody. Czy niebieska jest ' + gdzie + ' co biała, czy naprzeciw?',
    [['tak, tam samo', () => wizDone(false)], ['nie, naprzeciw', () => wizDone(true)]]);
}

async function wizDone(snake) {
  await api('rawtest', { off: true });
  apply(await api('settings', { origin: WIZ.origin, rows: WIZ.rows, serpentine: snake }));
  await api('anim', { id: 'kalibracja' });
  wizBox('Sprawdzenie',
    'Gotowe. Na ramce powinien być teraz <b>biały piksel w lewym górnym rogu</b>, '
    + '<b>czerwona linia od niego w prawo</b> i <b>zielona w dół</b>. Zgadza się?',
    [['tak, działa', () => { $('#wizard').innerHTML = ''; toast('geometria ustawiona'); refresh(); }],
     ['nie, jeszcze raz', wizStart]]);
}
$('#wizStart').onclick = wizStart;
$('#netSave').onclick = async () => {
  const st = await api('settings', {
    hostname: $('#host').value,
    ap_always: $('#apAlways').checked,
    captive: $('#captive').checked,
  });
  apply(st);
  toast('zapisane — po restarcie panel pod ' + st.hostname + '.local');
};
$('#btnSave').onclick = async () => {
  apply(await api('settings', {
    btn_active_high: $('#btnLogic').value === '1',
    show_ip: $('#showIp').checked,
  }));
  toast('zapisane, logika przycisku zadziała po restarcie');
};
$('#logSave').onclick = async () => {
  apply(await api('settings', {
    log_file: $('#logFile').checked,
    wifi_powersave: $('#wifiPm').checked,
  }));
  toast('zapisane' + ($('#wifiPm').checked ? ' — oszczędzanie zadziała po restarcie' : ''));
};
$('#logShow').onclick = async () => {
  const r = await api('log');
  const box = $('#logBox');
  box.textContent = (r.text || '').trim() || '(log jest pusty)';
  box.scrollTop = box.scrollHeight;
};
$('#logClear').onclick = async () => {
  if (!confirm('Wyczyścić log?')) return;
  const r = await api('log/clear', {});
  $('#logBox').textContent = (r.text || '').trim();
  toast('log wyczyszczony');
};

$('#reboot').onclick = async () => {
  if (!confirm('Zrestartować lampkę?')) return;
  await api('reboot', {});
  toast('restart, panel wróci za chwilę');
  setTimeout(refresh, 9000);
};

// ---------------------------------------------------------------------- WiFi
$('#scan').onclick = async () => {
  const box = $('#netlist');
  box.innerHTML = '<p class="hint">skanuję…</p>';
  const r = await api('wifi/scan');
  box.dataset.k = '';
  box.innerHTML = '';
  if (!r.nets || !r.nets.length) {
    box.innerHTML = '<p class="hint">nic nie znalazłem</p>';
    return;
  }
  r.nets.forEach((n) => {
    const row = document.createElement('div');
    row.className = 'fitem';
    row.innerHTML = '<span class="nm">' + esc(n.ssid) + '</span><span class="rssi">' + n.rssi + ' dBm</span>';
    row.onclick = () => { $('#ssid').value = n.ssid; $('#pass').focus(); };
    box.appendChild(row);
  });
};
$('#wifiSave').onclick = async () => {
  const ssid = $('#ssid').value.trim();
  if (!ssid) { toast('podaj nazwę sieci'); return; }
  const cc = $('#country').value.trim().toUpperCase();
  if (cc && cc !== (ST && ST.country)) await api('settings', { country: cc });
  const r = await api('wifi', { ssid: ssid, pass: $('#pass').value });
  if (!r.ok) { toast(r.err || 'nie zapisano'); return; }
  toast('łączę się…');
  watchWifi();
};

// Podczas proby polaczenia odpytujemy czesciej, zeby od razu bylo widac wynik.
let wifiT = null;
function watchWifi() {
  clearInterval(wifiT);
  let n = 0;
  wifiT = setInterval(async () => {
    const st = await api('state');
    apply(st);
    if (++n > 40 || (st.ok && !st.net.trying)) {
      clearInterval(wifiT);
      if (st.ok && !st.net.trying) {
        toast(st.net.err ? 'nie udało się — patrz „Stan"' : 'połączona, adres ' + st.net.ip);
      }
    }
  }, 1500);
}
$('#forget').onclick = async () => {
  if (!confirm('Zapomnieć sieć WiFi? Lampka wróci do trybu AP.')) return;
  await api('wifi/forget', {});
  toast('zapomniane, restart');
};

// ------------------------------------------------------------------ start
// przelaczniki edytora pamietane w przegladarce
['tog', 'live', 'playLamp'].forEach((id) => {
  const el = $('#' + id);
  try {
    const v = localStorage.getItem('lampka.' + id);
    if (v !== null) el.checked = v === '1';
    el.addEventListener('change', () => localStorage.setItem('lampka.' + id, el.checked ? '1' : '0'));
  } catch (e) { /* prywatne okno - trudno, zostaja domyslne */ }
});

buildGrid();
AN = [blankFrame()];
renderStrip();
redraw();
histBtns();
markSwatches('#brushSw', '#ff0000');
$('#brush').value = '#ff0000';
refresh();
setInterval(() => { if (!painting && !playing && !document.hidden) refresh(); }, 8000);
