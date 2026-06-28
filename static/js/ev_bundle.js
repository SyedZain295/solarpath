// Solar Path EV Phase 3 — guided EV + wallbox + PV bundle

const BUNDLE_STORAGE_KEY = 'solarpath_ev_bundle';

function bundleProfilePayload() {
  const kwp = parseFloat(document.getElementById('bdg_kwp')?.value || '0');
  return {
    budget_eur: parseFloat(document.getElementById('bdg_budget')?.value || '0'),
    weekly_km: parseFloat(document.getElementById('bdg_weekly_km')?.value || '0'),
    home_charging: document.getElementById('bdg_home_charge')?.value || 'yes',
    has_pv: document.getElementById('bdg_has_pv')?.checked || false,
    has_battery: document.getElementById('bdg_has_battery')?.checked || false,
    has_wallbox: document.getElementById('bdg_has_wallbox')?.checked || false,
    system_kwp: kwp > 0 ? kwp : 0,
    priority: 'running_cost',
  };
}

function setBundleStep(n) {
  document.querySelectorAll('.evm-bundle-panel').forEach((el) => el.classList.add('hidden'));
  document.getElementById(`bundleStep${n}`)?.classList.remove('hidden');
  document.querySelectorAll('.evm-step').forEach((el) => {
    const step = parseInt(el.dataset.step, 10);
    el.classList.toggle('evm-step--active', step === n);
    el.classList.toggle('evm-step--done', step < n);
  });
}

function saveBundleState(state) {
  try { localStorage.setItem(BUNDLE_STORAGE_KEY, JSON.stringify(state)); } catch { /* ignore */ }
}

function loadBundleState() {
  try {
    const raw = localStorage.getItem(BUNDLE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function prefillFromQuery() {
  const p = new URLSearchParams(window.location.search);
  if (p.get('budget')) document.getElementById('bdg_budget').value = p.get('budget');
  if (p.get('weekly_km')) document.getElementById('bdg_weekly_km').value = p.get('weekly_km');
  if (p.get('kwp')) {
    document.getElementById('bdg_kwp').value = p.get('kwp');
    document.getElementById('bdg_has_pv').checked = true;
  }
  if (p.get('has_pv') === '1') document.getElementById('bdg_has_pv').checked = true;
  if (p.get('has_wallbox') === '1') document.getElementById('bdg_has_wallbox').checked = true;
  return p.get('vehicle') || '';
}

function renderBundleVehiclePick(candidates, onPick) {
  const grid = document.getElementById('bundleVehicleGrid');
  if (!grid) return;
  if (!candidates.length) {
    grid.innerHTML = `<p>${tr('evm.no_matches', 'No matches')}</p>`;
    return;
  }
  grid.innerHTML = candidates.map((v) => {
    const fit = v.solar_path_fit || {};
    return `
      <article class="evm-vehicle-card evm-bundle-pick-card" data-slug="${v.slug}">
        <span class="evm-fit-pill">${fit.fit_label || ''} · ${fit.fit_score || '—'}/100</span>
        <h3>${v.make} ${v.model}</h3>
        <p class="evm-trim">${v.trim || ''} · ${formatEur(v.price_eur)}</p>
        <p class="evm-fit-line">${tr('evm.household_kwh', 'Added household demand')}: ~${(fit.annual_charging_kwh_added || 0).toLocaleString()} kWh/${tr('evm.per_year', 'per year')}</p>
        <button type="button" class="btn btn-primary btn-sm evm-pick-vehicle" data-slug="${v.slug}">${tr('evm.bundle_pick', 'Choose this EV')}</button>
      </article>`;
  }).join('');
  grid.querySelectorAll('.evm-pick-vehicle').forEach((btn) => {
    btn.addEventListener('click', () => onPick(btn.dataset.slug));
  });
}

function renderWallboxPv(data) {
  const wrap = document.getElementById('bundleWallboxPv');
  if (!wrap || !data) return;
  const wb = data.wallbox || {};
  const pv = data.pv || {};
  const rec = wb.recommended;
  const altHtml = (wb.alternatives || []).map((a) => `
    <label class="evm-wallbox-option">
      <input type="radio" name="wallbox_id" value="${a.id}" ${rec?.id === a.id ? 'checked' : ''}>
      <span><strong>${a.make} ${a.model}</strong> · ${a.ac_kw} kW · ${formatEur(a.installed_price_eur)}</span>
      <span class="form-hint">${a.notes || ''}</span>
    </label>`).join('');

  const recHtml = rec ? `
    <label class="evm-wallbox-option evm-wallbox-option--rec">
      <input type="radio" name="wallbox_id" value="${rec.id}" checked>
      <span><strong>${rec.make} ${rec.model}</strong> · ${rec.ac_kw} kW · ${formatEur(rec.installed_price_eur)}</span>
      <span class="form-hint">${wb.reason || rec.notes || ''}</span>
    </label>` : `<p>${tr('evm.bundle_no_wallbox', 'No wallbox needed')}</p>`;

  wrap.innerHTML = `
    <div class="evm-bundle-block">
      <h3>${tr('evm.bundle_wallbox_heading', 'Wallbox')}</h3>
      ${wb.keep_existing ? `<p class="form-hint">${wb.reason || ''}</p>` : ''}
      <div class="evm-wallbox-list">${recHtml}${altHtml}</div>
    </div>
    <div class="evm-bundle-block">
      <h3>${tr('evm.bundle_pv_heading', 'PV fit')}</h3>
      <p>${pv.reason || ''}</p>
      <ul class="evm-bundle-facts">
        ${pv.has_pv ? `<li>${tr('evm.bundle_current_kwp', 'Current')}: ${pv.current_kwp || 0} kWp</li>` : ''}
        <li>${tr('evm.bundle_target_kwp', 'Target')}: ${pv.target_total_kwp || pv.suggested_kwp || '—'} kWp</li>
        ${pv.add_kwp > 0 ? `<li>${tr('evm.bundle_add_kwp', 'Add')}: +${pv.add_kwp} kWp · ~${formatEur(pv.est_cost_eur)}</li>` : ''}
        <li>${tr('evm.bundle_ev_kwh', 'EV charging')}: ~${(pv.annual_ev_kwh || 0).toLocaleString()} kWh/${tr('evm.per_year', 'per year')}</li>
      </ul>
    </div>`;
}

function renderBundleSummary(data) {
  const wrap = document.getElementById('bundleSummary');
  const leadForm = document.getElementById('bundleLeadForm');
  if (!wrap || !data?.vehicle) return;
  const v = data.vehicle;
  const wb = data.wallbox || {};
  const pv = data.pv || {};
  const costs = data.costs || {};
  const ctas = data.ctas || {};
  const rec = wb.recommended;

  wrap.innerHTML = `
    <div class="evm-bundle-summary-grid">
      <article class="evm-bundle-summary-card">
        <h3>${tr('evm.bundle_summary_ev', 'Electric vehicle')}</h3>
        <p><strong>${v.make} ${v.model}</strong> ${v.trim ? `· ${v.trim}` : ''}</p>
        <p>${formatEur(v.price_eur)} · ${v.battery_kwh} kWh</p>
        <p class="form-hint">${v.solar_path_fit?.fit_label || ''}</p>
      </article>
      <article class="evm-bundle-summary-card">
        <h3>${tr('evm.bundle_summary_wallbox', 'Wallbox')}</h3>
        ${rec ? `<p><strong>${rec.make} ${rec.model}</strong></p><p>${formatEur(wb.install_cost_eur || rec.installed_price_eur)}</p>` : `<p>${tr('evm.bundle_existing_wallbox', 'Use existing wallbox')}</p>`}
      </article>
      <article class="evm-bundle-summary-card">
        <h3>${tr('evm.bundle_summary_pv', 'PV')}</h3>
        <p>${pv.reason || '—'}</p>
        ${pv.est_cost_eur ? `<p><strong>${formatEur(pv.est_cost_eur)}</strong> ${tr('evm.bundle_pv_est', 'est. add-on')}</p>` : ''}
      </article>
    </div>
    <div class="evm-bundle-totals">
      <p><strong>${tr('evm.bundle_total_upfront', 'Illustrative upfront')}</strong>: ${formatEur(costs.total_upfront_eur)}</p>
      <p class="form-hint">${tr('evm.bundle_charging_annual', 'Est. charging')}: ${formatEur(costs.charging_grid_annual_eur)}/${tr('evm.per_year', 'per year')} grid${
        costs.charging_with_pv_annual_eur != null ? ` · ${formatEur(costs.charging_with_pv_annual_eur)}/${tr('evm.per_year', 'per year')} ${tr('evm.with_pv', 'With your PV')}` : ''
      }</p>
    </div>
    <div class="evm-bundle-cta-row">
      <a href="${ctas.calculator_url || '/calculator'}" class="btn btn-outline">${tr('evm.bundle_cta_calc', 'Full PV sizing')}</a>
      <a href="${ctas.compare_quotes_url || '/compare-quotes'}" class="btn btn-outline">${tr('evm.bundle_cta_quotes', 'Compare installer quotes')}</a>
      <button type="button" class="btn btn-primary" id="bundleShowLead">${tr('evm.bundle_lead_btn', 'Send bundle to dealer')}</button>
    </div>
    <p class="form-hint">${data.disclaimer || ''}</p>`;

  leadForm?.classList.add('hidden');
  document.getElementById('bundleShowLead')?.addEventListener('click', () => {
    leadForm?.classList.remove('hidden');
    leadForm?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
}

async function fetchBundle(profile, vehicleSlug = '', wallboxId = '') {
  const resp = await fetch('/api/ev-bundle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...profile, vehicle_slug: vehicleSlug, wallbox_id: wallboxId }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || 'failed');
  return data;
}

function initEvBundle() {
  const state = loadBundleState();
  prefillFromQuery();

  document.getElementById('bundleProfileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const profile = bundleProfilePayload();
    const grid = document.getElementById('bundleVehicleGrid');
    grid.innerHTML = `<p>${tr('suppliers.loading', 'Loading…')}</p>`;
    setBundleStep(2);
    try {
      const data = await fetchBundle(profile);
      state.profile = profile;
      state.candidates = data.candidates || [];
      saveBundleState(state);
      renderBundleVehiclePick(state.candidates, async (slug) => {
        state.vehicle_slug = slug;
        saveBundleState(state);
        document.getElementById('bundleWallboxPv').innerHTML = `<p>${tr('suppliers.loading', 'Loading…')}</p>`;
        setBundleStep(3);
        const bundle = await fetchBundle(profile, slug);
        state.bundle = bundle;
        saveBundleState(state);
        renderWallboxPv(bundle);
      });
    } catch {
      grid.innerHTML = `<p class="text-red">${tr('suppliers.error', 'Error')}</p>`;
    }
  });

  document.getElementById('bundleBackTo1')?.addEventListener('click', () => setBundleStep(1));
  document.getElementById('bundleBackTo2')?.addEventListener('click', () => setBundleStep(2));
  document.getElementById('bundleBackTo3')?.addEventListener('click', () => setBundleStep(3));

  document.getElementById('bundleToSummary')?.addEventListener('click', async () => {
    const profile = state.profile || bundleProfilePayload();
    const slug = state.vehicle_slug;
    const wallboxId = document.querySelector('input[name="wallbox_id"]:checked')?.value || '';
    try {
      const bundle = await fetchBundle(profile, slug, wallboxId);
      state.bundle = bundle;
      saveBundleState(state);
      renderBundleSummary(bundle);
      setBundleStep(4);
    } catch {
      alert(tr('suppliers.error', 'Error'));
    }
  });

  document.getElementById('bundleLeadSubmit')?.addEventListener('click', async () => {
    const msg = document.getElementById('bundleLeadMsg');
    const slug = state.vehicle_slug;
    if (!slug) return;
    const profile = state.profile || {};
    const bundle = state.bundle || {};
    try {
      const resp = await fetch('/api/ev-buyer-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vehicle_slug: slug,
          buyer_name: document.getElementById('bundle_lead_name')?.value,
          buyer_email: document.getElementById('bundle_lead_email')?.value,
          buyer_phone: document.getElementById('bundle_lead_phone')?.value,
          buyer_postcode: document.getElementById('bundle_lead_postcode')?.value,
          message: document.getElementById('bundle_lead_message')?.value,
          buyer_profile: {
            ...profile,
            bundle_plan: {
              wallbox_id: document.querySelector('input[name="wallbox_id"]:checked')?.value,
              pv: bundle.pv,
              costs: bundle.costs,
            },
          },
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'failed');
      msg.textContent = data.message || tr('evm.lead_success', 'Thanks');
    } catch (err) {
      msg.textContent = err.message || tr('suppliers.error', 'Error');
    }
  });

  const preVehicle = new URLSearchParams(window.location.search).get('vehicle');
  if (preVehicle) {
    document.getElementById('bundleProfileForm')?.requestSubmit();
    setTimeout(async () => {
      const profile = bundleProfilePayload();
      state.profile = profile;
      state.vehicle_slug = preVehicle;
      const bundle = await fetchBundle(profile, preVehicle);
      state.bundle = bundle;
      saveBundleState(state);
      renderWallboxPv(bundle);
      setBundleStep(3);
    }, 800);
  }
}
