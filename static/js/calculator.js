document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('calculatorForm');
  if (!form) return;

  const steps = document.querySelectorAll('.calc-step');
  const progressFill = document.getElementById('progressFill');
  const progressSteps = document.querySelectorAll('#progressSteps span');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const submitBtn = document.getElementById('submitBtn');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const housingType = document.getElementById('housing_type');
  const apartmentNotice = document.getElementById('apartmentNotice');
  const submitBtnDefaultText = submitBtn?.textContent || '';

  let currentStep = 1;
  const totalSteps = steps.length || 7;
  let isSubmitting = false;

  const defaultInvite = window.BETA_INVITE_DEFAULT || '';
  if (defaultInvite) {
    try {
      if (!sessionStorage.getItem('betaInviteToken')) {
        sessionStorage.setItem('betaInviteToken', defaultInvite);
      }
    } catch (_) { /* private mode */ }
  }

  housingType?.addEventListener('change', () => {
    const apt = ['apartment_renter', 'apartment_owner'].includes(housingType.value);
    apartmentNotice?.classList.toggle('hidden', !apt);
  });

  function field(id) {
    return form.querySelector(`#${id}`);
  }

  function fieldVal(id) {
    return (field(id)?.value || '').trim();
  }

  function fieldChecked(id) {
    return Boolean(field(id)?.checked);
  }

  function updateUI() {
    steps.forEach((s) => s.classList.toggle('active', parseInt(s.dataset.step, 10) === currentStep));
    if (progressFill) progressFill.style.width = `${(currentStep / totalSteps) * 100}%`;
    progressSteps.forEach((s, i) => s.classList.toggle('active', i < currentStep));
    if (prevBtn) prevBtn.disabled = currentStep === 1;
    nextBtn?.classList.toggle('hidden', currentStep === totalSteps);
    submitBtn?.classList.toggle('hidden', currentStep !== totalSteps);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function validateStep(step = currentStep) {
    if (step === 1 && !form.querySelectorAll('input[name="goals"]:checked').length) {
      alert(tr('calc.js.select_goal', 'Please select at least one goal.'));
      return false;
    }
    if (step === 3) {
      const plz = fieldVal('postcode');
      const loc = fieldVal('location');
      const lat = fieldVal('latitude');
      const lon = fieldVal('longitude');
      if (!plz && !loc && (!lat || !lon)) {
        alert(tr('calc.js.enter_location', 'Please enter a location.'));
        return false;
      }
    }
    if (step === 4) {
      const bill = fieldVal('monthly_bill');
      const kwh = fieldVal('monthly_kwh');
      if (!bill && !kwh) {
        alert(tr('calc.js.enter_usage', 'Please enter bill or kWh.'));
        return false;
      }
    }
    return true;
  }

  function validateAllSteps() {
    const saved = currentStep;
    for (let step = 1; step <= totalSteps; step += 1) {
      if (!validateStep(step)) {
        currentStep = step;
        updateUI();
        return false;
      }
    }
    currentStep = totalSteps;
    updateUI();
    return true;
  }

  nextBtn?.addEventListener('click', () => {
    if (!validateStep()) return;
    if (currentStep < totalSteps) {
      currentStep += 1;
      updateUI();
    }
  });

  prevBtn?.addEventListener('click', () => {
    if (currentStep > 1) {
      currentStep -= 1;
      updateUI();
    }
  });

  function showCalcError(message) {
    [document.getElementById('calcError'), document.getElementById('calcErrorBottom')].forEach((el) => {
      if (!el) return;
      el.textContent = message;
      el.classList.remove('hidden');
    });
    if (!document.getElementById('calcError') && !document.getElementById('calcErrorBottom')) {
      alert(message);
    }
    (document.getElementById('calcErrorBottom') || document.getElementById('calcError'))
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearCalcError() {
    [document.getElementById('calcError'), document.getElementById('calcErrorBottom')].forEach((el) => {
      el?.classList.add('hidden');
    });
  }

  function setLoading(active) {
    if (loadingOverlay) {
      if (active && loadingOverlay.parentElement !== document.body) {
        document.body.appendChild(loadingOverlay);
      }
      loadingOverlay.classList.toggle('hidden', !active);
      loadingOverlay.setAttribute('aria-busy', active ? 'true' : 'false');
    }
    [submitBtn, nextBtn, prevBtn].forEach((btn) => {
      if (btn) btn.disabled = active;
    });
    if (submitBtn) {
      submitBtn.textContent = active
        ? tr('calc.loading', 'Calculating your recommendation…')
        : submitBtnDefaultText;
    }
    if (active) {
      const msg = document.getElementById('loadingMessage');
      if (msg) msg.textContent = tr('calc.loading', 'Calculating your recommendation…');
    }
  }

  function buildPayload() {
    const goals = [...form.querySelectorAll('input[name="goals"]:checked')].map((c) => c.value);
    return {
      postcode: fieldVal('postcode'),
      location_name: fieldVal('location'),
      latitude: fieldVal('latitude') || null,
      longitude: fieldVal('longitude') || null,
      monthly_bill_eur: parseFloat(fieldVal('monthly_bill')) || 0,
      monthly_kwh: parseFloat(fieldVal('monthly_kwh')) || 0,
      electricity_price_ct: parseFloat(fieldVal('electricity_price')) || 32,
      feed_in_type: field('feed_in_type')?.value || 'partial',
      roof_type: field('roof_type')?.value || 'pitched_south',
      roof_area_m2: parseFloat(fieldVal('roof_area')) || 0,
      budget_eur: parseFloat(fieldVal('budget')) || 0,
      goals: goals.length ? goals : ['lower_bill'],
      housing_type: field('housing_type')?.value || 'detached',
      owner_status: field('owner_status')?.value || 'owner',
      shading: field('shading')?.value || 'unknown',
      has_heat_pump: fieldChecked('has_heat_pump'),
      has_ev: fieldChecked('has_ev'),
      has_electric_water_heater: fieldChecked('has_electric_water_heater'),
      has_pool: fieldChecked('has_pool'),
      has_roof_photos: fieldChecked('has_roof_photos'),
      has_home_office: fieldChecked('has_home_office'),
      has_ac: fieldChecked('has_ac'),
      planned_ev: fieldChecked('planned_ev'),
      high_daytime_use: fieldChecked('high_daytime_use'),
      planned_extension: fieldChecked('planned_extension'),
      budget_first_mode: fieldChecked('budget_first_mode'),
      installation_timeframe: field('installation_timeframe')?.value || 'not_sure',
      connect_meter: fieldChecked('connect_meter'),
      battery_interest: field('battery_interest')?.value || 'unsure',
      financing_interest: field('financing_interest')?.value || 'no',
    };
  }

  async function runCalculation() {
    if (isSubmitting) return;
    if (!validateAllSteps()) return;

    isSubmitting = true;
    clearCalcError();
    setLoading(true);

    const intakeSlug = sessionStorage.getItem('intakeInstallerSlug') || '';
    const betaInvite = sessionStorage.getItem('betaInviteToken') || window.BETA_INVITE_DEFAULT || '';
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    if (betaInvite) headers['X-Beta-Invite'] = betaInvite;

    try {
      const payload = buildPayload();
      if (intakeSlug) payload.source_installer_slug = intakeSlug;

      const msg = document.getElementById('loadingMessage');
      if (msg) msg.textContent = tr('calc.loading_pvgis', 'Fetching solar yield from PVGIS…');
      const slowTimer = setTimeout(() => {
        const hint = document.querySelector('.loading-hint');
        if (hint) {
          hint.textContent = tr(
            'calc.loading_slow',
            'Still working… free hosting can take up to 60 seconds on first load.'
          );
        }
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
      } catch (_) {
        try {
          localStorage.setItem('solarRecommendation', JSON.stringify(data));
        } catch (storageErr) {
          throw new Error(
            tr(
              'calc.js.storage_failed',
              'Could not save results — try a normal browser window (not private mode).'
            )
          );
        }
      }
      window.location.href = '/results';
      return;
    } catch (err) {
      const message = err.name === 'AbortError'
        ? tr(
            'calc.js.timeout',
            'Request timed out — the server may be waking up. Wait 60 seconds and try again.'
          )
        : (err.message || tr('calc.js.calc_failed', 'Calculation failed'));
      showCalcError(tr('common.error_prefix', 'Error') + ': ' + message);
    } finally {
      isSubmitting = false;
      setLoading(false);
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    runCalculation();
  });

  submitBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    runCalculation();
  });

  updateUI();
});

async function parseJsonResponse(resp) {
  const text = await resp.text();
  const ctype = resp.headers.get('content-type') || '';
  if (!ctype.includes('application/json')) {
    if (resp.status === 401) {
      throw new Error(
        tr('calc.js.beta_required', 'Beta access required — open the invite link first, then try again.')
      );
    }
    throw new Error(
      tr('calc.js.server_error', 'Server error ({status}). Please try again.').replace('{status}', resp.status)
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(
      resp.ok
        ? tr('calc.js.invalid_response', 'Invalid server response')
        : tr('calc.js.server_error', 'Server error ({status}). Please try again.').replace('{status}', resp.status)
    );
  }
}
