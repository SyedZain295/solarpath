// Solar Path EV — Phase 1 advisor (find, listings, home energy, dealer intake)

function evPayloadFromFindForm() {
  const kwp = parseFloat(document.getElementById('ev_kwp')?.value || '0');
  return {
    budget_eur: parseFloat(document.getElementById('ev_budget')?.value || '0'),
    weekly_km: parseFloat(document.getElementById('ev_weekly_km')?.value || '0'),
    long_trips_per_year: parseInt(document.getElementById('ev_long_trips')?.value || '0', 10),
    family_size: parseInt(document.getElementById('ev_family')?.value || '2', 10),
    boot_priority: document.getElementById('ev_boot')?.value || 'medium',
    owner_status: document.getElementById('ev_owner')?.value || 'owner',
    home_charging: document.getElementById('ev_home_charge')?.value || 'yes',
    has_pv: document.getElementById('ev_has_pv')?.checked || false,
    has_battery: document.getElementById('ev_has_battery')?.checked || false,
    has_wallbox: document.getElementById('ev_has_wallbox')?.checked || false,
    system_kwp: kwp > 0 ? kwp : 0,
    priority: document.getElementById('ev_priority')?.value || 'running_cost',
  };
}

function formatEur(n) {
  if (typeof formatCurrency === 'function') return formatCurrency(n);
  return `€${Number(n || 0).toLocaleString()}`;
}

function certBadge(cert) {
  if (!cert) return tr('evm.cert.none', 'No certificate on file');
  if (cert.status === 'uploaded') {
    const soh = cert.state_of_health_pct != null ? ` — ${cert.state_of_health_pct}% SoH` : '';
    const prov = cert.provider ? ` (${cert.provider})` : '';
    return tr('evm.cert.uploaded', 'Certificate uploaded') + soh + prov;
  }
  if (cert.status === 'test_available') return tr('evm.cert.test_available', 'Independent test available');
  return tr('evm.cert.none', 'No certificate on file');
}

function renderVehicleCard(v) {
  const fit = v.solar_path_fit || {};
  const cert = fit.battery_certificate_label || {};
  const demo = fit.is_demo_listing ? `<span class="evm-demo-badge">${tr('evm.demo_badge', 'Demo listing')}</span>` : '';
  const partner = v.listing_status === 'partner' ? `<span class="evm-partner-badge">${tr('evm.partner_badge', 'Partner listing')}</span>` : '';
  const featured = v.featured ? `<span class="evm-featured-badge">${tr('evm.featured', 'Featured')}</span>` : '';
  const reasons = (fit.match_reasons || []).slice(0, 3).map((r) => `<li>${r}</li>`).join('');
  const pvLine = fit.pv_coverage_label
    ? `<p class="evm-fit-line evm-fit-pv">${fit.pv_coverage_label}</p>`
    : '';
  const costPv = fit.annual_charging_cost_with_pv_eur != null
    ? `<div><span>${tr('evm.with_pv', 'With your PV')}</span><strong>${formatEur(fit.annual_charging_cost_with_pv_eur)}/${tr('evm.per_year', 'per year')}</strong></div>`
    : '';

  return `
    <article class="evm-vehicle-card ${fit.fit_score >= 65 ? 'evm-vehicle-card--strong' : ''}" data-slug="${v.slug}">
      <div class="evm-vehicle-top">
        ${demo}${partner}${featured}
        <span class="evm-fit-pill">${fit.fit_label || tr('evm.match_score', 'Solar Path fit')} · ${fit.fit_score || '—'}/100</span>
      </div>
      <h3>${v.make} ${v.model}</h3>
      <p class="evm-trim">${v.trim || ''} · ${v.year || ''} · ${v.location || ''}</p>
      <div class="evm-price">${formatEur(v.price_eur)}</div>
      <dl class="evm-spec-grid">
        <div><dt>${tr('evm.mileage', 'Mileage')}</dt><dd>${(v.mileage_km || 0).toLocaleString()} km</dd></div>
        <div><dt>${tr('evm.battery', 'Battery')}</dt><dd>${v.battery_kwh} kWh</dd></div>
        <div><dt>${tr('evm.winter_range', 'Winter range')}</dt><dd>${fit.winter_range_label || '—'}</dd></div>
        <div><dt>${tr('evm.dc_charge', 'DC fast charge')}</dt><dd>${v.dc_fast_charge_kw} kW</dd></div>
        <div><dt>${tr('evm.home_charge_time', 'Home charge (overnight)')}</dt><dd>~${fit.home_charging_hours || '—'} ${tr('evm.hours_per_night', 'h typical overnight')}</dd></div>
        <div><dt>${tr('evm.cert_status', 'Battery certificate')}</dt><dd>${certBadge(cert)}</dd></div>
        <div><dt>${tr('evm.warranty', 'Battery warranty')}</dt><dd>${fit.battery_warranty_label || '—'}</dd></div>
        <div><dt>${tr('evm.annual_cost', 'Est. annual charging')}</dt><dd>${formatEur(fit.annual_charging_cost_grid_eur)}/${tr('evm.per_year', 'per year')}</dd></div>
        ${costPv ? `<div><dt>${tr('evm.with_pv', 'With your PV')}</dt><dd>${formatEur(fit.annual_charging_cost_with_pv_eur)}/${tr('evm.per_year', 'per year')}</dd></div>` : ''}
      </dl>
      ${pvLine}
      ${fit.wallbox_recommended ? `<p class="evm-fit-line"><strong>${tr('evm.wallbox_rec', 'Wallbox recommended')}</strong> · ${fit.suggested_setup || ''}</p>` : ''}
      <p class="evm-fit-line"><strong>${tr('evm.household_kwh', 'Added household demand')}</strong>: ~${(fit.annual_charging_kwh_added || 0).toLocaleString()} kWh/${tr('evm.per_year', 'per year')}</p>
      ${reasons ? `<ul class="evm-match-reasons">${reasons}</ul>` : ''}
      <div class="evm-card-actions">
        <a href="/ev/bundle?vehicle=${encodeURIComponent(v.slug)}" class="btn btn-primary btn-sm">${tr('evm.bundle_cta_short', 'Build home-energy bundle')}</a>
        <a href="/ev/home-energy?vehicle=${encodeURIComponent(v.slug)}" class="btn btn-outline btn-sm">${tr('evm.view_energy', 'Home energy check')}</a>
        <button type="button" class="btn btn-outline btn-sm evm-lead-btn" data-slug="${v.slug}">${tr('evm.lead_cta', 'Get dealer contact')}</button>
      </div>
    </article>`;
}

function initEvFind() {
  const form = document.getElementById('evFindForm');
  const results = document.getElementById('evFindResults');
  if (!form) return;

  const params = new URLSearchParams(window.location.search);
  if (params.get('budget')) document.getElementById('ev_budget').value = params.get('budget');
  if (params.get('weekly_km')) document.getElementById('ev_weekly_km').value = params.get('weekly_km');
  if (params.get('kwp')) {
    document.getElementById('ev_has_pv').checked = true;
    document.getElementById('ev_kwp').value = params.get('kwp');
  }
  if (params.get('has_pv') === '1') document.getElementById('ev_has_pv').checked = true;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    results.classList.remove('hidden');
    results.innerHTML = `<p>${tr('suppliers.loading', 'Loading…')}</p>`;
    try {
      const resp = await fetch('/api/ev-match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(evPayloadFromFindForm()),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'failed');
      const recs = data.recommendations || [];
      if (!recs.length) {
        results.innerHTML = `<p>${tr('evm.no_matches', 'No matches')}</p>`;
        return;
      }
      results.innerHTML = `
        <div class="evm-results-head">
          <h2>${tr('evm.results_title', 'These EVs fit your life')}</h2>
          <p>${tr('evm.results_sub', '')}</p>
        </div>
        <div class="evm-vehicle-grid">${recs.map(renderVehicleCard).join('')}</div>
        <p class="form-hint">${data.disclaimer || ''}</p>`;
      wireLeadButtons(results);
    } catch {
      results.innerHTML = `<p class="text-red">${tr('suppliers.error', 'Error loading')}</p>`;
    }
  });
}

function initEvListings() {
  const grid = document.getElementById('evListingsGrid');
  const apply = document.getElementById('flt_apply');
  if (!grid) return;

  async function load() {
    grid.innerHTML = `<p>${grid.dataset.loading || 'Loading…'}</p>`;
    const q = new URLSearchParams({
      budget_max: document.getElementById('flt_budget')?.value || '',
      range_min: document.getElementById('flt_range')?.value || '',
      battery_health_min: document.getElementById('flt_soh')?.value || '',
      fast_charge_min: document.getElementById('flt_fast')?.value || '',
      certificate_only: document.getElementById('flt_cert')?.checked ? '1' : '',
      weekly_km: '290',
    });
    try {
      const resp = await fetch(`/api/ev-vehicles?${q}`);
      const data = await resp.json();
      const items = data.vehicles || [];
      grid.innerHTML = items.length
        ? items.map(renderVehicleCard).join('')
        : `<p>${tr('evm.no_matches', 'No matches')}</p>`;
      wireLeadButtons(grid);
    } catch {
      grid.innerHTML = `<p>${tr('suppliers.error', 'Error')}</p>`;
    }
  }

  apply?.addEventListener('click', load);
  load();
}

async function loadVehicleOptions(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  try {
    const resp = await fetch('/api/ev-vehicles');
    const data = await resp.json();
    (data.vehicles || []).forEach((v) => {
      const opt = document.createElement('option');
      opt.value = v.slug;
      opt.textContent = `${v.make} ${v.model}`;
      sel.appendChild(opt);
    });
    const params = new URLSearchParams(window.location.search);
    if (params.get('vehicle')) sel.value = params.get('vehicle');
  } catch { /* ignore */ }
}

function initEvHomeEnergy() {
  const form = document.getElementById('evEnergyForm');
  const results = document.getElementById('evEnergyResults');
  if (!form) return;
  loadVehicleOptions('ee_vehicle');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const kwp = parseFloat(document.getElementById('ee_kwp')?.value || '0');
    const payload = {
      weekly_km: parseFloat(document.getElementById('ee_weekly_km')?.value || '0'),
      home_charging: document.getElementById('ee_home_charge')?.value,
      has_pv: document.getElementById('ee_has_pv')?.checked,
      has_battery: document.getElementById('ee_has_battery')?.checked,
      has_wallbox: document.getElementById('ee_has_wallbox')?.checked,
      system_kwp: kwp > 0 ? kwp : 0,
      vehicle_slug: document.getElementById('ee_vehicle')?.value || '',
    };
    results.classList.remove('hidden');
    results.innerHTML = `<p>${tr('suppliers.loading', 'Loading…')}</p>`;
    try {
      const resp = await fetch('/api/ev-home-energy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      const items = (data.recommendations || []).map((item) => `
        <div class="evm-energy-item evm-energy-item--${item.priority}">
          <h3>${item.title}</h3>
          <p>${item.detail}</p>
        </div>`).join('');
      results.innerHTML = `
        <div class="evm-results-head">
          <h2>${tr('evm.energy_results', 'Recommendations')}</h2>
          <p>~${(data.annual_ev_kwh || 0).toLocaleString()} kWh/year EV charging · Grid ~${formatEur(data.grid_cost_annual_eur)}/yr${
            data.with_pv_cost_annual_eur != null ? ` · With PV ~${formatEur(data.with_pv_cost_annual_eur)}/yr` : ''
          }</p>
        </div>
        <div class="evm-energy-list">${items}</div>
        <p class="form-hint">${tr('evm.bundle_cta_line', 'Turn this into a full EV + wallbox + PV plan.')}</p>
        <div class="evm-bundle-cta-row">
          <a href="/ev/bundle?vehicle=${encodeURIComponent(document.getElementById('ee_vehicle')?.value || new URLSearchParams(window.location.search).get('vehicle') || '')}" class="btn btn-primary">${tr('evm.bundle_cta_short', 'Build home-energy bundle')}</a>
          <a href="/calculator" class="btn btn-outline">${tr('nav.get_started', 'Get Started')}</a>
        </div>`;
    } catch {
      results.innerHTML = `<p>${tr('suppliers.error', 'Error')}</p>`;
    }
  });

  if (new URLSearchParams(window.location.search).get('vehicle')) {
    setTimeout(() => form.requestSubmit(), 400);
  }
}

function initEvSell() {
  const form = document.getElementById('evSellForm');
  const ok = document.getElementById('evSellSuccess');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const resp = await fetch('/api/ev-dealer-intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: document.getElementById('dealer_name')?.value,
          email: document.getElementById('dealer_email')?.value,
          phone: document.getElementById('dealer_phone')?.value,
          location: document.getElementById('dealer_location')?.value,
        }),
      });
      if (!resp.ok) throw new Error('failed');
      form.classList.add('hidden');
      ok?.classList.remove('hidden');
    } catch {
      alert(tr('suppliers.error', 'Error'));
    }
  });
}

function wireLeadButtons(root) {
  root.querySelectorAll('.evm-lead-btn').forEach((btn) => {
    btn.addEventListener('click', () => openEvLeadModal(btn.dataset.slug));
  });
}

function ensureEvLeadModal() {
  if (document.getElementById('evLeadModal')) return;
  const wrap = document.createElement('div');
  wrap.id = 'evLeadModal';
  wrap.className = 'modal hidden';
  wrap.innerHTML = `
    <div class="modal-content glass-panel evm-lead-modal">
      <h2>${tr('evm.lead_modal_title', 'Contact dealer')}</h2>
      <p class="form-hint">${tr('evm.lead_modal_sub', 'Share your details — qualified leads go to the partner dealer.')}</p>
      <form id="evLeadForm">
        <input type="hidden" id="evLeadSlug" value="">
        <div class="form-group"><label>${tr('common.name', 'Name')} *</label><input type="text" id="evLeadName" required></div>
        <div class="form-group"><label>${tr('common.email', 'Email')} *</label><input type="email" id="evLeadEmail" required></div>
        <div class="form-row">
          <div class="form-group"><label>${tr('common.phone', 'Phone')}</label><input type="tel" id="evLeadPhone"></div>
          <div class="form-group"><label>${tr('calc.postcode', 'Postcode')}</label><input type="text" id="evLeadPostcode" maxlength="5"></div>
        </div>
        <div class="form-group"><label>${tr('evm.lead_message', 'Message')}</label><textarea id="evLeadMessage" rows="2"></textarea></div>
        <div class="evm-lead-actions-row">
          <button type="button" class="btn btn-outline" id="evLeadCancel">${tr('common.cancel', 'Cancel')}</button>
          <button type="submit" class="btn btn-primary">${tr('evm.lead_submit', 'Send to dealer')}</button>
        </div>
      </form>
      <p id="evLeadSuccess" class="success-message hidden"></p>
    </div>`;
  document.body.appendChild(wrap);
  document.getElementById('evLeadCancel')?.addEventListener('click', () => wrap.classList.add('hidden'));
  document.getElementById('evLeadForm')?.addEventListener('submit', submitEvLead);
}

function openEvLeadModal(slug) {
  ensureEvLeadModal();
  const modal = document.getElementById('evLeadModal');
  document.getElementById('evLeadSlug').value = slug;
  document.getElementById('evLeadSuccess')?.classList.add('hidden');
  document.getElementById('evLeadForm')?.classList.remove('hidden');
  modal.classList.remove('hidden');
}

async function submitEvLead(e) {
  e.preventDefault();
  const slug = document.getElementById('evLeadSlug').value;
  const profile = typeof evPayloadFromFindForm === 'function' ? evPayloadFromFindForm() : {};
  try {
    const resp = await fetch('/api/ev-buyer-lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vehicle_slug: slug,
        buyer_name: document.getElementById('evLeadName').value,
        buyer_email: document.getElementById('evLeadEmail').value,
        buyer_phone: document.getElementById('evLeadPhone').value,
        buyer_postcode: document.getElementById('evLeadPostcode').value,
        message: document.getElementById('evLeadMessage').value,
        buyer_profile: profile,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'failed');
    document.getElementById('evLeadForm')?.classList.add('hidden');
    const ok = document.getElementById('evLeadSuccess');
    if (ok) {
      ok.classList.remove('hidden');
      ok.textContent = data.message || tr('evm.lead_success', 'Thanks');
    }
  } catch (err) {
    alert(err.message || tr('suppliers.error', 'Error'));
  }
}
