// Extended results sections – readiness, scenarios, trust, roadmap

function renderEvAssessment(ev) {
  if (!ev || !ev.ownership) return '';
  const notes = (ev.notes || []).map((n) => `<li>${n}</li>`).join('');
  const future = (ev.future_features || []).map((f) => `<li>${f}</li>`).join('');
  return `
    <section class="result-section">
      <div class="results-panel ev-profile-panel">
        <span class="results-panel-kicker">${tr('results.ev_profile_title', 'EV charging profile')}</span>
        <h2 class="results-panel-title">${tr('results.ev_profile_sub', 'Based on your driving and charging answers')}</h2>
        <dl class="ev-profile-grid">
          <div><dt>${tr('calc.ev.ownership', 'EV status')}</dt><dd>${ev.ownership_label || '—'}</dd></div>
          <div><dt>${tr('calc.ev.vehicle_model', 'Vehicle')}</dt><dd>${ev.vehicle_model || '—'}</dd></div>
          <div><dt>${tr('calc.ev.annual_km', 'Annual km')}</dt><dd>${ev.annual_km ? ev.annual_km.toLocaleString() + ' km' : '—'}</dd></div>
          <div><dt>${tr('calc.ev.consumption', 'Consumption')}</dt><dd>${ev.consumption_kwh_100km || '—'} kWh/100 km</dd></div>
          <div><dt>${tr('results.ev_annual_charge', 'Est. charging')}</dt><dd>${(ev.annual_charging_kwh || 0).toLocaleString()} kWh/yr</dd></div>
          <div><dt>${tr('calc.ev.priority', 'Priority')}</dt><dd>${ev.charging_priority_label || '—'}</dd></div>
          <div><dt>${tr('results.ev_grid_cost', 'Grid charging cost')}</dt><dd>~€${(ev.estimated_grid_charging_cost_annual_eur || 0).toLocaleString()}/yr</dd></div>
          <div><dt>${tr('results.ev_pv_cost', 'With PV (est.)')}</dt><dd>~€${(ev.estimated_charging_cost_with_pv_annual_eur || 0).toLocaleString()}/yr</dd></div>
        </dl>
        ${notes ? `<ul class="ev-profile-notes">${notes}</ul>` : ''}
        <p class="ev-profile-cta-wrap">
          <a href="/ev/bundle?weekly_km=${Math.round((ev.annual_km || 12000) / 52)}&has_wallbox=${ev.has_wallbox === 'yes' ? '1' : ''}" class="btn btn-primary btn-sm">${tr('evm.bundle_cta_short', 'Build home-energy bundle')}</a>
          <a href="/ev/find" class="btn btn-outline btn-sm">${tr('evm.results_cta', 'Find used EVs that fit your setup')}</a>
        </p>
        ${future ? `<div class="info-box"><strong>${tr('results.ev_future', 'Planned enhancements')}</strong><ul>${future}</ul></div>` : ''}
      </div>
    </section>`;
}

function packageComponentTier(pkg) {
  const tiers = {
    cheapest: tr('results.tier.budget', 'Budget components (string inverter)'),
    best_value: tr('results.tier.balanced', 'Balanced components (hybrid inverter)'),
    most_reliable: tr('results.tier.premium', 'Premium / backup-capable components'),
  };
  return tiers[pkg.id] || pkg.subtitle || '—';
}

function renderHpAssessment(hp) {
  if (!hp || !hp.status) return '';
  const notes = (hp.notes || []).map((n) => `<li>${n}</li>`).join('');
  return `
    <section class="result-section">
      <div class="results-panel ev-profile-panel hp-profile-panel">
        <span class="results-panel-kicker">${tr('results.hp_profile_title', 'Heating & heat pump profile')}</span>
        <h2 class="results-panel-title">${tr('results.hp_profile_sub', 'Based on your heating goals and answers')}</h2>
        <dl class="ev-profile-grid">
          <div><dt>${tr('results.hp_goals', 'Goals')}</dt><dd>${hp.goals_label || '—'}</dd></div>
          <div><dt>${tr('calc.hp.status', 'Heat pump status')}</dt><dd>${hp.status_label || '—'}</dd></div>
          <div><dt>${tr('calc.hp.type', 'System type')}</dt><dd>${hp.type_label || '—'}</dd></div>
          <div><dt>${tr('calc.hp.heated_area', 'Heated area')}</dt><dd>${hp.heated_area_m2 ? hp.heated_area_m2.toLocaleString() + ' m²' : '—'}</dd></div>
          <div><dt>${tr('results.hp_annual_heat', 'Est. heat electricity')}</dt><dd>${(hp.annual_heat_kwh || 0).toLocaleString()} kWh/yr</dd></div>
          <div><dt>${tr('calc.hp.priority', 'Priority')}</dt><dd>${hp.priority_label || '—'}</dd></div>
          <div><dt>${tr('results.hp_grid_cost', 'Grid heating cost')}</dt><dd>~€${(hp.estimated_grid_heating_cost_annual_eur || 0).toLocaleString()}/yr</dd></div>
          <div><dt>${tr('results.hp_pv_cost', 'With PV (est.)')}</dt><dd>~€${(hp.estimated_heating_cost_with_pv_annual_eur || 0).toLocaleString()}/yr</dd></div>
        </dl>
        ${notes ? `<ul class="ev-profile-notes">${notes}</ul>` : ''}
      </div>
    </section>`;
}

function renderTrustGlossary() {
  return `
    <section class="result-section compact-section">
      <div class="trust-glossary info-box">
        <h2 class="trust-glossary-title">${tr('results.trust_glossary_title', 'How to read our labels')}</h2>
        <dl class="trust-glossary-grid">
          <div><dt>${tr('results.trust.verified', 'Registered supplier')}</dt><dd>${tr('results.trust.verified_def', 'Business on file with identity and insurance documentation when enrolled — not a guarantee of workmanship.')}</dd></div>
          <div><dt>${tr('results.trust.quality', 'Quality score')}</dt><dd>${tr('results.trust.quality_def', 'Internal fit score from certifications, reviews, and quote completeness — relative ranking, not a government rating.')}</dd></div>
          <div><dt>${tr('results.trust.reliability', 'Package tier')}</dt><dd>${tr('results.trust.reliability_def', 'Budget / Balanced / Premium describes component level in our catalog model — not field-tested reliability.')}</dd></div>
          <div><dt>${tr('results.trust.readiness', 'Site readiness index')}</dt><dd>${tr('results.trust.readiness_def', 'Indicative score from your inputs — a site survey is still required before installation.')}</dd></div>
        </dl>
      </div>
    </section>`;
}

function renderReadiness(r) {
  if (!r || !r.label) return '';
  const palette = scoreColorPalette(r.score);
  const factors = (r.factors || []).map(f => {
    const impactLabel = f.impact === 'positive' ? tr('results.good', 'Good') : f.impact === 'negative' ? tr('results.review', 'Review') : tr('results.note', 'Note');
    const icon = f.impact === 'positive' ? '✓' : f.impact === 'negative' ? '!' : 'i';
    return `
    <div class="readiness-factor readiness-${f.impact}">
      <div class="readiness-factor-icon" aria-hidden="true">${icon}</div>
      <div class="readiness-factor-body">
        <span class="readiness-factor-badge">${impactLabel}</span>
        <span class="readiness-factor-name">${f.factor}</span>
        <span class="readiness-factor-detail">${f.detail}</span>
      </div>
    </div>`;
  }).join('');
  return `
    <section class="result-section compact-section">
      <div class="readiness-panel readiness-${r.level}" style="--score-color:${palette.color};--score-glow:${palette.glow};border-color:${palette.color}">
        <div class="readiness-header" style="background:${palette.headerGradient}">
          <div class="readiness-score-ring" style="--pct:${r.score};--ring-color:${palette.ringFill};--ring-track:${palette.ringTrack}">
            <span class="readiness-score-num" style="color:${palette.color}">${r.score}</span>
          </div>
          <div class="readiness-header-text">
            <h2 class="readiness-title">${r.label}</h2>
            <p class="readiness-summary">${r.summary}</p>
            <p class="readiness-sc">${tr('results.readiness_index', 'Site readiness index')} · ~${Math.min(100, r.self_consumption_pct || 35)}% ${tr('results.estimated_self_consumption', 'estimated self-consumption')}</p>
          </div>
        </div>
        <div class="readiness-factors-wrap">
          <p class="readiness-factors-label">${tr('results.readiness_checked', 'What we checked')}</p>
          <div class="readiness-factors">${factors}</div>
        </div>
      </div>
    </section>`;
}

function renderWhyExplanation(text, bullets) {
  return renderWhyScanBlocks({ why_explanation: text, why_recommend: bullets });
}

function renderWhyScanBlocks(d) {
  const rec = d.system_recommendation || {};
  const sizing = d.sizing_summary || {};
  const ci = d.calculator_inputs || {};
  const goals = (d.goals || ci.goals || []).map(formatDisplayLabel).join(', ') || '—';
  const annualKwh = sizing.annual_consumption_kwh || sizingAnnualKwhFromData(d);
  const yieldKwh = d.specific_yield_kwh_kwp || 950;
  const batt = rec.battery_kwh || d.battery_kwh || 0;
  const parts = [`${rec.headline_kwp || d.system_kwp || '—'} kWp PV`];
  if (batt > 0) parts.push(`${batt} kWh battery`);
  if ((d.goals || []).includes('ev_charging')) parts.push('smart wallbox');
  const headline = parts.join(' + ');

  const useText = d.why_explanation || `Estimated use ~${Number(annualKwh).toLocaleString()} kWh/year at ${ci.electricity_price_ct || 32} ct/kWh drives the target system size.`;
  const roofText = sizing.roof_note || sizing.formula_text || `Roof type ${formatDisplayLabel(ci.roof_type || 'pitched_south')} with ~${yieldKwh} kWh/kWp yield.`;
  const goalText = (d.why_recommend || []).slice(0, 2).map((b) => b.replace(/\*\*/g, '')).join(' ') || `Goals: ${goals}.`;
  const limits = (d.why_limitations || []).map((n) => `<li>${n}</li>`).join('');

  return `
    <section class="result-section compact-section">
      <div class="result-insight-card why-scan-card">
        <div class="result-insight-header">
          <span class="result-insight-kicker">${tr('results.why_kicker', 'Our analysis')}</span>
          <h2 class="why-card-title">${tr('results.why_scan_headline', 'Your recommended system')}</h2>
          <p class="why-scan-headline">${headline}</p>
        </div>
        <div class="why-scan-grid">
          <div class="why-scan-block">
            <h3>${tr('results.why_because_use', 'Because of your electricity use')}</h3>
            <p>${useText}</p>
          </div>
          <div class="why-scan-block">
            <h3>${tr('results.why_because_roof', 'Because of your roof')}</h3>
            <p>${roofText}</p>
          </div>
          <div class="why-scan-block">
            <h3>${tr('results.why_because_goals', 'Because of your goals')}</h3>
            <p>${goalText}</p>
          </div>
          <div class="why-scan-block why-scan-block--limits">
            <h3>${tr('results.why_not_cover', 'What this does not cover')}</h3>
            <ul class="why-scan-limits">${limits || `<li>${tr('results.why_not_cover', 'What this does not cover')}</li>`}</ul>
          </div>
        </div>
      </div>
    </section>`;
}

function sizingAnnualKwhFromData(d) {
  const ci = d.calculator_inputs || {};
  if (ci.monthly_kwh > 0) return Math.round(ci.monthly_kwh * 12);
  return 4000;
}

function renderNextStepsPath(steps) {
  const items = (steps || []).map((s, i) => `
    <div class="path-step ${i === 0 ? 'path-step--current' : ''}">
      <span class="path-step-num">${s.step || i + 1}</span>
      <div>
        <p class="path-step-title">${tr(s.title_key || '', s.title || '')}</p>
        <p class="path-step-detail">${tr(s.detail_key || '', s.detail || '')}</p>
      </div>
    </div>
  `).join('');
  if (!items) return '';
  return `
    <section class="result-section compact-section">
      <div class="results-panel project-path-panel">
        <span class="results-panel-kicker">${tr('results.path_kicker', 'Your project path')}</span>
        <h2 class="results-panel-title">${tr('results.path_title', 'Next steps')}</h2>
        <p class="results-panel-sub">${tr('results.path_sub', 'A typical journey from first estimate to monitoring — your installer will confirm timing.')}</p>
        <div class="project-path-steps">${items}</div>
      </div>
    </section>`;
}

const HOUSEHOLD_LOAD_TONES = {
  has_heat_pump: 'heat',
  has_ev: 'ev',
  planned_ev: 'ev',
  has_electric_water_heater: 'water',
  has_pool: 'pool',
  has_home_office: 'office',
  has_ac: 'ac',
  high_daytime_use: 'solar',
  planned_extension: 'build',
};

function renderHouseholdProfile(hp) {
  if (!hp || !hp.active_loads) return '';
  const hasLoads = hp.active_loads.length > 0;
  const delta = Math.max(0, (hp.adjusted_annual_kwh || 0) - (hp.base_annual_kwh || 0));

  const loadsHtml = hasLoads
    ? hp.active_loads.map(l => {
        const tone = HOUSEHOLD_LOAD_TONES[l.key] || 'default';
        const kwh = l.estimated_annual_kwh;
        return `
        <div class="household-load-card household-load-card--${tone}">
          <span class="household-load-icon" aria-hidden="true">${l.icon}</span>
          <div class="household-load-body">
            <span class="household-load-label">${l.label}</span>
            ${kwh ? `<span class="household-load-kwh">+${formatNumber(kwh)} kWh/yr</span>` : `<span class="household-load-kwh household-load-kwh--boost">${tr('results.self_use_boost', 'Boosts self-use')}</span>`}
          </div>
        </div>`;
      }).join('')
    : `<div class="household-empty-state">
        <div class="household-empty-icon" aria-hidden="true">🏠</div>
        <p class="household-empty-title">${tr('results.no_major_loads_title', 'No major loads added yet')}</p>
        <p class="household-empty-desc">${tr('results.no_major_loads_desc', 'Heat pumps, EVs, and pool pumps change how much solar and battery you need.')}</p>
        <a href="/calculator" class="household-empty-cta">${tr('results.add_in_calculator', 'Add in calculator')} →</a>
      </div>`;

  return `
    <section class="result-section compact-section">
      <div class="result-insight-card household-profile-card">
        <div class="result-insight-header household-profile-header">
          <span class="result-insight-kicker">${tr('results.household_kicker', 'Your usage')}</span>
          <h2>${tr('results.household_profile', 'Household energy profile')}</h2>
          <div class="household-use-stats">
            <div class="household-use-stat household-use-stat--adjusted">
              <span class="household-use-stat-label">${tr('results.adjusted_annual_use', 'Adjusted annual use')}</span>
              <strong>${formatNumber(hp.adjusted_annual_kwh)}</strong>
              <span class="household-use-stat-unit">kWh/yr</span>
            </div>
            <div class="household-use-stat household-use-stat--base">
              <span class="household-use-stat-label">${tr('results.base', 'Base')}</span>
              <strong>${formatNumber(hp.base_annual_kwh)}</strong>
              <span class="household-use-stat-unit">kWh/yr</span>
            </div>
            ${delta > 0 ? `
            <div class="household-use-stat household-use-stat--delta">
              <span class="household-use-stat-label">${tr('results.load_additions', 'From loads')}</span>
              <strong>+${formatNumber(delta)}</strong>
              <span class="household-use-stat-unit">kWh/yr</span>
            </div>` : ''}
          </div>
        </div>
        <div class="result-insight-body household-profile-body">
          <div class="household-loads-grid">${loadsHtml}</div>
          ${hp.battery_sizing_note ? `
          <div class="household-sizing-note household-sizing-note--${hasLoads ? 'active' : 'standard'}">
            <span class="household-sizing-icon" aria-hidden="true">${hasLoads ? '🔋' : '📊'}</span>
            <span>${hp.battery_sizing_note}</span>
          </div>` : ''}
          ${!hasLoads && hp.lead_value_note ? `
          <a href="/calculator" class="household-profile-cta">${hp.lead_value_note} →</a>` : ''}
        </div>
      </div>
    </section>`;
}

function renderPriceScenarios(ps) {
  if (!ps || !ps.scenarios) return '';
  const cards = ps.scenarios.map((s, i) => `
    <button type="button" class="scenario-card" data-scenario="${s.id}" data-scenario-idx="${i}">
      <span class="scenario-label">${s.label}</span>
      <span class="scenario-payback">${s.payback_years} yr payback</span>
      <span class="scenario-net">10-yr net: ${formatCurrency(s.ten_year_net_eur)}</span>
      <span class="scenario-note">${s.note}</span>
    </button>
  `).join('');
  return `
    <section class="result-section" id="priceScenarios">
      <div class="price-scenarios-panel">
        <span class="results-panel-kicker">${tr('results.scenarios_kicker', 'Sensitivity check')}</span>
        <h2 class="results-panel-title">${tr('results.price_change', 'What if electricity prices change?')}</h2>
        <p class="results-panel-sub">${tr('results.price_change_sub', 'Drag the slider or tap a scenario - savings and payback shift with price assumptions.')}</p>
        <div class="scenario-slider-wrap">
          <input type="range" id="priceScenarioSlider" min="0" max="2" step="1" value="1"
            class="scenario-slider" aria-label="Electricity price scenario">
          <div class="scenario-labels" role="tablist" aria-label="Price scenarios">
            <button type="button" class="scenario-label-btn" data-scenario-idx="0">${tr('results.stable', 'Stable')}</button>
            <button type="button" class="scenario-label-btn" data-scenario-idx="1">${tr('results.moderate_rise', 'Moderate rise')}</button>
            <button type="button" class="scenario-label-btn" data-scenario-idx="2">${tr('results.faster_rise', 'Faster rise')}</button>
          </div>
        </div>
        <div class="scenario-grid">${cards}</div>
        <p class="scenario-disclaimer">${ps.disclaimer || ''}</p>
      </div>
    </section>`;
}

function renderFinancingComparison(fc) {
  if (!fc) return '';
  const cash = fc.cash || {};
  const loan = fc.loan || {};
  return `
    <section class="result-section compact-section" id="financingSection">
      <div class="fin-compare-panel">
        <span class="results-panel-kicker">${tr('results.financing_kicker', 'Payment options')}</span>
        <h2 class="results-panel-title">${tr('results.cash_financing', 'Cash vs financing')}</h2>
        <p class="results-panel-sub">${tr('results.cash_financing_sub', 'Illustrative comparison - not an offer of credit.')}</p>
      <div class="fin-compare-grid">
        <div class="fin-compare-card fin-compare-card--cash">
          <h3>${cash.label}</h3>
          <div class="fin-row"><span>Upfront</span><strong>${formatCurrency(cash.upfront)}</strong></div>
          <div class="fin-row"><span>Monthly savings</span><strong>${formatCurrency(cash.monthly_savings_offset)}</strong></div>
          <div class="fin-row"><span>Net monthly cash</span><strong class="text-green">${formatCurrency(cash.net_monthly_cash)}</strong></div>
        </div>
        <div class="fin-compare-card fin-compare-card--loan fin-compare-highlight">
          <h3>${loan.label}</h3>
          <div class="fin-row"><span>Monthly payment</span><strong>${formatCurrency(loan.monthly_payment)}</strong></div>
          <div class="fin-row"><span>Savings offset</span><strong>${formatCurrency(loan.monthly_savings_offset)}</strong></div>
          <div class="fin-row"><span>Net monthly cash</span><strong class="${loan.net_monthly_cash >= 0 ? 'text-green' : 'text-red'}">${formatCurrency(loan.net_monthly_cash)}</strong></div>
          <div class="fin-row"><span>10-yr total cost</span><strong>${formatCurrency(loan.total_cost_10yr)}</strong></div>
        </div>
      </div>
      <p class="scenario-disclaimer">${fc.disclaimer || ''}</p>
      </div>
    </section>`;
}

function renderBudgetFirst(bf) {
  if (!bf) return '';
  return `
    <section class="result-section compact-section">
      <div class="result-insight-card budget-first-card">
        <div class="result-insight-header">
          <h2>${tr('results.budget_first', 'Budget-first result')}</h2>
        </div>
        <div class="result-insight-body">
          <p>${bf.summary}</p>
        <div class="budget-stats">
          <span>Max ~<strong>${bf.max_system_kwp} kWp</strong></span>
          <span>~<strong>${formatNumber(bf.estimated_annual_production_kwh)} kWh/yr</strong> production</span>
          <span>Covers ~<strong>${bf.covers_consumption_pct}%</strong> of use</span>
        </div>
        <p class="insight-note">${bf.financing_note}</p>
        </div>
      </div>
    </section>`;
}

function renderQuoteChecklist(items) {
  if (!items || !items.length) return '';
  const lis = items.map(i => `
    <li class="quote-checklist-item">
      <span class="quote-checklist-check" aria-hidden="true">✓</span>
      <span class="quote-checklist-text">${i}</span>
    </li>
  `).join('');
  return `
    <section class="result-section quote-checklist-section">
      <div class="quote-checklist-card">
        <header class="quote-checklist-header">
          <div class="quote-checklist-header-main">
            <div class="quote-checklist-icon" aria-hidden="true">📋</div>
            <div>
              <h2 class="quote-checklist-title">${tr('results.quote_checklist', 'Quote quality checklist')}</h2>
              <p class="quote-checklist-intro">${tr('results.quote_checklist_intro', 'Every installer quote should include these items - use this when reviewing offers.')}</p>
            </div>
          </div>
          <span class="quote-checklist-count">${items.length} ${tr('results.items_to_verify', 'items to verify')}</span>
        </header>
        <ul class="quote-checklist-grid">${lis}</ul>
      </div>
    </section>`;
}

function reasonChipTone(reason) {
  const r = (reason || '').toLowerCase();
  if (r.includes('postcode') || r.includes('regional') || r.includes('plz')) return 'area';
  if (r.includes('budget') || r.includes('cost')) return 'budget';
  if (r.includes('verified')) return 'verified';
  if (r.includes('battery')) return 'battery';
  if (r.includes('commercial') || r.includes('agricultural')) return 'specialty';
  if (r.includes('installation') || r.includes('weeks')) return 'timing';
  return 'default';
}

function fitTier(score) {
  const s = Number(score) || 0;
  if (s >= 75) return 'strong';
  if (s >= 55) return 'good';
  return 'possible';
}

function renderMatchedSuppliers(suppliers) {
  if (!suppliers || !suppliers.length) return '';
  const cards = suppliers.map((s, i) => {
    const ver = (s.verification || []).filter(v => v.status === 'verified').length;
    const tier = fitTier(s.fit_score);
    const reasons = (s.fit_reasons || []).slice(0, 3);
    const reasonChips = reasons.length
      ? reasons.map(r => `<span class="match-reason-chip match-reason-chip--${reasonChipTone(r)}">${r}</span>`).join('')
      : `<span class="match-reason-chip match-reason-chip--default">${tr('results.regional_coverage', 'Regional coverage')}</span>`;
    const verified = s.verified || ver >= 2;
    return `
      <article class="match-supplier-card match-supplier-card--${tier}">
        <span class="match-supplier-rank" aria-hidden="true">#${i + 1}</span>
        <div class="match-supplier-top">
          <h3 class="match-supplier-name">${s.company_name}</h3>
          <div class="match-fit-score match-fit-score--${tier}" title="${s.fit_label || 'Fit'}">
            <span class="match-fit-num">${s.fit_score ?? '—'}</span>
            <span class="match-fit-of">/100</span>
          </div>
        </div>
        <p class="match-fit-label">${s.fit_label || tr('results.match_label', 'Match')}</p>
        ${reasons.length ? `<p class="match-fit-because"><strong>${tr('results.supplier_matched_because', 'Matched because')}:</strong> ${reasons.join(' · ')}</p>` : ''}
        <div class="match-reason-chips">${reasonChips}</div>
        <div class="match-supplier-meta">
          ${verified
            ? `<span class="match-meta-pill match-meta-pill--verified">✓ ${tr('results.supplier_verified', 'Registered partner')}</span>`
            : `<span class="match-meta-pill match-meta-pill--directory">${tr('results.supplier_directory', 'Directory listing')}</span>`}
          ${ver > 0 ? `<span class="match-meta-pill match-meta-pill--checks">${ver} ${tr('results.checks_passed', 'checks passed')}</span>` : ''}
          ${s.plan && s.plan !== 'basic' ? `<span class="match-meta-pill match-meta-pill--plan">${s.plan} ${tr('results.plan_label', 'plan')}</span>` : ''}
        </div>
      </article>`;
  }).join('');
  return `
    <section class="result-section matched-suppliers-section">
      <div class="matched-suppliers-panel">
        <span class="matched-suppliers-kicker">${tr('results.matched_suppliers_kicker', 'Top matches for your project')}</span>
        <h2 class="matched-suppliers-title">${tr('results.matched_suppliers_title', 'Matched suppliers')}</h2>
        <p class="matched-suppliers-sub">${tr('results.matched_suppliers_sub', 'Ranked by fit for your project - not just who pays the most.')}</p>
        <p class="matched-suppliers-note">${tr('results.supplier_max_note', 'You choose which installers receive your details. Maximum 3 at once.')}</p>
        <div class="match-supplier-grid">${cards}</div>
      </div>
    </section>`;
}

function renderVerificationFramework() {
  const items = [
    { icon: '🪪', title: tr('results.verify.identity', 'Business identity'), desc: tr('results.verify.identity_desc', 'Company registration and contact details'), status: tr('results.verify.on_enrollment', 'On enrollment') },
    { icon: '🛡️', title: tr('results.verify.insurance', 'Insurance'), desc: tr('results.verify.insurance_desc', 'Liability cover documentation'), status: tr('results.verify.on_enrollment', 'On enrollment') },
    { icon: '📜', title: tr('results.verify.certs', 'Certifications'), desc: tr('results.verify.certs_desc', 'Electrical credentials where applicable'), status: tr('results.verify.on_enrollment', 'On enrollment') },
    { icon: '🏗️', title: tr('results.verify.portfolio', 'Project portfolio'), desc: tr('results.verify.portfolio_desc', 'Recent installation examples'), status: tr('results.verify.planned', 'Planned') },
    { icon: '⏱️', title: tr('results.verify.response', 'Response time'), desc: tr('results.verify.response_desc', 'Median first reply when tracked'), status: tr('results.verify.planned', 'Planned') },
    { icon: '✅', title: tr('results.verify.quote', 'Quote completeness'), desc: tr('results.verify.quote_desc', 'Checklist compliance score'), status: tr('results.verify.planned', 'Planned') },
    { icon: '⭐', title: tr('results.verify.ratings', 'Customer ratings'), desc: tr('results.verify.ratings_desc', 'Post-installation feedback'), status: tr('results.verify.planned', 'Planned') },
  ];
  const grid = items.map(i => `
    <article class="verify-framework-item">
      <div class="verify-framework-item-icon" aria-hidden="true">${i.icon}</div>
      <div class="verify-framework-item-body">
        <div class="verify-framework-item-top">
          <h3 class="verify-framework-item-title">${i.title}</h3>
          <span class="verify-framework-status">${i.status}</span>
        </div>
        <p class="verify-framework-item-desc">${i.desc}</p>
      </div>
    </article>
  `).join('');
  return `
    <section class="result-section verify-framework-section">
      <div class="verify-framework-card">
        <header class="verify-framework-header">
          <div class="verify-framework-header-main">
            <div class="verify-framework-shield" aria-hidden="true">🛡️</div>
            <div>
              <h2 class="verify-framework-title">${tr('results.verify_suppliers', 'Supplier quality framework')}</h2>
              <p class="verify-framework-intro">${tr('results.verify_suppliers_intro', 'When suppliers enroll, we document these checks. Not every item is verified for every listing yet.')}</p>
            </div>
          </div>
          <div class="verify-framework-meta">
            <span class="verify-framework-meta-pill">7 ${tr('results.checks_per_supplier', 'checks per supplier')}</span>
            <span class="verify-framework-meta-pill">${tr('results.updated_quarterly', 'Updated quarterly')}</span>
          </div>
        </header>
        <div class="verify-framework-grid">${grid}</div>
      </div>
    </section>`;
}

function renderEnergyRoadmap(steps) {
  if (!steps || !steps.length) return '';

  const ROADMAP_ICONS = {
    pv: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    ev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/></svg>',
    heat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M12 2c2 4 6 6 6 10a6 6 0 11-12 0c0-4 4-6 6-10z"/></svg>',
    battery: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="2" y="7" width="18" height="10" rx="2"/><path d="M22 11v2M6 11h4M12 11h4"/></svg>',
    tariff: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M3 3v18h18"/><path d="M7 16l4-5 4 3 5-7"/></svg>',
    expand: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 8v8M8 12h8"/></svg>',
    default: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1v-9.5z"/></svg>',
  };

  function roadmapIcon(title) {
    const t = (title || '').toLowerCase();
    if (t.includes('pv') || t.includes('rooftop') || t.includes('solar')) return ROADMAP_ICONS.pv;
    if (t.includes('ev') || t.includes('charger')) return ROADMAP_ICONS.ev;
    if (t.includes('heat')) return ROADMAP_ICONS.heat;
    if (t.includes('battery')) return ROADMAP_ICONS.battery;
    if (t.includes('tariff')) return ROADMAP_ICONS.tariff;
    if (t.includes('expand')) return ROADMAP_ICONS.expand;
    return ROADMAP_ICONS.default;
  }

  function phaseClass(phase) {
    const p = (phase || '').toLowerCase();
    if (p === 'now') return 'now';
    if (p === 'next') return 'next';
    return 'later';
  }

  const rows = steps.map((s, i) => {
    const phase = phaseClass(s.phase);
    const isLast = i === steps.length - 1;
    return `
    <article class="energy-roadmap-step energy-roadmap-step--${phase}${isLast ? ' energy-roadmap-step--last' : ''}">
      <div class="energy-roadmap-rail" aria-hidden="true">
        <span class="energy-roadmap-dot"></span>
        ${isLast ? '' : '<span class="energy-roadmap-line"></span>'}
      </div>
      <div class="energy-roadmap-card-inner">
        <div class="energy-roadmap-icon energy-roadmap-icon--${phase}">${roadmapIcon(s.title)}</div>
        <div class="energy-roadmap-body">
          <span class="energy-roadmap-phase energy-roadmap-phase--${phase}">${s.phase}</span>
          <h3 class="energy-roadmap-title">${s.title}</h3>
          <p class="energy-roadmap-detail">${s.detail}</p>
        </div>
      </div>
    </article>`;
  }).join('');

  const nowCount = steps.filter(s => phaseClass(s.phase) === 'now').length;
  const nextCount = steps.filter(s => phaseClass(s.phase) === 'next').length;
  const laterCount = steps.length - nowCount - nextCount;

  return `
    <section class="result-section energy-roadmap-section">
      <div class="energy-roadmap-card">
        <header class="energy-roadmap-header">
          <div class="energy-roadmap-header-main">
            <div class="energy-roadmap-header-icon" aria-hidden="true">🗺️</div>
            <div>
              <h2 class="energy-roadmap-title-main">${tr('results.energy_roadmap', 'Your home energy roadmap')}</h2>
              <p class="energy-roadmap-intro">${tr('results.energy_roadmap_intro', "Solar is often step one - here's what could come next for your home.")}</p>
            </div>
          </div>
          <div class="energy-roadmap-legend">
            ${nowCount ? `<span class="energy-roadmap-legend-pill energy-roadmap-legend-pill--now">${nowCount} now</span>` : ''}
            ${nextCount ? `<span class="energy-roadmap-legend-pill energy-roadmap-legend-pill--next">${nextCount} next</span>` : ''}
            ${laterCount ? `<span class="energy-roadmap-legend-pill energy-roadmap-legend-pill--later">${laterCount} later</span>` : ''}
          </div>
        </header>
        <div class="energy-roadmap-track">${rows}</div>
      </div>
    </section>`;
}

function renderDecisionReportBanner(dr) {
  if (!dr) return '';
  return `
    <section class="result-section compact-section">
      <div class="decision-report-banner">
        <h2>📄 ${dr.title || tr('results.report_title', 'Solar Decision Report')}</h2>
        <p>${tr('results.decision_report_banner', 'Your full assessment includes suitability, three packages, scenarios, assumptions, installer brief, and quote checklist.')}</p>
        <button class="btn btn-accent" id="downloadPdfBtnTop">${tr('results.download_pdf', 'Download decision report (PDF)')}</button>
      </div>
    </section>`;
}

function renderYieldValidation(yv) {
  if (!yv || yv.delta_pct == null) return '';
  const cls = yv.warning ? 'yield-warn' : 'yield-ok';
  const msg = tr(yv.message_key || 'yield.gsa_ok', 'Solar yield cross-checked with Global Solar Atlas');
  return `<div class="yield-validation ${cls}" role="status">${msg} <span class="yield-validation-delta">(PVGIS vs GSA: ${yv.delta_pct > 0 ? '+' : ''}${yv.delta_pct}%)</span></div>`;
}

function renderLeadTier(lt) {
  if (!lt) return '';
  const tierKey = lt.tier ? `lead.tier.${lt.tier}` : '';
  const tierLabel = tierKey ? tr(tierKey, lt.label || lt.tier) : (lt.label || lt.tier);
  return `
    <div class="project-profile-chip project-profile-chip--${lt.tier || 'basic'}">
      <span class="project-profile-kicker">${tr('results.project_readiness', 'Project readiness')}</span>
      <strong class="project-profile-tier">${tierLabel}</strong>
      ${lt.description ? `<span class="project-profile-desc">${lt.description}</span>` : ''}
    </div>`;
}

const SITE_GAP_META = [
  { pattern: /roof dim|dachfl|dach gr/i, icon: '📐', tone: 'dimension' },
  { pattern: /shading|verschattung|schatt/i, icon: '🌳', tone: 'shade' },
  { pattern: /photo|foto|bild/i, icon: '📷', tone: 'photo' },
  { pattern: /budget|budget/i, icon: '€', tone: 'budget' },
  { pattern: /electrical|elektr|zähler|meter/i, icon: '⚡', tone: 'electrical' },
];

function siteGapMeta(label) {
  const text = (label || '').toLowerCase();
  for (const g of SITE_GAP_META) {
    if (g.pattern.test(text)) return g;
  }
  return { icon: '＋', tone: 'default' };
}

function renderReportExtras(d) {
  const dr = d.decision_report || {};
  const gaps = dr.site_gaps || d.confidence?.missing_data || [];
  const assumptions = d.assumptions || [];
  if (!gaps.length && !assumptions.length) return '';

  const gapItems = gaps.map(g => {
    const meta = siteGapMeta(g);
    return `
    <li class="report-extra-item report-extra-item--${meta.tone}">
      <span class="report-extra-icon" aria-hidden="true">${meta.icon}</span>
      <div class="report-extra-body">
        <span class="report-extra-label">${g}</span>
        <a href="/calculator" class="report-extra-link">${tr('results.add_now', 'Add in calculator')} →</a>
      </div>
    </li>`;
  }).join('');

  const assumptionTones = ['location', 'use', 'price', 'yield', 'catalog'];
  const assumptionItems = assumptions.map((a, i) => {
    const tone = assumptionTones[i % assumptionTones.length];
    return `<li class="report-assumption-item report-assumption-item--${tone}">${a}</li>`;
  }).join('');

  const gapsBlock = gaps.length ? `
    <div class="report-extras-card report-extras-card--gaps">
      <span class="report-extras-kicker">${tr('results.site_gaps_kicker', 'Improve accuracy')}</span>
      <h3>${tr('results.site_gaps_title', 'Information that would improve your quote')}</h3>
      <p class="report-extras-intro">${tr('results.site_gaps_intro', 'Installers can still quote without these — but accuracy improves when you add them in the calculator or quote form.')}</p>
      <ul class="report-extras-list">${gapItems}</ul>
    </div>` : '';

  const assumptionsBlock = assumptions.length ? `
    <div class="report-extras-card report-extras-card--assumptions">
      <span class="report-extras-kicker">${tr('results.assumptions_kicker', 'Behind the numbers')}</span>
      <h3>${tr('results.assumptions_title', 'Assumptions & uncertainty')}</h3>
      <p class="report-extras-intro">${tr('results.assumptions_intro', 'Figures below are estimates based on the inputs you provided.')}</p>
      <ul class="report-extras-assumptions">${assumptionItems}</ul>
    </div>` : '';

  return `
    <section class="result-section report-extras-section">
      <div class="report-extras-grid">${gapsBlock}${assumptionsBlock}</div>
    </section>`;
}

function setupPriceScenarioSlider() {
  const root = document.getElementById('priceScenarios');
  const slider = document.getElementById('priceScenarioSlider');
  if (!root || !slider) return;

  const cards = root.querySelectorAll('.scenario-card');
  const labelBtns = root.querySelectorAll('.scenario-label-btn');

  const highlight = (idx) => {
    const i = Math.max(0, Math.min(2, parseInt(idx, 10) || 0));
    slider.value = String(i);
    const pct = (i / 2) * 100;
    slider.style.background = `linear-gradient(90deg, #0f766e 0%, #0f766e ${pct}%, #cbd5e1 ${pct}%, #cbd5e1 100%)`;
    cards.forEach((c, j) => c.classList.toggle('scenario-active', j === i));
    labelBtns.forEach((b, j) => {
      b.classList.toggle('scenario-label-active', j === i);
      b.setAttribute('aria-selected', j === i ? 'true' : 'false');
    });
  };

  highlight(slider.value);
  slider.addEventListener('input', () => highlight(slider.value));
  slider.addEventListener('change', () => highlight(slider.value));
  labelBtns.forEach((btn) => {
    btn.addEventListener('click', () => highlight(btn.dataset.scenarioIdx));
  });
  cards.forEach((card) => {
    card.addEventListener('click', () => highlight(card.dataset.scenarioIdx));
  });
}

function saveAssessmentToServer(data) {
  fetchCurrentCustomer().then((customer) => {
    fetch('/api/assessments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        customer_id: customer?.id || '',
        customer_email: customer?.email || '',
        recommendation: data,
      }),
    }).catch(() => {});
  });
}
