// Live assumption sliders, battery worth-it toggle, 20-year cashflow chart

function renderAssumptionPanel(d) {
  const ci = d.calculator_inputs || {};
  const fin = d.financials || {};
  const pkg = d.three_packages?.packages?.[d.selected_package_id || 'best_value'] || d.selected_package || {};
  const base = {
    price: ci.electricity_price_ct || d.energy_economics?.electricity_price_ct || 32,
    annualKwh: sizingAnnualKwh(d),
    battery: pkg.battery_kwh || d.battery_kwh || 0,
    evKm: ci.ev_annual_km || d.ev_assessment?.annual_km || 0,
    budget: ci.budget_eur || 0,
    loanYears: d.financing_comparison?.loan?.term_years || 10,
    roofArea: ci.roof_area_m2 || 0,
    savings: pkg.annual_savings || fin.annual_savings || 0,
    payback: pkg.payback_years || fin.payback_years || 12,
    kwp: d.system_kwp || pkg.product_spec?.system_kwp_actual || 5,
    upfront: pkg.upfront_cost || fin.system_cost_typical || 15000,
  };

  return `
    <section class="result-section" id="assumptionPanel">
      <div class="results-panel assumptions-panel">
        <span class="results-panel-kicker">${tr('results.assumptions_title', 'Adjust assumptions')}</span>
        <h2 class="results-panel-title">${tr('results.assumptions_title', 'Adjust assumptions')}</h2>
        <p class="results-panel-sub">${tr('results.assumptions_sub', 'Move sliders to see how savings, payback and size shift — illustrative only.')}</p>
        <div class="assumption-sliders">
          ${assumptionSlider('assumptionPrice', tr('results.assumption.price', 'Electricity price (ct/kWh)'), base.price, 18, 50, 1, base.price)}
          ${assumptionSlider('assumptionConsumption', tr('results.assumption.consumption', 'Annual consumption (kWh)'), base.annualKwh, 1500, 12000, 100, base.annualKwh)}
          ${assumptionSlider('assumptionBattery', tr('results.assumption.battery', 'Battery size (kWh)'), base.battery, 0, 20, 0.5, base.battery)}
          ${assumptionSlider('assumptionEvKm', tr('results.assumption.ev_km', 'EV km per year'), base.evKm, 0, 30000, 500, base.evKm)}
          ${assumptionSlider('assumptionBudget', tr('results.assumption.budget', 'Budget (€)'), base.budget || base.upfront, 5000, 40000, 500, base.budget || base.upfront)}
          ${assumptionSlider('assumptionLoanYears', tr('results.assumption.loan_years', 'Loan duration (years)'), base.loanYears, 5, 20, 1, base.loanYears)}
          ${assumptionSlider('assumptionRoofArea', tr('results.assumption.roof_area', 'Roof area (m²)'), base.roofArea || 40, 10, 120, 1, base.roofArea || 40)}
        </div>
        <div class="assumption-live-metrics">
          <div><span>${tr('results.assumption.live_savings', 'Est. annual savings')}</span><strong id="liveSavings">${formatCurrency(base.savings)}</strong></div>
          <div><span>${tr('results.assumption.live_payback', 'Est. payback')}</span><strong id="livePayback">${base.payback} yrs</strong></div>
          <div><span>${tr('results.assumption.live_kwp', 'Est. system size')}</span><strong id="liveKwp">${base.kwp} kWp</strong></div>
        </div>
        ${renderBatteryWorthPanel(d)}
        ${renderCashflowChartPanel(d, base)}
      </div>
    </section>`;
}

function sizingAnnualKwh(d) {
  const sizing = d.sizing_summary || {};
  if (sizing.annual_consumption_kwh) return sizing.annual_consumption_kwh;
  const ci = d.calculator_inputs || {};
  if (ci.monthly_kwh > 0) return Math.round(ci.monthly_kwh * 12);
  return 4000;
}

function assumptionSlider(id, label, value, min, max, step, displayVal) {
  return `
    <label class="assumption-slider-row" for="${id}">
      <span class="assumption-slider-label">${label}</span>
      <span class="assumption-slider-value" id="${id}Val">${formatAssumptionDisplay(id, displayVal)}</span>
      <input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${value}">
    </label>`;
}

function formatAssumptionDisplay(id, val) {
  if (id === 'assumptionPrice') return `${Number(val).toFixed(0)} ct`;
  if (id === 'assumptionBudget') return formatCurrency(val);
  if (id === 'assumptionBattery') return `${Number(val).toFixed(1)} kWh`;
  if (id === 'assumptionEvKm') return `${Number(val).toLocaleString()} km`;
  if (id === 'assumptionLoanYears') return `${val} yrs`;
  if (id === 'assumptionRoofArea') return `${val} m²`;
  return `${Number(val).toLocaleString()} kWh`;
}

function renderBatteryWorthPanel(d) {
  const bc = d.battery_comparison;
  if (!bc?.with_battery) return '';
  const noB = bc.without_battery || {};
  const yesB = bc.with_battery || {};
  const extraCost = (yesB.upfront_extra_eur != null) ? yesB.upfront_extra_eur : '—';
  const verdict = yesB.annual_savings > noB.annual_savings * 1.08
    ? tr('results.yes', 'Yes')
    : tr('results.review', 'Review');
  return `
    <div class="battery-worth-panel" id="batteryWorthPanel">
      <h3>${tr('results.battery_worth_title', 'Battery: worth it or not?')}</h3>
      <p class="section-sub">${tr('results.battery_worth_sub', 'Compare with and without storage for your profile.')}</p>
      <label class="battery-worth-toggle">
        <input type="checkbox" id="batteryWorthToggle" ${(d.battery_kwh || 0) > 0 ? 'checked' : ''}>
        <span>${tr('results.with_battery', 'With battery')}</span>
      </label>
      <div class="battery-worth-grid">
        <div class="battery-worth-col" id="batteryWorthWithout">
          <strong>${tr('results.without_battery', 'Without battery')}</strong>
          <span>${noB.self_consumption_ratio || '—'}% ${tr('results.self_consumption', 'Self-consumption')}</span>
          <span>${formatCurrency(noB.annual_savings || 0)}/yr</span>
          <span>${tr('results.backup', 'Backup')}: ${tr('results.no', 'No')}</span>
        </div>
        <div class="battery-worth-col highlight" id="batteryWorthWith">
          <strong>${tr('results.with_battery', 'With battery')}</strong>
          <span>${yesB.self_consumption_ratio || '—'}% ${tr('results.self_consumption', 'Self-consumption')}</span>
          <span>${formatCurrency(yesB.annual_savings || 0)}/yr</span>
          <span>${tr('results.backup', 'Backup')}: ${tr('results.yes', 'Yes')}</span>
        </div>
      </div>
      <p class="battery-worth-verdict"><strong>${tr('results.battery_worth_verdict', 'Worth it for you?')}</strong> <span id="batteryWorthVerdict">${verdict}</span></p>
    </div>`;
}

function renderCashflowChartPanel(d, base) {
  return `
    <div class="cashflow-chart-panel">
      <h3>${tr('results.cashflow_chart_title', '20-year cumulative cash flow')}</h3>
      <canvas id="cashflowChart" width="640" height="220" role="img" aria-label="${tr('results.cashflow_chart_title', '20-year cumulative cash flow')}"></canvas>
      <div class="cashflow-legend">
        <span class="cashflow-legend-item cashflow-legend-cash">${tr('results.cashflow_cash', 'Cash purchase')}</span>
        <span class="cashflow-legend-item cashflow-legend-loan">${tr('results.cashflow_loan', 'Financing')}</span>
      </div>
    </div>`;
}

function wireAssumptionSliders(d) {
  const panel = document.getElementById('assumptionPanel');
  if (!panel) return;
  const ci = d.calculator_inputs || {};
  const fin = d.financials || {};
  const pkg = d.three_packages?.packages?.[d.selected_package_id || selectedPackageId || 'best_value'] || d.selected_package || {};
  const base = {
    price: ci.electricity_price_ct || d.energy_economics?.electricity_price_ct || 32,
    annualKwh: sizingAnnualKwh(d),
    battery: pkg.battery_kwh || d.battery_kwh || 0,
    evKm: ci.ev_annual_km || d.ev_assessment?.annual_km || 0,
    budget: ci.budget_eur || 0,
    loanYears: d.financing_comparison?.loan?.term_years || 10,
    roofArea: ci.roof_area_m2 || 0,
    savings: pkg.annual_savings || fin.annual_savings || 0,
    payback: pkg.payback_years || fin.payback_years || 12,
    kwp: d.system_kwp || pkg.product_spec?.system_kwp_actual || 5,
    upfront: pkg.upfront_cost || fin.system_cost_typical || 15000,
  };

  const liveSavings = document.getElementById('liveSavings');
  const livePayback = document.getElementById('livePayback');
  const liveKwp = document.getElementById('liveKwp');

  function readVals() {
    return {
      price: parseFloat(document.getElementById('assumptionPrice')?.value || base.price),
      annualKwh: parseFloat(document.getElementById('assumptionConsumption')?.value || base.annualKwh),
      battery: parseFloat(document.getElementById('assumptionBattery')?.value || base.battery),
      evKm: parseFloat(document.getElementById('assumptionEvKm')?.value || base.evKm),
      budget: parseFloat(document.getElementById('assumptionBudget')?.value || base.budget),
      loanYears: parseFloat(document.getElementById('assumptionLoanYears')?.value || base.loanYears),
      roofArea: parseFloat(document.getElementById('assumptionRoofArea')?.value || base.roofArea),
    };
  }

  let recalcTimer = null;
  let recalcBusy = false;

  function recalc() {
    const v = readVals();
    clearTimeout(recalcTimer);
    recalcTimer = setTimeout(async () => {
      if (recalcBusy) return;
      recalcBusy = true;
      try {
        const resp = await fetch('/api/calculate/recalc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({
            calculator_inputs: d.calculator_inputs || {},
            location: d.location || {},
            pvgis: d.pvgis || { specific_yield_kwh_kwp: d.specific_yield_kwh_kwp },
            selected_package_id: d.selected_package_id || selectedPackageId || 'best_value',
            overrides: {
              electricity_price_ct: v.price,
              annual_kwh: v.annualKwh,
              battery_kwh: v.battery,
              ev_annual_km: v.evKm,
              budget_eur: v.budget,
              loan_years: v.loanYears,
              roof_area_m2: v.roofArea,
            },
          }),
        });
        if (resp.ok) {
          const data = await resp.json();
          const savings = data.annual_savings ?? data.financials?.annual_savings ?? base.savings;
          const payback = data.payback_years ?? data.financials?.payback_years ?? base.payback;
          const kwp = data.system_kwp ?? base.kwp;
          const upfront = data.upfront_cost ?? data.financials?.system_cost_typical ?? base.upfront;
          if (liveSavings) liveSavings.textContent = formatCurrency(savings);
          if (livePayback) livePayback.textContent = `${Number(payback).toFixed(1)} yrs`;
          if (liveKwp) liveKwp.textContent = `${Number(kwp).toFixed(1)} kWp`;
          drawCashflowChart(
            { ...d, financing_comparison: data.financing_comparison || d.financing_comparison },
            savings,
            upfront,
            v.loanYears,
          );
          return;
        }
      } catch (_err) {
        /* fall through to local heuristic */
      } finally {
        recalcBusy = false;
      }
      recalcLocal(v);
    }, 280);
  }

  function recalcLocal(v) {
    const priceRatio = v.price / (base.price || 32);
    const useRatio = v.annualKwh / (base.annualKwh || 4000);
    const battBonus = 1 + (v.battery / 20) * 0.12;
    const evBonus = 1 + (v.evKm / 20000) * 0.05;
    const roofCap = v.roofArea > 0 ? Math.min(1.2, v.roofArea / 40) : 1;

    const savings = (base.savings || 800) * priceRatio * Math.sqrt(useRatio) * battBonus * evBonus;
    const kwp = Math.max(2, Math.min(30, (base.kwp || 5) * useRatio * roofCap));
    const upfront = v.budget > 0 ? Math.min(v.budget, (base.upfront || 15000) * (kwp / (base.kwp || 5))) : (base.upfront || 15000) * (kwp / (base.kwp || 5));
    const payback = savings > 0 ? Math.max(4, Math.min(25, upfront / savings)) : base.payback;

    if (liveSavings) liveSavings.textContent = formatCurrency(savings);
    if (livePayback) livePayback.textContent = `${payback.toFixed(1)} yrs`;
    if (liveKwp) liveKwp.textContent = `${kwp.toFixed(1)} kWp`;

    drawCashflowChart(d, savings, upfront, v.loanYears);
  }

  panel.querySelectorAll('input[type="range"]').forEach((input) => {
    input.addEventListener('input', () => {
      const valEl = document.getElementById(`${input.id}Val`);
      if (valEl) valEl.textContent = formatAssumptionDisplay(input.id, input.value);
      recalc();
    });
  });

  document.getElementById('batteryWorthToggle')?.addEventListener('change', (e) => {
    const withCol = document.getElementById('batteryWorthWith');
    const withoutCol = document.getElementById('batteryWorthWithout');
    if (e.target.checked) {
      withCol?.classList.add('highlight');
      withoutCol?.classList.remove('highlight');
    } else {
      withoutCol?.classList.add('highlight');
      withCol?.classList.remove('highlight');
    }
  });

  recalcLocal(readVals());
}

function drawCashflowChart(d, annualSavings, upfront, loanYears) {
  const canvas = document.getElementById('cashflowChart');
  if (!canvas?.getContext) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const pad = { l: 48, r: 16, t: 16, b: 32 };
  const years = 20;
  const loan = d.financing_comparison?.loan || {};
  const monthlyPay = loan.monthly_payment || upfront / (loanYears * 12) * 1.15;
  const monthlySave = annualSavings / 12;

  const cashSeries = [0];
  const loanSeries = [0];
  for (let y = 1; y <= years; y += 1) {
    const prevCash = cashSeries[y - 1];
    const prevLoan = loanSeries[y - 1];
    const yrSave = annualSavings * Math.pow(1.02, y - 1);
    cashSeries.push(prevCash + yrSave - (y === 1 ? upfront : 0));
    const loanOut = monthlyPay * 12 - monthlySave * 12;
    loanSeries.push(prevLoan + yrSave - (y === 1 ? upfront * 0.1 : 0) - Math.max(0, loanOut));
  }

  const all = cashSeries.concat(loanSeries);
  const minY = Math.min(...all, -upfront);
  const maxY = Math.max(...all, annualSavings * 5);
  const xStep = (w - pad.l - pad.r) / years;
  const yScale = (val) => h - pad.b - ((val - minY) / (maxY - minY || 1)) * (h - pad.t - pad.b);

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#64748b';
  ctx.font = '11px Inter, sans-serif';
  ctx.fillText('€', 8, pad.t + 8);

  function drawLine(series, color) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    series.forEach((val, i) => {
      const x = pad.l + i * xStep;
      const y = yScale(val);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  drawLine(cashSeries, '#0f766e');
  drawLine(loanSeries, '#f59e0b');

  ctx.fillStyle = '#94a3b8';
  for (let y = 0; y <= years; y += 5) {
    const x = pad.l + y * xStep;
    ctx.fillText(String(y), x - 4, h - 10);
  }
}
