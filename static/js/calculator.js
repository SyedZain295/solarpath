document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('calculatorForm');
  const steps = document.querySelectorAll('.calc-step');
  const progressFill = document.getElementById('progressFill');
  const progressSteps = document.querySelectorAll('#progressSteps span');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const submitBtn = document.getElementById('submitBtn');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const housingType = document.getElementById('housing_type');
  const apartmentNotice = document.getElementById('apartmentNotice');

  let currentStep = 1;
  const totalSteps = steps.length;

  housingType?.addEventListener('change', () => {
    const apt = ['apartment_renter', 'apartment_owner'].includes(housingType.value);
    apartmentNotice?.classList.toggle('hidden', !apt);
  });

  function updateUI() {
    steps.forEach(s => s.classList.toggle('active', parseInt(s.dataset.step) === currentStep));
    progressFill.style.width = `${(currentStep / totalSteps) * 100}%`;
    progressSteps.forEach((s, i) => s.classList.toggle('active', i < currentStep));
    prevBtn.disabled = currentStep === 1;
    nextBtn.classList.toggle('hidden', currentStep === totalSteps);
    submitBtn.classList.toggle('hidden', currentStep !== totalSteps);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function validateStep() {
    if (currentStep === 1 && !form.querySelectorAll('input[name="goals"]:checked').length) {
      alert(tr('calc.js.select_goal', 'Please select at least one goal.')); return false;
    }
    if (currentStep === 3) {
      const plz = form.querySelector('#postcode')?.value.trim();
      const loc = form.querySelector('#location').value.trim();
      const lat = form.querySelector('#latitude').value;
      const lon = form.querySelector('#longitude').value;
      if (!plz && !loc && (!lat || !lon)) { alert(tr('calc.js.enter_location', 'Please enter a location.')); return false; }
    }
    if (currentStep === 4) {
      const bill = form.querySelector('#monthly_bill').value;
      const kwh = form.querySelector('#monthly_kwh').value;
      if (!bill && !kwh) { alert(tr('calc.js.enter_usage', 'Please enter bill or kWh.')); return false; }
    }
    return true;
  }

  nextBtn.addEventListener('click', () => {
    if (!validateStep()) return;
    if (currentStep < totalSteps) { currentStep++; updateUI(); }
  });

  prevBtn.addEventListener('click', () => {
    if (currentStep > 1) { currentStep--; updateUI(); }
  });

  function showCalcError(message) {
    [document.getElementById('calcError'), document.getElementById('calcErrorBottom')].forEach((el) => {
      if (!el) return;
      el.textContent = message;
      el.classList.remove('hidden');
    });
    if (!document.getElementById('calcError')) alert(message);
    (document.getElementById('calcErrorBottom') || document.getElementById('calcError'))
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearCalcError() {
    [document.getElementById('calcError'), document.getElementById('calcErrorBottom')].forEach((el) => {
      el?.classList.add('hidden');
    });
  }

  function setLoading(active) {
    loadingOverlay?.classList.toggle('hidden', !active);
    loadingOverlay?.setAttribute('aria-busy', active ? 'true' : 'false');
    [submitBtn, nextBtn, prevBtn].forEach(btn => { if (btn) btn.disabled = active; });
    if (active) {
      const msg = document.getElementById('loadingMessage');
      if (msg) msg.textContent = tr('calc.loading', 'Calculating your recommendation…');
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateStep()) return;
    clearCalcError();
    setLoading(true);

    const goals = [...form.querySelectorAll('input[name="goals"]:checked')].map(c => c.value);
    const intakeSlug = sessionStorage.getItem('intakeInstallerSlug') || '';
    const payload = {
      postcode: form.querySelector('#postcode')?.value.trim() || '',
      location_name: form.querySelector('#location').value.trim(),
      latitude: form.querySelector('#latitude').value || null,
      longitude: form.querySelector('#longitude').value || null,
      monthly_bill_eur: parseFloat(form.querySelector('#monthly_bill').value) || 0,
      monthly_kwh: parseFloat(form.querySelector('#monthly_kwh').value) || 0,
      electricity_price_ct: parseFloat(form.querySelector('#electricity_price').value) || 32,
      feed_in_type: form.querySelector('#feed_in_type').value,
      roof_type: form.querySelector('#roof_type').value,
      roof_area_m2: parseFloat(form.querySelector('#roof_area').value) || 0,
      budget_eur: parseFloat(form.querySelector('#budget').value) || 0,
      goals,
      housing_type: form.querySelector('#housing_type').value,
      owner_status: form.querySelector('#owner_status').value,
      shading: form.querySelector('#shading').value,
      has_heat_pump: form.querySelector('#has_heat_pump').checked,
      has_ev: form.querySelector('#has_ev').checked,
      has_electric_water_heater: form.querySelector('#has_electric_water_heater').checked,
      has_pool: form.querySelector('#has_pool').checked,
      has_roof_photos: form.querySelector('#has_roof_photos').checked,
      has_home_office: form.querySelector('#has_home_office')?.checked || false,
      has_ac: form.querySelector('#has_ac')?.checked || false,
      planned_ev: form.querySelector('#planned_ev')?.checked || false,
      high_daytime_use: form.querySelector('#high_daytime_use')?.checked || false,
      planned_extension: form.querySelector('#planned_extension')?.checked || false,
      budget_first_mode: form.querySelector('#budget_first_mode')?.checked || false,
      installation_timeframe: form.querySelector('#installation_timeframe').value,
      connect_meter: form.querySelector('#connect_meter').checked,
      battery_interest: form.querySelector('#battery_interest')?.value || 'unsure',
      financing_interest: form.querySelector('#financing_interest')?.value || 'no',
    };
    if (intakeSlug) payload.source_installer_slug = intakeSlug;

    const betaInvite = sessionStorage.getItem('betaInviteToken') || '';
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    if (betaInvite) headers['X-Beta-Invite'] = betaInvite;

    try {
      const msg = document.getElementById('loadingMessage');
      if (msg) msg.textContent = tr('calc.loading_pvgis', 'Fetching solar yield from PVGIS…');
      const slowTimer = setTimeout(() => {
        const hint = document.querySelector('.loading-hint');
        if (hint) hint.textContent = tr('calc.loading_slow', 'Still working… free hosting can take up to 60 seconds on first load.');
      }, 12000);
      const controller = new AbortController();
      const abortTimer = setTimeout(() => controller.abort(), 120000);
      const resp = await fetch('/api/calculate', {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        signal: controller.signal,
        body: JSON.stringify(payload),
      });
      clearTimeout(slowTimer);
      clearTimeout(abortTimer);
      const data = await parseJsonResponse(resp);
      if (!resp.ok) throw new Error(data.error || tr('calc.js.calc_failed', 'Calculation failed'));
      if (intakeSlug) data.source_installer_slug = intakeSlug;
      try {
        sessionStorage.setItem('solarRecommendation', JSON.stringify(data));
      } catch (storageErr) {
        throw new Error(tr('calc.js.storage_failed', 'Could not save results — try a normal browser window (not private mode).'));
      }
      window.location.href = '/results';
    } catch (err) {
      const message = err.name === 'AbortError'
        ? tr('calc.js.timeout', 'Request timed out — the server may be waking up. Wait 60 seconds and try again.')
        : err.message;
      showCalcError(tr('common.error_prefix', 'Error') + ': ' + message);
      setLoading(false);
    }
  });

  updateUI();
});

async function parseJsonResponse(resp) {
  const text = await resp.text();
  const ctype = resp.headers.get('content-type') || '';
  if (!ctype.includes('application/json')) {
    if (resp.status === 401) {
      throw new Error(tr('calc.js.beta_required', 'Beta access required — open the invite link first, then try again.'));
    }
    throw new Error(tr('calc.js.server_error', 'Server error ({status}). Please try again.').replace('{status}', resp.status));
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(resp.ok ? tr('calc.js.invalid_response', 'Invalid server response') : tr('calc.js.server_error', 'Server error ({status}). Please try again.').replace('{status}', resp.status));
  }
}
