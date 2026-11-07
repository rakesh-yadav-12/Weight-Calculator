/* This file only reads the inputs and talks to the server.
   Every calculation happens in Python (see app.py -> calc_weight). */

const g = id => document.getElementById(id);
const fmt = (n, d) => Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const rowsBox = g('wc-rows');
const tpl = g('wc-row-tpl');
const clean = v => v.replace(/,/g, '.').replace(/[^0-9.]/g, '').replace(/^(\d*\.\d*)\./, '$1');
const digits = v => v.replace(/\D/g, '');

function setRes(el, text, empty) {
  el.textContent = text;
  el.classList.toggle('empty', !!empty);
}

/* Picture follows the pipe type of the pipe you are working on. */
function setHero(mode) {
  const hollow = mode === 'hollow';
  g('art-round').classList.toggle('off', hollow);
  g('art-hollow').classList.toggle('off', !hollow);
  g('hero-cap').textContent = hollow ? 'Hollow Section' : 'Round Pipe';
}

/* Table columns and headings follow the selected pipe type(s). */
function updateView() {
  const modes = new Set([...rowsBox.querySelectorAll('.f-mode')].map(m => m.value));
  const view = modes.size > 1 ? 'mixed' : (modes.has('hollow') ? 'hollow' : 'round');
  g('wc-tbl').dataset.view = view;
  g('h-a').textContent = view === 'round' ? 'OD (mm) *' : view === 'hollow' ? 'Side A (mm) *' : 'OD / Side A (mm) *';
  g('h-b').textContent = view === 'hollow' ? 'Side B (mm) *' : 'Side B (mm)';
}

function updateGrand() {
  let sum = 0, pcs = 0;
  rowsBox.querySelectorAll('.wc-data').forEach(r => { sum += r._total || 0; pcs += r._pcs || 0; });
  g('wc-grand').textContent = fmt(sum, 2);
  g('wc-gpcs').textContent = fmt(pcs, 0) + (pcs === 1 ? ' pipe' : ' pipes');
}

function addRow(focus, after) {
  const row = tpl.content.firstElementChild.cloneNode(true);
  const q = s => row.querySelector(s);
  row._seq = 0; row._timer = 0; row._total = 0; row._pcs = 0;

  const reset = (msg) => {
    row._total = 0; row._pcs = 0;
    setRes(q('.r-eq'), '—', true); setRes(q('.r-kgm'), '—', true); setRes(q('.r-wpp'), '—', true); setRes(q('.r-tot'), '—', true);
    q('.wc-msg').textContent = msg || '';
    updateGrand();
  };

  const applyMode = () => {
    const hollow = q('.f-mode').value === 'hollow';
    row.classList.toggle('is-round', !hollow);
    q('.t-a').textContent = hollow ? 'Side A (mm)' : 'OD (mm)';
    q('.f-a').placeholder = hollow ? 'e.g. 40' : 'e.g. 60';
    const b = q('.f-b');
    b.disabled = !hollow;
    if (!hollow) b.value = '';
    updateView();
  };

  const calc = async () => {
    const mySeq = ++row._seq;
    const mode = q('.f-mode').value;
    const a = q('.f-a').value;
    let r;
    try {
      const res = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, od: a, a, b: q('.f-b').value, t: q('.f-t').value, length: q('.f-l').value, nos: q('.f-n').value })
      });
      r = await res.json();
    } catch (e) {
      if (mySeq === row._seq) reset('Could not reach the server - please try again.');
      return;
    }
    if (mySeq !== row._seq) return;
    const showEq = () => {
      if (mode === 'hollow' && r.equivalent_od) setRes(q('.r-eq'), fmt(r.equivalent_od, 2));
      else setRes(q('.r-eq'), '\u2014', true);
    };
    if (!r.ok) { reset(/^Enter/.test(r.message) ? '' : r.message); showEq(); return; }

    const hasTot = r.total_weight !== null && r.total_weight !== undefined;
    row._total = hasTot ? Number(r.total_weight) : 0;
    row._pcs = hasTot ? (parseInt(q('.f-n').value, 10) || 0) : 0;
    showEq();
    setRes(q('.r-kgm'), fmt(r.kg_per_metre, 3));
    if (r.weight_per_pipe !== null && r.weight_per_pipe !== undefined) setRes(q('.r-wpp'), fmt(r.weight_per_pipe, 2));
    else setRes(q('.r-wpp'), '—', true);
    if (hasTot) setRes(q('.r-tot'), fmt(r.total_weight, 2));
    else setRes(q('.r-tot'), '—', true);
    q('.wc-msg').textContent = '';
    updateGrand();
  };

  const live = () => { clearTimeout(row._timer); row._timer = setTimeout(calc, 120); };

  row.querySelectorAll('input:not([type=hidden])').forEach(i => {
    i.addEventListener('input', () => {
      const v = i.classList.contains('f-n') ? digits(i.value) : clean(i.value);
      if (v !== i.value) i.value = v;
      live();
    });
    i.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); calc(); } });
  });
  row.addEventListener('focusin', () => setHero(q('.f-mode').value));
  row.querySelectorAll('.wc-tog button').forEach(btn => btn.addEventListener('click', () => {
    q('.f-mode').value = btn.dataset.v;
    row.querySelectorAll('.wc-tog button').forEach(x => {
      const on = x === btn; x.classList.toggle('is-on', on); x.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    applyMode(); setHero(btn.dataset.v); calc();
  }));
  q('.b-add').addEventListener('click', () => addRow(true, row));
  q('.b-del').addEventListener('click', () => {
    row._seq++; row.remove();
    if (!rowsBox.children.length) addRow(false);
    const last = rowsBox.lastElementChild;
    setHero(last ? last.querySelector('.f-mode').value : 'round');
    updateView(); updateGrand();
  });

  if (after && after.parentNode === rowsBox) after.after(row); else rowsBox.appendChild(row);
  applyMode();
  setHero('round');
  if (focus) {
    try { q('.f-a').focus({ preventScroll: true }); } catch (e) {}
    row.scrollIntoView({ block: 'nearest' });
  }
  return row;
}

g('wc-clr').onclick = () => {
  rowsBox.querySelectorAll('.wc-data').forEach(r => { r._seq++; });
  rowsBox.replaceChildren();
  addRow(true);
  updateView(); updateGrand();
};

addRow(false);
updateGrand();
