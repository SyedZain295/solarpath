// Side-by-side PV quote comparison — server scoring + warning signs

const MAX_QUOTES = 3;

const CHECK_FIELDS = [
  { key: 'includes_installation', labelKey: 'compare.js.chk_installation', weight: 2 },
  { key: 'includes_mounting', labelKey: 'compare.js.chk_mounting', weight: 1 },
  { key: 'includes_scaffolding', labelKey: 'compare.js.chk_scaffolding', weight: 1 },
  { key: 'includes_grid_registration', labelKey: 'compare.js.chk_grid', weight: 2 },
  { key: 'includes_mastr', labelKey: 'compare.js.chk_mastr', weight: 2 },
  { key: 'includes_battery', labelKey: 'compare.js.chk_battery', weight: 1 },
  { key: 'includes_monitoring', labelKey: 'compare.js.chk_monitoring', weight: 1 },
  { key: 'includes_optimizer', labelKey: 'compare.js.chk_optimizer', weight: 1 },
  { key: 'includes_electrician', labelKey: 'compare.js.chk_electrician', weight: 1 },
  { key: 'includes_removal', labelKey: 'compare.js.chk_removal', weight: 1 },
];

const SAMPLE_QUOTE = `SolarTech München GmbH
Angebot Nr. 2026-1847
Photovoltaik Komplettanlage 8,4 kWp
Gesamtpreis: 18.450,00 EUR brutto
Module: 20× Trina Vertex 420 Wp
Wechselrichter: Fronius Primo GEN24 8.0 Plus
Speicher: 10,2 kWh BYD Battery-Box
Jahresertrag ca. 8.900 kWh
Garantie: 25 Jahre Module, 12 Jahre Wechselrichter
Enthalten: Montage, Gerüst, Netzanmeldung, MaStR, Monitoring
Gültig 30 Tage
---
BayerSolar GmbH
Angebot Nr. 9921
8,4 kWp PV-Anlage
Gesamtpreis: 15.200,00 EUR
Module: 20× JA Solar 420 Wp
Wechselrichter SMA Sunny Tripower 6.0 kW
Jahresertrag 8.500 kWh
Garantie: 12 Jahre Module
Montage inklusive
Gültig 7 Tage`;

let quoteCount = 0;

document.addEventListener('DOMContentLoaded', () => {
  addQuoteForm();
  addQuoteForm();
  document.getElementById('addQuoteBtn')?.addEventListener('click', () => {
    if (quoteCount < MAX_QUOTES) addQuoteForm();
  });
  document.getElementById('compareBtn')?.addEventListener('click', runComparison);
  document.getElementById('parseQuoteBtn')?.addEventListener('click', parsePastedQuote);
  document.getElementById('loadSampleBtn')?.addEventListener('click', () => {
    const ta = document.getElementById('quotePaste');
    if (ta) ta.value = SAMPLE_QUOTE;
    parsePastedQuote();
  });
  document.getElementById('quoteFile')?.addEventListener('change', handleFileUpload);
});

async function handleFileUpload(e) {
  const file = e.target.files?.[0];
  const msg = document.getElementById('parseMsg');
  e.target.value = '';
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  msg.textContent = tr('compare.js.parsing', 'Parsing…');
  const resp = await fetch('/api/quotes/parse-upload', { method: 'POST', body: fd });
  const data = await resp.json();
  if (!resp.ok) {
    msg.textContent = data.error || tr('compare.js.parse_fail', 'Parse failed');
    return;
  }
  applyParsedQuotes(data.quotes || []);
  msg.textContent = tr('compare.js.parsed_pdf', 'Extracted {n} quote(s) from PDF — verify before comparing.').replace('{n}', data.count || 0);
}

async function parsePastedQuote() {
  const text = document.getElementById('quotePaste')?.value.trim();
  const msg = document.getElementById('parseMsg');
  if (!text) return;
  msg.textContent = tr('compare.js.parsing', 'Parsing…');
  const resp = await fetch('/api/quotes/parse-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, multi: true }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    msg.textContent = data.error || tr('compare.js.parse_fail', 'Parse failed');
    return;
  }
  const quotes = data.quotes || [data];
  applyParsedQuotes(quotes);
  const conf = quotes.map(q => q.confidence).join(', ');
  msg.textContent = tr('compare.js.parsed_multi', 'Parsed {n} quote(s) ({conf}) — verify before comparing.')
    .replace('{n}', quotes.length)
    .replace('{conf}', conf);
}

function applyParsedQuotes(quotes) {
  ensureQuoteForms(quotes.length);
  const forms = [...document.querySelectorAll('.compare-quote-form')];
  quotes.slice(0, MAX_QUOTES).forEach((q, i) => fillFormFromParsed(forms[i], q));
}

function ensureQuoteForms(n) {
  while (quoteCount < n && quoteCount < MAX_QUOTES) addQuoteForm();
}

function fillFormFromParsed(form, data) {
  if (!form || !data) return;
  const set = (name, v) => {
    const el = form.querySelector(`[name="${name}"]`);
    if (el && v != null && v !== '') el.value = v;
  };
  set('installer', data.installer);
  set('total_eur', data.total_eur);
  set('kwp', data.kwp);
  set('production_kwh', data.production_kwh);
  set('panel_count', data.panel_count);
  set('panel_wp', data.panel_wp);
  set('panels', data.panels);
  set('inverter', data.inverter);
  set('inverter_kw', data.inverter_kw);
  set('battery_kwh', data.battery_kwh);
  set('warranty_years', data.warranty_years);
  set('validity_days', data.validity_days);
  set('notes', data.notes);
  CHECK_FIELDS.forEach(f => {
    const el = form.querySelector(`[name="${f.key}"]`);
    if (el) el.checked = !!(data[f.key] || (data.checks && data.checks[f.key]));
  });
  updateCostPerKwp(form);
}

function addQuoteForm() {
  if (quoteCount >= MAX_QUOTES) return;
  quoteCount++;
  const id = quoteCount;
  const wrap = document.createElement('div');
  wrap.className = 'compare-quote-form';
  wrap.dataset.quoteId = id;
  wrap.innerHTML = `
    <h3>${tr('compare.js.quote_n', 'Quote')} ${id}</h3>
    <div class="form-row">
      <div class="form-group"><label>${tr('compare.js.installer', 'Installer')}</label><input type="text" name="installer"></div>
      <div class="form-group"><label>${tr('compare.js.total', 'Total price')}</label><input type="number" name="total_eur" min="0" step="100"></div>
      <div class="form-group"><label>${tr('compare.js.validity', 'Valid (days)')}</label><input type="number" name="validity_days" min="0" step="1" placeholder="30"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>${tr('compare.js.kwp', 'kWp')}</label><input type="number" name="kwp" min="0" step="0.1"></div>
      <div class="form-group"><label>${tr('compare.js.production', 'Production')}</label><input type="number" name="production_kwh" min="0" placeholder="kWh/yr"></div>
      <div class="form-group"><label>${tr('compare.js.cost_per_kwp', '€/kWp')}</label><input type="text" name="cost_per_kwp_display" readonly class="readonly-field" placeholder="auto"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>${tr('compare.js.panel_count', 'Panel count')}</label><input type="number" name="panel_count" min="0" step="1"></div>
      <div class="form-group"><label>${tr('compare.js.panel_wp', 'Panel Wp each')}</label><input type="number" name="panel_wp" min="0" step="5" placeholder="420"></div>
      <div class="form-group"><label>${tr('compare.js.panels', 'Panel model')}</label><input type="text" name="panels"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>${tr('compare.js.inverter', 'Inverter')}</label><input type="text" name="inverter"></div>
      <div class="form-group"><label>${tr('compare.js.inverter_kw', 'Inverter kW')}</label><input type="number" name="inverter_kw" min="0" step="0.1"></div>
      <div class="form-group"><label>${tr('compare.js.battery', 'Battery')}</label><input type="number" name="battery_kwh" min="0" step="0.1" placeholder="0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>${tr('compare.js.warranty', 'Warranty')}</label><input type="number" name="warranty_years" min="0"></div>
    </div>
    <div class="register-checks compare-checks-grid">
      ${CHECK_FIELDS.map(f => `<label><input type="checkbox" name="${f.key}"> ${tr(f.labelKey, f.key)}</label>`).join('')}
    </div>
    <div class="form-group"><label>${tr('compare.js.notes', 'Notes')}</label><textarea name="notes" rows="2"></textarea></div>
  `;
  document.getElementById('quoteForms')?.appendChild(wrap);
  wrap.querySelectorAll('[name="total_eur"], [name="kwp"]').forEach(el => {
    el.addEventListener('input', () => updateCostPerKwp(wrap));
  });
  const addBtn = document.getElementById('addQuoteBtn');
  if (addBtn) addBtn.disabled = quoteCount >= MAX_QUOTES;
}

function updateCostPerKwp(form) {
  const total = parseFloat(form.querySelector('[name="total_eur"]')?.value) || 0;
  const kwp = parseFloat(form.querySelector('[name="kwp"]')?.value) || 0;
  const display = form.querySelector('[name="cost_per_kwp_display"]');
  if (display) display.value = kwp > 0 ? formatCurrency(Math.round(total / kwp)) : '';
}

function collectQuotes() {
  return [...document.querySelectorAll('.compare-quote-form')].map(form => {
    const g = (n) => form.querySelector(`[name="${n}"]`);
    const total = parseFloat(g('total_eur')?.value) || 0;
    const kwp = parseFloat(g('kwp')?.value) || 0;
    const row = {
      installer: g('installer')?.value.trim() || '—',
      total_eur: total,
      kwp: kwp || null,
      production_kwh: parseFloat(g('production_kwh')?.value) || null,
      panel_count: parseInt(g('panel_count')?.value, 10) || null,
      panel_wp: parseFloat(g('panel_wp')?.value) || null,
      panels: g('panels')?.value.trim() || '',
      inverter: g('inverter')?.value.trim() || '',
      inverter_kw: parseFloat(g('inverter_kw')?.value) || null,
      battery_kwh: parseFloat(g('battery_kwh')?.value) || 0,
      warranty_years: parseInt(g('warranty_years')?.value, 10) || null,
      validity_days: parseInt(g('validity_days')?.value, 10) || null,
      notes: g('notes')?.value.trim() || '',
    };
    CHECK_FIELDS.forEach(f => { row[f.key] = g(f.key)?.checked || false; });
    return row;
  }).filter(q => q.total_eur > 0 || (q.installer && q.installer !== '—'));
}

async function runComparison() {
  const out = document.getElementById('compareResults');
  const quotes = collectQuotes();
  if (!quotes.length) {
    out.innerHTML = `<p class="form-error">${tr('compare.js.need_price', 'Enter at least one quote.')}</p>`;
    out.classList.remove('hidden');
    return;
  }
  out.innerHTML = `<p class="form-hint">${tr('compare.js.comparing', 'Comparing…')}</p>`;
  out.classList.remove('hidden');
  const resp = await fetch('/api/quotes/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quotes }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    out.innerHTML = `<p class="form-error">${esc(data.error || tr('compare.js.compare_fail', 'Comparison failed'))}</p>`;
    return;
  }
  renderComparison(data);
}

function renderComparison(data) {
  const out = document.getElementById('compareResults');
  const quotes = data.quotes || [];
  const summary = data.summary || {};
  const bestIdx = summary.best_value_index ?? 0;
  const lowCpkIdx = summary.lowest_cpk_index ?? 0;

  const cards = quotes.map((q, i) => `
    <article class="quote-summary-card ${i === bestIdx ? 'best-value' : ''}">
      <h4>${tr('compare.js.quote_n', 'Quote')} ${i + 1}: ${esc(q.installer)}</h4>
      <div class="quote-summary-stats">
        <span><strong>${formatCurrency(q.total_eur)}</strong> ${tr('compare.js.total_cost', 'total')}</span>
        <span>${q.cost_per_kwp ? formatCurrency(q.cost_per_kwp) + '/kWp' : '—'}</span>
        <span>${tr('compare.js.value_score', 'Value')}: <strong>${q.value_score}/100</strong></span>
        <span>${tr('compare.js.complete', 'Complete')}: ${q.completeness_pct}%</span>
      </div>
      ${i === lowCpkIdx && q.cost_per_kwp ? `<span class="quote-badge">${tr('compare.js.lowest_cpk', 'Lowest €/kWp')}</span>` : ''}
      ${i === bestIdx ? `<span class="quote-badge quote-badge-value">${tr('compare.js.best_value', 'Best overall value')}</span>` : ''}
      ${renderWarnings(q.warnings)}
      ${q.missing?.length ? `<p class="form-hint warn">${tr('compare.js.missing', 'Missing')}: ${esc(q.missing.join(', '))}</p>` : ''}
    </article>
  `).join('');

  const summaryLine = quotes.length >= 2
    ? `<p class="compare-summary-line">${tr('compare.js.summary_line', 'Best value: {best} · Lowest €/kWp: {low} ({cpk})')
      .replace('{best}', esc(summary.best_value_installer || '—'))
      .replace('{low}', esc(summary.lowest_cpk_installer || '—'))
      .replace('{cpk}', summary.lowest_cpk ? formatCurrency(summary.lowest_cpk) + '/kWp' : '—')}</p>`
    : '';

  const rows = (data.rows || []).map(row => {
    const label = rowLabel(row.key, row.label);
    const cells = row.values.map((val, i) => {
      const q = quotes[i];
      let display = val;
      if (row.bool === true) display = val ? '✓' : '✗';
      else if (row.key === 'total_eur' && val) display = formatCurrency(val);
      else if (row.key === 'cost_per_kwp' && val) display = formatCurrency(val);
      else if (row.key === 'value_score' && val != null) display = `${val}/100`;
      else if (row.key === 'completeness_pct' && val != null) display = `${val}%`;
      else if (row.key === 'battery_kwh') display = val ? `${val} kWh` : tr('compare.js.none', 'None');
      else if (val == null || val === '') display = '—';
      const best = isBestCell(row, val, quotes, i);
      return `<td${best ? ' class="cell-best"' : ''}>${esc(String(display))}</td>`;
    });
    return `<tr><th>${esc(label)}</th>${cells.join('')}</tr>`;
  }).join('');

  out.innerHTML = `
    <h2 class="section-title">${tr('compare.js.title', 'Comparison')}</h2>
    ${summaryLine}
    <div class="quote-summary-grid">${cards}</div>
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead><tr><th>${tr('compare.js.item', 'Item')}</th>${quotes.map((_, i) => `<th>${tr('compare.js.quote_n', 'Quote')} ${i + 1}</th>`).join('')}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p class="form-hint">${esc(data.disclaimer || tr('compare.js.disclaimer', ''))}</p>
  `;
  out.classList.remove('hidden');
}

function rowLabel(key, fallback) {
  const map = {
    total_eur: tr('compare.js.total_cost', 'Total cost'),
    cost_per_kwp: tr('compare.js.cost_per_kwp', '€/kWp'),
    kwp: tr('compare.js.system_kwp', 'kWp'),
    panels: tr('compare.js.panels', 'Panel model'),
    inverter: tr('compare.js.inverter', 'Inverter'),
    battery_kwh: tr('compare.js.battery', 'Battery'),
    includes_mounting: tr('compare.js.chk_mounting', 'Mounting'),
    includes_electrician: tr('compare.js.chk_electrician', 'Electrical work'),
    includes_grid_registration: tr('compare.js.chk_grid', 'Grid registration'),
    includes_mastr: tr('compare.js.chk_mastr', 'MaStR'),
    warranty_years: tr('compare.js.warranty', 'Warranty'),
    completeness_pct: tr('compare.js.complete', 'Completeness'),
    value_score: tr('compare.js.value_score', 'Value score'),
    missing: tr('compare.js.likely_missing', 'Likely missing'),
  };
  return map[key] || fallback || key;
}

function isBestCell(row, val, quotes, idx) {
  if (!row.highlight || val == null) return false;
  const nums = row.values.map(v => (typeof v === 'number' ? v : null)).filter(v => v != null);
  if (!nums.length) return false;
  if (row.highlight === 'lowest') return val === Math.min(...nums);
  if (row.highlight === 'highest') return val === Math.max(...nums);
  return false;
}

function renderWarnings(warnings) {
  if (!warnings?.length) return '';
  const items = warnings.map(w => {
    const cls = w.level === 'high' ? 'quote-warn-high' : (w.level === 'medium' ? 'quote-warn-medium' : 'quote-warn-low');
    return `<li class="${cls}">${esc(w.message)}</li>`;
  }).join('');
  return `<div class="quote-warnings"><strong>${tr('compare.js.warnings', 'Warning signs')}</strong><ul>${items}</ul></div>`;
}

function formatCurrency(n) {
  const lang = document.documentElement.lang === 'de' ? 'de-DE' : 'en-IE';
  return new Intl.NumberFormat(lang, { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
}

function esc(text) {
  return String(text ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
