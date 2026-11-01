// Small stand-in for the Claude dashboard runtime, so the same panel code runs on a plain site.
// Reads data/site.json (written by scripts/atualizar.py) and filters the daily rows by the chosen period.
window.dash = (() => {
  const SOURCES = {
    profile: {file: 'profile'},
    followers_daily: {file: 'followers_daily'},
    daily: {file: 'daily', range: ['start', 'end']},
    daily_prev: {file: 'daily', range: ['pstart', 'pend']},
    moves: {file: 'daily', range: ['start', 'end']},
    media: {file: 'media'},
    gender: {file: 'gender'},
    age: {file: 'age'},
    cities: {file: 'cities'},
    ads_media: {file: 'ads_media'},
  };
  let raw = null, failed = false, refreshing = false, params = {}, cache = {};
  const calcs = {}, draws = {}, subs = [];

  const rowsFor = (id) => {
    const src = SOURCES[id];
    const rows = (raw && raw[src.file]) || [];
    if (!src.range) return rows;
    const [a, b] = src.range.map((k) => params[k]);
    if (!a || !b) return [];
    return rows.filter((r) => { const d = String(r.date).slice(0, 10); return d >= a && d <= b; });
  };

  const data = (id) => {
    if (cache[id]) return cache[id];
    let out;
    if (calcs[id]) {
      const ins = calcs[id].inputs.map(data);
      const bad = ins.find((d) => d.status !== 'ok');
      out = bad ? {status: bad.status, data: [], refreshing} : {status: 'ok', data: calcs[id].fn(...ins.map((d) => d.data)), refreshing};
    } else if (!SOURCES[id]) out = {status: 'missing', data: [], refreshing};
    else if (failed && !raw) out = {status: 'error', data: [], refreshing};
    else if (!raw) out = {status: 'loading', data: [], refreshing};
    else out = {status: 'ok', data: rowsFor(id), refreshing};
    out.meta = [];
    return (cache[id] = out);
  };

  const runDraw = (name) => document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => {
    try { draws[name](el); } catch (e) { console.error(name, e); }
  });
  const render = () => {
    cache = {};
    subs.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
    Object.keys(draws).forEach(runDraw);
  };

  const load = (bust) => fetch('data/site.json' + (bust ? '?t=' + Date.now() : ''), {cache: bust ? 'no-store' : 'default'})
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((j) => { raw = j; failed = false; })
    .catch(() => { failed = true; })
    .finally(() => { refreshing = false; render(); });

  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
  document.addEventListener('DOMContentLoaded', () => load(false));

  let refreshTimer;
  return {
    data,
    calc: (id, def) => { calcs[id] = def; },
    draw: (name, fn) => { if (fn) draws[name] = fn; else if (draws[name]) { cache = {}; runDraw(name); } },
    onData: (fn) => { subs.push(fn); try { fn(); } catch (e) { console.error(e); } },
    params: () => ({...params}),
    setParams: (p) => { params = {...params, ...p}; render(); },
    resetParams: () => { params = {}; render(); },
    refresh: () => {
      // Every source lives in one file, so many refresh calls become a single reload.
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => { refreshing = true; render(); load(true); }, 0);
    },
    setLink: () => {},
    colors: [],
  };
})();
