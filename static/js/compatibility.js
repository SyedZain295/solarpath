let catalog = { panels: [], inverters: [], batteries: [], counts: {} };

document.addEventListener('DOMContentLoaded', async () => {
  const panelSel = document.getElementById('compat_panel');
  const invSel = document.getElementById('compat_inverter');
  const batSel = document.getElementById('compat_battery');
  const form = document.getElementById('compatForm');
  const kwpInput = document.getElementById('compat_kwp');
  const panelsInput = document.getElementById('compat_panels');

  if (window.COMPAT_CATALOG?.panels?.length) {
    catalog = window.COMPAT_CATALOG;
    updateCatalogStats();
    renderDropdowns();
  }

  try {
    const resp = await fetch('/api/catalog');
    if (resp.ok) {
      catalog = await resp.json();
      updateCatalogStats();
      renderDropdowns();
    } else if (!catalog.panels?.length) {
      showCatalogError(panelSel, invSel);
    }
  } catch {
    if (!catalog.panels?.length) showCatalogError(panelSel, invSel);
  }

  panelSel?.addEventListener('change', () => { updateSpecCards(); syncPanelCount(); });
  invSel?.addEventListener('change', () => { renderBatteryDropdown(); updateSpecCards(); });
  batSel?.addEventListener('change', updateSpecCards);
  kwpInput?.addEventListener('input', () => { panelsInput.value = ''; syncPanelCount(); });
  panelsInput?.addEventListener('input', syncKwpFromPanels);

  document.querySelectorAll('#kwpPresets .city-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#kwpPresets .city-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      kwpInput.value = btn.dataset.kwp;
      panelsInput.value = '';
      syncPanelCount();
      suggestInverterForSize(parseFloat(btn.dataset.kwp));
    });
  });

  document.getElementById('applyFilters')?.addEventListener('click', renderDropdowns);
  document.getElementById('clearFilters')?.addEventListener('click', () => {
    ['filter_min_wp', 'filter_min_ac', 'filter_min_kwh'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    renderDropdowns();
  });

  form?.addEventListener('submit', runCheck);
  updateSpecCards();
  syncPanelCount();
});

function updateCatalogStats() {
  const el = document.getElementById('compatCatalogStats');
  if (!el || !catalog.counts) return;
  const { panels = 0, inverters = 0, batteries = 0 } = catalog.counts;
  el.textContent = tr('compat.catalog_stats', '{panels} panels · {inverters} inverters · {batteries} batteries — 2–50 kWp')
    .replace('{panels}', panels)
    .replace('{inverters}', inverters)
    .replace('{batteries}', batteries);
}

function getFilters() {
  return {
    minWp: parseFloat(document.getElementById('filter_min_wp')?.value) || 0,
    minAc: parseFloat(document.getElementById('filter_min_ac')?.value) || 0,
    minKwh: parseFloat(document.getElementById('filter_min_kwh')?.value) || 0,
  };
}

function filteredPanels() {
  const { minWp } = getFilters();
  return catalog.panels.filter(p => !minWp || p.power_wp >= minWp);
}

function filteredInverters(kwp = null) {
  const { minAc } = getFilters();
  const targetKwp = kwp ?? parseFloat(document.getElementById('compat_kwp')?.value) || 10;
  return catalog.inverters.filter(i => {
    if (minAc && i.ac_power_kw < minAc) return false;
    if (targetKwp >= 15) {
      return i.dc_max_kw >= targetKwp * 0.95 && i.ac_power_kw >= targetKwp * 0.80;
    }
    return true;
  });
}

function batteriesForInverter(inverterId, minKwh = 0) {
  const inv = itemById('inverters', inverterId);
  const allowed = new Set(inv?.compatible_battery_ids || []);
  return catalog.batteries.filter(b => {
    if (minKwh && b.capacity_kwh < minKwh) return false;
    if (!inv?.hybrid) return false;
    if (allowed.size) return allowed.has(b.id);
    return true;
  });
}

function renderDropdowns() {
  const panels = filteredPanels();
  const kwp = parseFloat(document.getElementById('compat_kwp')?.value) || 10;
  const inverters = filteredInverters(kwp);

  fillSelect('compat_panel', panels, panels.find(p => p.power_wp >= 420)?.id || panels[0]?.id);
  const preferInv = inverters.find(i => i.ac_power_kw >= kwp * 0.85 && i.dc_max_kw >= kwp * 0.95)
    || inverters.find(i => i.ac_power_kw >= 8)
    || inverters[0];
  fillSelect('compat_inverter', inverters, preferInv?.id);
  renderBatteryDropdown();
  updateSpecCards();
  syncPanelCount();
}

function renderBatteryDropdown() {
  const { minKwh } = getFilters();
  const invId = document.getElementById('compat_inverter')?.value;
  const inv = itemById('inverters', invId);
  const prev = document.getElementById('compat_battery')?.value || '';
  const noBat = { id: '', label: tr('compat.no_battery', 'No battery') };

  let batteries = [];
  if (inv?.hybrid) {
    batteries = batteriesForInverter(invId, minKwh);
  }

  fillSelect('compat_battery', [noBat, ...batteries], prev && [...batteries, noBat].some(b => b.id === prev) ? prev : '');
}

function suggestInverterForSize(kwp) {
  const inverters = filteredInverters(kwp);
  const match = inverters.find(i => i.ac_power_kw >= kwp * 0.85 && i.dc_max_kw >= kwp * 0.95)
    || inverters[inverters.length - 1];
  if (match) {
    const sel = document.getElementById('compat_inverter');
    if (sel && [...sel.options].some(o => o.value === match.id)) {
      sel.value = match.id;
      renderBatteryDropdown();
      updateSpecCards();
    }
  }
}

function showCatalogError(panelSel, invSel) {
  const msg = '<option value="">Could not load product catalog</option>';
  if (panelSel && !panelSel.options.length) panelSel.innerHTML = msg;
  if (invSel && !invSel.options.length) invSel.innerHTML = msg;
}

function fillSelect(id, items, preferId) {
  const sel = document.getElementById(id);
  if (!sel || !items?.length) return;
  const prev = sel.value;
  sel.innerHTML = items.map(i => `<option value="${i.id}">${esc(i.label || i.id)}</option>`).join('');
  if (preferId && items.some(i => i.id === preferId)) sel.value = preferId;
  else if (prev && items.some(i => i.id === prev)) sel.value = prev;
}

function itemById(cat, id) {
  return catalog[cat]?.find(x => x.id === id);
}

function updateSpecCards() {
  const p = itemById('panels', document.getElementById('compat_panel')?.value);
  const i = itemById('inverters', document.getElementById('compat_inverter')?.value);
  const b = itemById('batteries', document.getElementById('compat_battery')?.value);

  setSpec('panelSpec', p, [
    ['Wp', p?.power_wp],
    [tr('compat.efficiency', 'Efficiency'), p?.efficiency_pct ? `${p.efficiency_pct}%` : null],
    ['Voc', p?.voc_v ? `${p.voc_v} V` : null],
    ['Isc', p?.isc_a ? `${p.isc_a} A` : null],
    [tr('compat.price', 'Price'), p?.price_eur ? `€${p.price_eur}` : null],
  ]);
  setSpec('inverterSpec', i, [
    [tr('compat.ac_kw', 'AC'), i?.ac_power_kw ? `${i.ac_power_kw} kW` : null],
    [tr('compat.dc_kw', 'DC max'), i?.dc_max_kw ? `${i.dc_max_kw} kW` : null],
    ['MPPT', i?.mppt_count],
    [tr('compat.hybrid_short', 'Hybrid'), i?.hybrid ? '✓' : '—'],
    [tr('compat.backup_short', 'Backup'), i?.backup_capable ? '✓' : '—'],
  ]);
  setSpec('batterySpec', b, b ? [
    [tr('compat.capacity', 'Capacity'), `${b.capacity_kwh} kWh`],
    [tr('compat.usable', 'Usable'), `${b.usable_kwh ?? b.capacity_kwh} kWh`],
    [tr('compat.max_power', 'Max power'), b.max_power_kw ? `${b.max_power_kw} kW` : null],
    [tr('compat.price', 'Price'), b.price_eur ? `€${b.price_eur}` : null],
  ] : []);
}

function setSpec(elId, item, rows) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!item) { el.innerHTML = ''; return; }
  el.innerHTML = `<div class="compat-spec-grid">${rows.filter(([, v]) => v != null && v !== '').map(([k, v]) =>
    `<span><strong>${k}</strong> ${v}</span>`).join('')}</div>`;
}

function syncPanelCount() {
  const kwp = parseFloat(document.getElementById('compat_kwp')?.value) || 0;
  const p = itemById('panels', document.getElementById('compat_panel')?.value);
  const panelsInput = document.getElementById('compat_panels');
  if (!p || !kwp || panelsInput?.value) return;
  const n = Math.ceil(kwp * 1000 / p.power_wp);
  panelsInput.placeholder = `${n} ${tr('compat.panels', 'panels')} @ ${p.power_wp} Wp`;
}

function syncKwpFromPanels() {
  const n = parseInt(document.getElementById('compat_panels')?.value, 10);
  const p = itemById('panels', document.getElementById('compat_panel')?.value);
  if (!n || !p) return;
  document.getElementById('compat_kwp').value = (n * p.power_wp / 1000).toFixed(2);
}

async function runCheck(e) {
  e.preventDefault();
  const out = document.getElementById('compatResults');
  out.classList.add('loading');
  const goals = document.getElementById('compat_backup')?.checked ? ['backup'] : [];
  const panelCount = parseInt(document.getElementById('compat_panels')?.value, 10);
  const panel = itemById('panels', document.getElementById('compat_panel')?.value);
  let systemKwp = parseFloat(document.getElementById('compat_kwp')?.value) || 5;
  if (panelCount > 0 && panel) systemKwp = panelCount * panel.power_wp / 1000;

  const body = {
    panel_id: document.getElementById('compat_panel').value,
    inverter_id: document.getElementById('compat_inverter').value,
    battery_id: document.getElementById('compat_battery').value || null,
    system_kwp: systemKwp,
    goals,
  };

  try {
    const resp = await fetch('/api/catalog/compatibility-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();

    const scorePct = data.checks?.length
      ? Math.round((data.passed_count / data.checks.length) * 100)
      : 0;

    const checks = (data.checks || []).map(c =>
      `<li class="compat-check ${c.passed ? 'passed' : 'failed'}">${c.passed ? '✓' : '✗'} <strong>${tr(c.label_key, c.id)}</strong> — ${c.detail}</li>`
    ).join('');

    let altHtml = '';
    if (!data.ok) {
      const altResp = await fetch('/api/catalog/alternatives', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const altData = await altResp.json();
      const alts = altData.alternatives || {};
      const catLabels = {
        inverters: tr('compat.inverter', 'Inverters'),
        batteries: tr('compat.battery', 'Batteries'),
        panels: tr('compat.panel', 'Panels'),
      };
      const sections = ['inverters', 'batteries', 'panels'].map(cat => {
        const items = alts[cat] || [];
        if (!items.length) return '';
        return `<h4>${catLabels[cat]}</h4><ul class="compat-alt-list">${items.map(i =>
          `<li>${esc(i.label)}${i.power_wp ? ` · ${i.power_wp} Wp` : ''}${i.ac_power_kw ? ` · ${i.ac_power_kw} kW AC` : ''}${i.capacity_kwh ? ` · ${i.capacity_kwh} kWh` : ''}${i.price_eur ? ` · €${i.price_eur}` : ''}</li>`
        ).join('')}</ul>`;
      }).join('');
      if (sections) altHtml = `<div class="compat-alternatives"><h3>${tr('compat.alternatives', 'Alternatives')}</h3>${sections}</div>`;
    }

    const nums = `
      <div class="compat-numbers-grid">
        <div class="compat-num-card"><span>${tr('compat.actual_kwp', 'System')}</span><strong>${data.system_kwp_actual} kWp</strong></div>
        <div class="compat-num-card"><span>${tr('compat.panels', 'Panels')}</span><strong>${data.num_panels} × ${data.panel_wp || panel?.power_wp || '—'} Wp</strong></div>
        <div class="compat-num-card"><span>DC/AC</span><strong>${data.dc_ac_ratio ?? '—'}</strong></div>
        <div class="compat-num-card"><span>${tr('compat.score', 'Score')}</span><strong>${scorePct}%</strong></div>
      </div>`;

    out.innerHTML = `
      <h2 class="section-title ${data.ok ? 'compat-pass' : 'compat-fail'}">${data.ok ? tr('compat.pass', 'Compatible') : tr('compat.fail', 'Issues found')}</h2>
      ${nums}
      <ul class="compat-checklist">${checks}</ul>
      ${altHtml}`;
    out.classList.remove('hidden');
  } finally {
    out.classList.remove('loading');
  }
}

function esc(text) {
  return String(text ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
