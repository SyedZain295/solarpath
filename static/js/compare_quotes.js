// Side-by-side PV quote comparison with scoring

const CHECK_FIELDS = [
  { key: 'includes_installation', labelKey: 'compare.js.chk_installation', weight: 2 },
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
Gültig 30 Tage`;

let quoteCount = 0;

document.addEventListener('DOMContentLoaded', () => {
  addQuoteForm();
  addQuoteForm();
  document.getElementById('addQuoteBtn')?.addEventListener('click', () => {
    if (quoteCount < 4) addQuoteForm();
  });
  document.getElementById('compareBtn')?.addEventListener('click', runComparison);
  document.getElementById('parseQuoteBtn')?.addEventListener('click', parsePastedQuote);
  document.getElementById('loadSampleBtn')?.addEventListener('click', () => {
    const ta = document.getElementById('quotePaste');
    if (ta) ta.value = SAMPLE_QUOTE;
    parsePastedQuote();
  });
  document.getElementById('quoteFile')?.addEventListener('change', async (e) => {
    document.getElementById('parseMsg').textContent = tr('compare.js.upload_stub', 'Paste quote text for now.');
    e.target.value = '';
  });
});

async function parsePastedQuote() {
  const text = document.getElementById('quotePaste')?.value.trim();
  const msg = document.getElementById('parseMsg');
  if (!text) return;
  const resp = await fetch('/api/quotes/parse-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  const data = await resp.json();
  if (!resp.ok) { msg.textContent = data.error || 'Parse failed'; return; }
  if (quoteCount >= 4) addQuoteForm();
  const form = document.querySelector('.compare-quote-form:last-child');
  if (!form) return;
  const set = (n, v) => { const el = form.querySelector(`[name="${n}"]`); if (el && v != null && v !== '') el.value = v; };
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
    if (el) el.checked = !!data[f.key];
  });
  msg.textContent = tr('compare.js.parsed', 'Parsed ({conf} confidence) — verify before comparing.').replace('{conf}', data.confidence);
}

function addQuoteForm() {
  if (quoteCount >= 4) return;
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
    const checks = {};
    CHECK_FIELDS.forEach(f => { checks[f.key] = g(f.key)?.checked || false; });
    const completeness = CHECK_FIELDS.reduce((s, f) => s + (checks[f.key] ? f.weight : 0), 0);
    const maxCompleteness = CHECK_FIELDS.reduce((s, f) => s + f.weight, 0);
    const production = parseFloat(g('production_kwh')?.value) || null;
    const costPerKwh = production && total ? Math.round(total / (production * 20)) : null;
    return {
      installer: g('installer')?.value.trim() || '—',
      total_eur: total,
      kwp,
      cost_per_kwp: kwp > 0 ? Math.round(total / kwp) : null,
      production_kwh: production,
      cost_per_kwh_lifetime: costPerKwh,
      panel_count: parseInt(g('panel_count')?.value, 10) || null,
      panel_wp: parseFloat(g('panel_wp')?.value) || null,
      panels: g('panels')?.value.trim() || '—',
      inverter: g('inverter')?.value.trim() || '—',
      inverter_kw: parseFloat(g('inverter_kw')?.value) || null,
      battery_kwh: parseFloat(g('battery_kwh')?.value) || 0,
      warranty_years: parseInt(g('warranty_years')?.value, 10) || null,
      validity_days: parseInt(g('validity_days')?.value, 10) || null,
      checks,
      completeness_pct: Math.round(completeness / maxCompleteness * 100),
      missing: CHECK_FIELDS.filter(f => !checks[f.key]).map(f => tr(f.labelKey, f.key)),
      notes: g('notes')?.value.trim() || '',
    };
  }).filter(q => q.total_eur > 0 || q.installer !== '—');
}

function scoreQuotes(quotes) {
  const cpk = quotes.map(q => q.cost_per_kwp).filter(Boolean);
  const minCpk = cpk.length ? Math.min(...cpk) : null;
  return quotes.map(q => {
    let score = 50;
    if (q.cost_per_kwp && minCpk) score += Math.max(0, 30 - Math.round((q.cost_per_kwp - minCpk) / minCpk * 100));
    score += Math.round(q.completeness_pct * 0.2);
    if (q.production_kwh && q.kwp) score += 5;
    if (q.warranty_years >= 20) score += 5;
    return { ...q, value_score: Math.min(100, Math.round(score)) };
  });
}

function runComparison() {
  const quotes = scoreQuotes(collectQuotes());
  const out = document.getElementById('compareResults');
  if (!quotes.length) {
    out.innerHTML = `<p class="form-error">${tr('compare.js.need_price', 'Enter at least one quote.')}</p>`;
    out.classList.remove('hidden');
    return;
  }

  const bestCpk = quotes.reduce((a, b) => (a.cost_per_kwp && (!b.cost_per_kwp || a.cost_per_kwp < b.cost_per_kwp)) ? a : b, quotes[0]);
  const bestScore = quotes.reduce((a, b) => (a.value_score > b.value_score) ? a : b, quotes[0]);

  const cards = quotes.map((q, i) => `
    <article class="quote-summary-card ${q === bestScore ? 'best-value' : ''}">
      <h4>${tr('compare.js.quote_n', 'Quote')} ${i + 1}: ${esc(q.installer)}</h4>
      <div class="quote-summary-stats">
        <span><strong>${formatCurrency(q.total_eur)}</strong> ${tr('compare.js.total_cost', 'total')}</span>
        <span>${q.cost_per_kwp ? formatCurrency(q.cost_per_kwp) + '/kWp' : '—'}</span>
        <span>${tr('compare.js.value_score', 'Value')}: <strong>${q.value_score}/100</strong></span>
        <span>${tr('compare.js.complete', 'Complete')}: ${q.completeness_pct}%</span>
      </div>
      ${q === bestCpk && q.cost_per_kwp ? `<span class="quote-badge">${tr('compare.js.lowest_cpk', 'Lowest €/kWp')}</span>` : ''}
      ${q.missing.length ? `<p class="form-hint warn">${tr('compare.js.missing', 'Missing')}: ${q.missing.join(', ')}</p>` : ''}
    </article>
  `).join('');

  const highlight = (rowKey, val, q) => {
    if (rowKey === 'cost_per_kwp' && q.cost_per_kwp === bestCpk.cost_per_kwp) return `class="cell-best"`;
    if (rowKey === 'value_score' && q.value_score === bestScore.value_score) return `class="cell-best"`;
    return '';
  };

  const rows = [
    ['installer', tr('compare.js.installer', 'Installer'), ...quotes.map(q => q.installer)],
    ['total', tr('compare.js.total_cost', 'Total'), ...quotes.map(q => formatCurrency(q.total_eur))],
    ['cost_per_kwp', tr('compare.js.cost_per_kwp', '€/kWp'), ...quotes.map(q => q.cost_per_kwp ? formatCurrency(q.cost_per_kwp) : '—')],
    ['value_score', tr('compare.js.value_score', 'Value score'), ...quotes.map(q => `${q.value_score}/100`)],
    ['kwp', tr('compare.js.system_kwp', 'kWp'), ...quotes.map(q => q.kwp || '—')],
    ['panel_count', tr('compare.js.panel_count', 'Panels'), ...quotes.map(q => q.panel_count ? `${q.panel_count}× ${q.panel_wp || '?'} Wp` : '—')],
    ['panels', tr('compare.js.panels', 'Panel model'), ...quotes.map(q => q.panels)],
    ['inverter', tr('compare.js.inverter', 'Inverter'), ...quotes.map(q => q.inverter_kw ? `${q.inverter} (${q.inverter_kw} kW)` : q.inverter)],
    ['battery', tr('compare.js.battery', 'Battery'), ...quotes.map(q => q.battery_kwh ? `${q.battery_kwh} kWh` : tr('compare.js.none', 'None'))],
    ['production', tr('compare.js.production_yr', 'Production/yr'), ...quotes.map(q => q.production_kwh ? `${q.production_kwh.toLocaleString()} kWh` : '—')],
    ['warranty', tr('compare.js.warranty', 'Warranty'), ...quotes.map(q => q.warranty_years ? `${q.warranty_years} ${tr('compare.js.years_abbr', 'yr')}` : '—')],
    ['validity', tr('compare.js.validity', 'Valid days'), ...quotes.map(q => q.validity_days || '—')],
    ...CHECK_FIELDS.map(f => [f.key, tr(f.labelKey, f.key), ...quotes.map(q => q.checks[f.key] ? '✓' : '✗')]),
    ['missing', tr('compare.js.likely_missing', 'Missing'), ...quotes.map(q => q.missing.length ? q.missing.join(', ') : '—')],
    ['notes', tr('compare.js.notes', 'Notes'), ...quotes.map(q => q.notes || '—')],
  ];

  out.innerHTML = `
    <h2 class="section-title">${tr('compare.js.title', 'Comparison')}</h2>
    <div class="quote-summary-grid">${cards}</div>
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead><tr><th>${tr('compare.js.item', 'Item')}</th>${quotes.map((_, i) => `<th>${tr('compare.js.quote_n', 'Quote')} ${i + 1}</th>`).join('')}</tr></thead>
        <tbody>${rows.map(r => {
          const rowKey = r[0];
          return `<tr>${r.slice(1).map((c, i) => {
            const attr = i > 0 ? highlight(rowKey, c, quotes[i - 1]) : '';
            return i === 0 ? `<th>${c}</th>` : `<td ${attr}>${esc(String(c))}</td>`;
          }).join('')}</tr>`;
        }).join('')}</tbody>
      </table>
    </div>
    <p class="form-hint">${tr('compare.js.disclaimer', '')}</p>
  `;
  out.classList.remove('hidden');
}

function formatCurrency(n) {
  const lang = document.documentElement.lang === 'de' ? 'de-DE' : 'en-IE';
  return new Intl.NumberFormat(lang, { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
}

function esc(text) {
  return String(text ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
