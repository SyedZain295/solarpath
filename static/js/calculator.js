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

  let currentStep = 0;
  let isSubmitting = false;

  const SITUATION_PRESETS = {
    new_pv: { goals: ['lower_bill'], has_existing_pv: false },
    pv_battery: { goals: ['lower_bill', 'backup'], has_existing_pv: true, battery_interest: 'yes' },
    pv_ev: { goals: ['lower_bill', 'ev_charging'], has_existing_pv: true },
    heat_pump: { goals: ['space_heating', 'lower_bill'], has_existing_pv: false },
    compare_quotes: { redirect: '/compare-quotes' },
    business_farm: { goals: ['business'], has_existing_pv: false },
  };

  const SECONDS_PER_STEP = 42;

  function selectedSituation() {
    const r = form.querySelector('input[name="situation"]:checked');
    return r ? r.value : '';
  }

  function applySituationPreset(situation) {
    const preset = SITUATION_PRESETS[situation];
    if (!preset) return true;
    if (preset.redirect) {
      window.location.href = preset.redirect;
      return false;
    }
    field('user_situation').value = situation;
    field('has_existing_pv').value = preset.has_existing_pv ? '1' : '0';
    form.querySelectorAll('input[name="goals"]').forEach((cb) => {
      cb.checked = (preset.goals || []).includes(cb.value);
    });
    if (preset.battery_interest && field('battery_interest')) {
      field('battery_interest').value = preset.battery_interest;
    }
    syncGoalSummary();
    syncEvProgressLabel();
    syncHpLoadCheckbox();
    return true;
  }

  function syncGoalSummary() {
    const el = document.getElementById('goalSelectionSummary');
    if (!el) return;
    const labels = [...form.querySelectorAll('input[name="goals"]:checked')].map((cb) => {
      const title = cb.closest('.goal-card')?.querySelector('.goal-title');
      return title ? title.textContent.trim() : cb.value;
    });
    if (!labels.length) {
      el.classList.add('hidden');
      el.textContent = '';
      return;
    }
    el.classList.remove('hidden');
    el.innerHTML = `<strong>${tr('calc.selected_goals', 'Selected')}:</strong> ${labels.join(' · ')}`;
  }

  function estimatedMinutesLeft(pos, totalSteps) {
    const remaining = Math.max(0, totalSteps - pos - 1);
    return Math.max(1, Math.ceil((remaining * SECONDS_PER_STEP) / 60));
  }
  function hasEvGoal() {
    return [...form.querySelectorAll('input[name="goals"]:checked')].some((c) => c.value === 'ev_charging');
  }

  function hasHeatGoal() {
    return [...form.querySelectorAll('input[name="goals"]:checked')].some((c) =>
      c.value === 'space_heating' || c.value === 'hot_water'
    );
  }

  function stepVisible(stepNum) {
    const el = form.querySelector(`.calc-step[data-step="${stepNum}"]`);
    if (!el) return false;
    const cond = el.dataset.conditional;
    if (cond === 'ev_charging') return hasEvGoal();
    if (cond === 'heat') return hasHeatGoal();
    return true;
  }

  function visibleStepNumbers() {
    return [...steps]
      .map((s) => parseInt(s.dataset.step, 10))
      .filter((n) => stepVisible(n))
      .sort((a, b) => a - b);
  }

  function syncEvProgressLabel() {
    document.querySelector('.progress-ev-step')?.classList.toggle('hidden', !hasEvGoal());
    document.querySelector('.progress-heat-step')?.classList.toggle('hidden', !hasHeatGoal());
  }

  function syncEvLoadCheckboxes() {
    const own = fieldVal('ev_ownership');
    const hasEv = field('has_ev');
    const plannedEv = field('planned_ev');
    if (!hasEv || !plannedEv) return;
    if (own === 'own') {
      hasEv.checked = true;
      plannedEv.checked = false;
    } else if (own === 'planning') {
      hasEv.checked = false;
      plannedEv.checked = true;
    }
  }

  function syncHpLoadCheckbox() {
    const status = fieldVal('hp_status');
    const hasHp = field('has_heat_pump');
    const wrap = document.querySelector('.hp-load-sync-wrap');
    if (!hasHp) return;
    if (status === 'have') {
      hasHp.checked = true;
    } else if (status === 'planning' || status === 'replacing_fossil') {
      hasHp.checked = false;
    }
    if (wrap) wrap.classList.toggle('hidden', hasHeatGoal());
  }

  form.querySelectorAll('input[name="goals"]').forEach((cb) => {
    cb.addEventListener('change', () => {
      syncGoalSummary();
      syncEvProgressLabel();
      syncHpLoadCheckbox();
      if (!hasEvGoal() && currentStep === 2) {
        currentStep = 1;
      }
      if (!hasHeatGoal() && currentStep === 3) {
        currentStep = hasEvGoal() ? 2 : 1;
      }
      updateUI();
    });
  });
  field('ev_ownership')?.addEventListener('change', syncEvLoadCheckboxes);
  field('hp_status')?.addEventListener('change', syncHpLoadCheckbox);

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

  const quickParams = new URLSearchParams(window.location.search);
  if (quickParams.get('quick') === '1') {
    const plz = quickParams.get('postcode');
    const kwh = quickParams.get('kwh');
    const roof = quickParams.get('roof');
    const goal = quickParams.get('goal');
    const owner = quickParams.get('owner');
    const roofType = quickParams.get('roof_type');
    if (plz && field('postcode')) field('postcode').value = plz;
    if (kwh && field('monthly_kwh')) field('monthly_kwh').value = kwh;
    if (roof && field('roof_area')) field('roof_area').value = roof;
    if (owner && field('owner_status')) field('owner_status').value = owner;
    if (roofType && field('roof_type')) field('roof_type').value = roofType;
    if (goal) {
      const goalCb = form.querySelector(`input[name="goals"][value="${goal}"]`);
      if (goalCb) goalCb.checked = true;
    }
    const newPv = form.querySelector('input[name="situation"][value="new_pv"]');
    if (newPv) newPv.checked = true;
    if (field('user_situation')) field('user_situation').value = 'new_pv';
    currentStep = 1;
    syncGoalSummary();
  }

  field('roof_photos')?.addEventListener('change', (e) => {
    if (e.target.files?.length && field('has_roof_photos')) {
      field('has_roof_photos').checked = true;
    }
  });

  function stepLabel(stepNum) {
    const el = form.querySelector(`.calc-step[data-step="${stepNum}"]`);
    return el?.dataset.stepLabel || '';
  }

  function updateUI() {
    const vis = visibleStepNumbers();
    const pos = Math.max(0, vis.indexOf(currentStep));
    const totalSteps = vis.length || 1;
    const pct = Math.round(((pos + 1) / totalSteps) * 100);

    steps.forEach((s) => {
      const n = parseInt(s.dataset.step, 10);
      s.classList.toggle('active', n === currentStep);
      s.classList.toggle('hidden', !stepVisible(n));
    });

    if (progressFill) progressFill.style.width = `${pct}%`;
    const progressBar = document.getElementById('progressBar');
    if (progressBar) progressBar.setAttribute('aria-valuenow', String(pct));

    const meta = document.getElementById('calcProgressMeta');
    if (meta) {
      const label = stepLabel(currentStep);
      const stepWord = tr('calc.js.step_of', 'Step {current} of {total}');
      const mins = estimatedMinutesLeft(pos, totalSteps);
      const timeLeft = tr('calc.js.time_left', 'About {min} min left').replace('{min}', String(mins));
      meta.innerHTML = stepWord
        .replace('{current}', `<strong>${pos + 1}</strong>`)
        .replace('{total}', `<strong>${totalSteps}</strong>`)
        + (label ? ` · ${label}` : '')
        + ` · ${timeLeft}`;
    }

    let progressIdx = 0;
    progressSteps.forEach((span) => {
      if (span.classList.contains('progress-ev-step') && !hasEvGoal()) {
        span.classList.add('hidden');
        return;
      }
      if (span.classList.contains('progress-heat-step') && !hasHeatGoal()) {
        span.classList.add('hidden');
        return;
      }
      span.classList.remove('hidden');
      span.classList.toggle('active', progressIdx === pos);
      span.classList.toggle('done', progressIdx < pos);
      progressIdx += 1;
    });

    syncEvProgressLabel();
    syncHpLoadCheckbox();
    if (prevBtn) prevBtn.disabled = pos <= 0;
    const last = vis[vis.length - 1];
    nextBtn?.classList.toggle('hidden', currentStep === last);
    submitBtn?.classList.toggle('hidden', currentStep !== last);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function validateStep(step = currentStep) {
    if (!stepVisible(step)) return true;
    if (step === 0 && !selectedSituation()) {
      alert(tr('calc.js.select_situation', 'Please select the option that best describes you.'));
      return false;
    }
    if (step === 1 && !form.querySelectorAll('input[name="goals"]:checked').length) {
      alert(tr('calc.js.select_goal', 'Please select at least one goal.'));
      return false;
    }
    if (step === 2 && hasEvGoal()) {
      if (!fieldVal('ev_ownership')) {
        alert(tr('calc.js.ev_ownership', 'Please say if you own an EV or are planning one.'));
        return false;
      }
      if (!fieldVal('ev_annual_km') || parseFloat(fieldVal('ev_annual_km')) <= 0) {
        alert(tr('calc.js.ev_km', 'Please enter your annual driving distance.'));
        return false;
      }
      if (!fieldVal('ev_home_charging') || !fieldVal('ev_park_home_daytime') || !fieldVal('ev_has_wallbox') || !fieldVal('ev_charging_priority')) {
        alert(tr('calc.js.ev_details', 'Please complete all EV charging questions.'));
        return false;
      }
      syncEvLoadCheckboxes();
    }
    if (step === 3 && hasHeatGoal()) {
      if (!fieldVal('hp_status') || !fieldVal('hp_type')) {
        alert(tr('calc.js.hp_status', 'Please complete heat pump status and type.'));
        return false;
      }
      const goals = [...form.querySelectorAll('input[name="goals"]:checked')].map((c) => c.value);
      if (goals.includes('space_heating')) {
        const area = parseFloat(fieldVal('hp_heated_area_m2')) || 0;
        const kwh = parseFloat(fieldVal('hp_annual_heat_kwh')) || 0;
        if (area <= 0 && kwh <= 0) {
          alert(tr('calc.js.hp_area', 'Enter heated floor area or annual heat electricity use.'));
          return false;
        }
      }
      if (!fieldVal('hp_daytime_heating') || !fieldVal('hp_priority')) {
        alert(tr('calc.js.hp_details', 'Please complete heating priority questions.'));
        return false;
      }
      syncHpLoadCheckbox();
    }
    if (step === 5) {
      const plz = fieldVal('postcode');
      const loc = fieldVal('location');
      const lat = fieldVal('latitude');
      const lon = fieldVal('longitude');
      if (!plz && !loc && (!lat || !lon)) {
        alert(tr('calc.js.enter_location', 'Please enter a location.'));
        return false;
      }
    }
    if (step === 6) {
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
    for (const step of visibleStepNumbers()) {
      if (!validateStep(step)) {
        currentStep = step;
        updateUI();
        return false;
      }
    }
    currentStep = visibleStepNumbers().slice(-1)[0] || saved;
    updateUI();
    return true;
  }

  function stepAfter(step) {
    const vis = visibleStepNumbers();
    const idx = vis.indexOf(step);
    return idx >= 0 && idx < vis.length - 1 ? vis[idx + 1] : step;
  }

  function stepBefore(step) {
    const vis = visibleStepNumbers();
    const idx = vis.indexOf(step);
    return idx > 0 ? vis[idx - 1] : step;
  }

  nextBtn?.addEventListener('click', () => {
    if (!validateStep()) return;
    if (currentStep === 0) {
      if (!applySituationPreset(selectedSituation())) return;
    }
    const vis = visibleStepNumbers();
    if (vis.indexOf(currentStep) < vis.length - 1) {
      currentStep = stepAfter(currentStep);
      updateUI();
    }
  });

  prevBtn?.addEventListener('click', () => {
    const vis = visibleStepNumbers();
    if (vis.indexOf(currentStep) > 0) {
      currentStep = stepBefore(currentStep);
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
      ev_ownership: fieldVal('ev_ownership'),
      ev_vehicle_model: fieldVal('ev_vehicle_model'),
      ev_annual_km: parseFloat(fieldVal('ev_annual_km')) || 0,
      ev_consumption_kwh_100km: parseFloat(fieldVal('ev_consumption_kwh_100km')) || 18,
      ev_home_charging: fieldVal('ev_home_charging'),
      ev_park_home_daytime: fieldVal('ev_park_home_daytime'),
      ev_has_wallbox: fieldVal('ev_has_wallbox'),
      ev_charging_priority: fieldVal('ev_charging_priority'),
      ev_dynamic_tariff_interest: field('ev_dynamic_tariff_interest')?.value || 'no',
      hp_status: fieldVal('hp_status'),
      hp_type: fieldVal('hp_type'),
      hp_heated_area_m2: parseFloat(fieldVal('hp_heated_area_m2')) || 0,
      hp_annual_heat_kwh: parseFloat(fieldVal('hp_annual_heat_kwh')) || 0,
      hp_replacing: fieldVal('hp_replacing'),
      hp_daytime_heating: fieldVal('hp_daytime_heating'),
      hp_priority: fieldVal('hp_priority'),
      user_situation: fieldVal('user_situation'),
      has_existing_pv: fieldVal('has_existing_pv') === '1',
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

  syncEvProgressLabel();
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
