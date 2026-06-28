// Results – three-package comparison, financial model, energy advisor sections

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
let selectedPackageId = 'best_value';

function formatLocation(name) {
  if (!name) return tr('results.location_fallback', 'Your location');
  const parts = name.split(',').map(s => s.trim()).filter(Boolean);
  if (parts.length >= 2) return `${parts[0]} · ${parts[1]}`;
  return parts[0] || name;
}

function formatDisplayLabel(value) {
  if (value == null || value === '') return '—';
  return String(value)
    .replace(/_/g, ' ')
    .trim()
    .split(/\s+/)
    .map(word => {
      const lower = word.toLowerCase();
      if (lower === 'kwh') return 'kWh';
      if (lower === 'kwp') return 'kWp';
      if (lower === 'ev') return 'EV';
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

document.addEventListener('DOMContentLoaded', () => {
  const raw = sessionStorage.getItem('solarRecommendation') || localStorage.getItem('solarRecommendation');
  if (!raw) {
    document.getElementById('resultsLoading').classList.add('hidden');
    document.getElementById('resultsError').classList.remove('hidden');
    return;
  }
  const data = JSON.parse(raw);
  const rec = data.selected_package || data.three_packages?.packages?.best_value;
  if (rec) selectedPackageId = rec.id || 'best_value';
  renderResults(data);
  document.getElementById('resultsLoading').classList.add('hidden');
  document.getElementById('resultsContent').classList.remove('hidden');
  setupQuoteModal(data);
  setupPDFDownload(data);
  setupPriceScenarioSlider();
  saveAssessmentToServer(data);
});

function renderResults(d) {
  const conf = d.confidence || {};
  const loc = d.location || {};
  const pkgs = d.three_packages?.packages || {};
  const tradeoffs = d.three_packages?.tradeoffs || {};

  document.getElementById('resultsContent').innerHTML = `
    <div class="results-header">
      <div class="confidence-badge confidence-${conf.level || 'medium'}">
        ${conf.score_label || tr('results.completeness_index', 'Information completeness')} · ${conf.score ?? '—'} · ${conf.estimated_accuracy || '±15%'}
      </div>
      <h1>${tr('results.report_title', 'Your Solar Decision Report')}</h1>
      <p class="results-header-loc">${formatLocation(loc.name)}</p>
      ${conf.summary ? `<p class="results-header-summary">${conf.summary}</p>` : ''}
      ${renderLeadTier(d.lead_qualification)}
      ${renderYieldValidation(d.yield_validation)}
      ${d.pvgis_fallback ? `<div class="info-box pvgis-fallback-notice">${d.pvgis_notice || tr('results.pvgis_fallback', 'Live solar data unavailable — regional estimate used.')}</div>` : ''}
      ${renderBrandedIntakeBanner(d.source_installer, d.source_installer_slug)}
    </div>

    ${renderTrustGlossary()}

    ${renderSystemRecommendation(d.system_recommendation, d.sizing_summary)}
    ${renderReadiness(d.readiness)}
    ${renderGoalDecisions(d.goal_decisions || [])}
    ${renderEvAssessment(d.ev_assessment)}
    ${renderHpAssessment(d.hp_assessment)}
    ${renderWhyExplanation(d.why_explanation, d.why_recommend)}
    ${d.solar_viable === false ? renderApartmentPath(d.apartment_path) : ''}
    ${renderBudgetFirst(d.budget_first)}
    ${renderHouseholdProfile(d.household_profile)}

    <section class="result-section">
      <div class="results-panel packages-panel">
        <span class="results-panel-kicker">${tr('results.packages_kicker', 'Compare options')}</span>
        <h2 class="results-panel-title">${tr('results.choose_tradeoff', 'Choose your trade-off')}</h2>
        <p class="results-panel-sub">${tr('results.choose_tradeoff_sub', 'Three honest packages - lowest cost, best long-term value, or best backup resilience.')}</p>
        <div class="packages-grid" id="packagesGrid">
          ${renderPackageCard(pkgs.cheapest, tradeoffs.cheapest_gives_up)}
          ${renderPackageCard(pkgs.best_value, tradeoffs.best_value_gives_up)}
          ${renderPackageCard(pkgs.most_reliable, tradeoffs.most_reliable_gives_up)}
        </div>
      </div>
    </section>

    ${renderEnergyEconomics(d.energy_economics, d.battery_comparison)}
    ${renderPriceScenarios(d.price_scenarios)}
    ${renderFinancingComparison(d.financing_comparison)}
    ${renderUsageBreakdown(d.usage_breakdown || [])}
    ${renderMeterTimeline(d.meter_timeline || {})}
    ${renderFinancialModel(pkgs[selectedPackageId]?.financial_model || d.financial_model)}
    ${renderVerificationFramework()}
    ${renderMatchedSuppliers(d.matched_suppliers)}
    ${renderQuoteChecklist(d.quote_quality_checklist)}
    ${renderConfidence(conf)}
    ${renderReportExtras(d)}
    ${renderProjectTracker(d.legal_checklist || [])}
    ${renderEnergyRoadmap(d.energy_roadmap)}
    ${renderProfileAndTech(d)}
    ${renderDecisionReportBanner(d.decision_report)}

    <div class="action-bar">
      <button class="btn btn-primary btn-lg" id="requestQuotesBtn">${tr('results.request_quotes', 'Request installer quotes')}</button>
      <a href="/compare-quotes" class="btn btn-outline">${tr('results.go_to_compare', 'Compare installer quotes')}</a>
      <label class="checkbox-inline pdf-privacy-opt">
        <input type="checkbox" id="pdfIncludeContact">
        ${tr('results.pdf_include_contact', 'Include my name/email in PDF when sharing with installers')}
      </label>
      <button class="btn btn-outline" id="downloadPdfBtn">${tr('results.download_pdf', 'Download PDF Report')}</button>
      <button class="btn btn-outline" id="emailReportBtn">${tr('results.send_installer', 'Send to Installer')}</button>
      <a href="/energy-advisor" class="btn btn-outline">${tr('results.energy_tips', 'Energy Savings Tips')}</a>
      <a href="/calculator" class="btn btn-outline">${tr('results.recalculate', 'Recalculate')}</a>
    </div>

    <div class="disclaimer-box">${d.disclaimer || ''}</div>
  `;

  document.querySelectorAll('.package-card').forEach(card => {
    card.addEventListener('click', () => {
      selectedPackageId = card.dataset.packageId;
      document.querySelectorAll('.package-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      d.selected_package_id = selectedPackageId;
      sessionStorage.setItem('solarRecommendation', JSON.stringify(d));
      fetch('/api/beta/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: 'package_select', payload: { package_id: selectedPackageId } }),
      }).catch(() => {});
      const pkgs = d.three_packages?.packages || {};
      const fmHtml = renderFinancialModel(pkgs[selectedPackageId]?.financial_model || d.financial_model);
      const fmEl = document.querySelector('.financial-model-section');
      if (fmEl && fmHtml) {
        const wrap = document.createElement('div');
        wrap.innerHTML = fmHtml;
        fmEl.replaceWith(wrap.firstElementChild);
      }
    });
  });

  document.getElementById('requestQuotesBtn')?.addEventListener('click', openQuoteModal);
}

function renderBrandedIntakeBanner(installer, slug) {
  if (!installer && !slug) return '';
  const name = installer?.company_name || slug;
  return `
    <div class="branded-intake-banner">
      <p>${tr('results.branded_intake', 'Your project brief will be sent directly to')} <strong>${name}</strong></p>
    </div>`;
}

function renderCompatibilityBadges(compat) {
  if (!compat) return '';
  const items = [
    ['dc_ok', 'results.compat.dc_ok', 'Inverter sized correctly', compat.inverter_dc_ok !== false],
    ['battery', 'results.compat.battery_ok', 'Battery compatible', compat.battery_compatible !== false],
    ['backup', 'results.compat.backup_ok', 'Backup capable', compat.backup_available !== false],
  ];
  return `<div class="compat-badges">${items.map(([kind, key, fallback, ok]) =>
    `<span class="compat-badge compat-badge--${kind} ${ok ? 'ok' : 'warn'}">${ok ? '✓' : '○'} ${tr(key, fallback)}</span>`
  ).join('')}</div>`;
}

function renderSystemRecommendation(rec, sizing) {
  if (!rec) return '';
  const spec = rec.product_spec || {};
  const panel = spec.panel || {};
  const inv = spec.inverter || {};
  const roof = spec.roof_check || {};
  const headline = tr('results.system_rec_headline', 'We recommend a {kwp} kWp system')
    .replace('{kwp}', rec.headline_kwp)
    .replace('{production}', (rec.annual_production_kwh || 0).toLocaleString());

  let roofMsg = '';
  if (roof.status === 'ok') {
    roofMsg = tr('results.roof_ok', '').replace('{required}', roof.required_m2).replace('{available}', roof.available_m2);
  } else if (roof.status === 'too_small') {
    roofMsg = tr('results.roof_too_small', '').replace('{required}', roof.required_m2).replace('{available}', roof.available_m2);
  } else {
    roofMsg = tr('results.roof_unknown', '');
  }

  const sizingBlock = sizing ? `
    <div class="sizing-breakdown">
      <h3>${tr('results.sizing_title', 'How we sized your system')}</h3>
      <div class="sizing-stats">
        <div class="sizing-stat sizing-stat--formula">
          <span class="sizing-stat-label">${tr('results.sizing_formula', 'Annual use ÷ yield')}</span>
          <strong>${sizing.formula_text} → ${sizing.recommended_kwp} kWp</strong>
        </div>
        <div class="sizing-stat sizing-stat--yield">
          <span class="sizing-stat-label">${tr('results.sizing_yield', 'Specific yield')}</span>
          <strong>${sizing.specific_yield_kwh_kwp.toLocaleString()} kWh/kWp/yr</strong>
        </div>
        <div class="sizing-stat sizing-stat--production">
          <span class="sizing-stat-label">${tr('results.sizing_production', 'Expected production')}</span>
          <strong>${sizing.annual_production_kwh.toLocaleString()} kWh/yr</strong>
        </div>
        <div class="sizing-stat sizing-stat--coverage">
          <span class="sizing-stat-label">${tr('results.sizing_coverage', 'Coverage').replace('{pct}', sizing.coverage_pct)}</span>
          <strong>~${sizing.coverage_pct}%</strong>
        </div>
        ${sizing.roof_max_kwp ? `
        <div class="sizing-stat sizing-stat--roof">
          <span class="sizing-stat-label">${tr('results.sizing_roof_cap', 'Roof limit')}</span>
          <strong>~${sizing.roof_max_kwp} kWp max</strong>
        </div>` : ''}
      </div>
      ${sizing.demand_note ? `<p class="sizing-roof-note warn">${sizing.demand_note}</p>` : ''}
      ${sizing.capped_by_roof ? `<p class="sizing-roof-note">${tr('results.sizing_roof_capped', 'Recommended size was reduced to fit available roof area — total demand may exceed what the roof can host.')}</p>` : ''}
      ${(sizing.roof_limit_next_steps || []).length ? `
        <div class="roof-limit-next-steps info-box">
          <strong>${tr('results.roof_limit_title', 'When roof area is the limiting factor')}</strong>
          <ul>${sizing.roof_limit_next_steps.map((s) => `<li>${s}</li>`).join('')}</ul>
        </div>` : ''}
      <p class="sizing-source">${sizing.data_source === 'PVGIS' ? tr('results.sizing_source_pvgis', '') : tr('results.sizing_source_est', '')}</p>
    </div>
  ` : '';

  const batteryLine = rec.battery_kwh > 0
    ? tr('results.system_rec_battery', '').replace('{battery}', rec.battery_label).replace('{kwh}', rec.battery_kwh)
    : tr('results.system_rec_no_battery', '');

  return `
    <section class="result-section system-rec-hero">
      <div class="system-rec-panel">
        <h2 class="section-title">${tr('results.system_rec_title', 'Your recommended system')}</h2>
        <p class="section-sub">${tr('results.system_rec_sub', '')}</p>
        <div class="system-rec-card">
          <div class="system-rec-headline-wrap">
            <span class="system-rec-kicker">${tr('results.recommended', 'Recommended')}</span>
            <p class="system-rec-headline">${headline}</p>
          </div>
          <ul class="system-rec-components">
            <li class="system-rec-component system-rec-component--panel">
              <span class="system-rec-component-icon" aria-hidden="true">☀</span>
              <span>${tr('results.system_rec_panels', '').replace('{qty}', panel.quantity || rec.num_panels).replace('{panel}', rec.panel_label).replace('{wp}', panel.power_wp || '')}</span>
            </li>
            <li class="system-rec-component system-rec-component--inverter">
              <span class="system-rec-component-icon" aria-hidden="true">⚡</span>
              <span>${tr('results.system_rec_inverter', '').replace('{inverter}', rec.inverter_label).replace('{kw}', inv.ac_power_kw || '')}</span>
            </li>
            <li class="system-rec-component system-rec-component--battery">
              <span class="system-rec-component-icon" aria-hidden="true">🔋</span>
              <span>${batteryLine}</span>
            </li>
          </ul>
          <div class="system-rec-metrics">
            <div class="system-rec-metric system-rec-metric--cost">
              <span class="system-rec-metric-icon" aria-hidden="true">€</span>
              <div class="system-rec-metric-body">
                <span>${tr('results.system_rec_cost', 'Est. cost')}</span>
                <strong>${formatCurrency(rec.estimated_cost_eur)}</strong>
              </div>
            </div>
            <div class="system-rec-metric system-rec-metric--savings">
              <span class="system-rec-metric-icon" aria-hidden="true">↓</span>
              <div class="system-rec-metric-body">
                <span>${tr('results.system_rec_savings', 'Year-1 savings')}</span>
                <strong>${formatCurrency(rec.annual_savings_eur)}/yr</strong>
              </div>
            </div>
            <div class="system-rec-metric system-rec-metric--package">
              <span class="system-rec-metric-icon" aria-hidden="true">★</span>
              <div class="system-rec-metric-body">
                <span>${tr('results.system_rec_package', 'Package')}</span>
                <strong>${rec.package_label || ''}</strong>
              </div>
            </div>
          </div>
          <p class="system-rec-roof ${roof.status === 'too_small' ? 'warn' : ''}">${roofMsg}</p>
          ${renderCompatibilityBadges(spec.compatibility)}
          <p class="system-rec-catalog-note">${tr('results.catalog_note', '')}</p>
        </div>
        ${sizingBlock}
      </div>
    </section>`;
}

function renderGoalDecisions(decisions) {
  if (!decisions.length) return '';
  const rows = decisions.map(gd => `
    <div class="goal-insight-row">
      <span class="goal-insight-tag">${gd.icon} ${gd.goal_label}</span>
      <span class="goal-insight-arrow" aria-hidden="true">→</span>
      <strong class="goal-insight-rec">${gd.primary}</strong>
      <span class="goal-insight-dot" aria-hidden="true">·</span>
      <span class="goal-insight-note">${gd.battery_note}</span>
    </div>
  `).join('');

  return `
    <section class="goal-insight-section" aria-label="Goal to technology decision">
      <p class="goal-insight-label">${tr('results.goal_decision', 'Goal to Technology Decision')}</p>
      <div class="goal-insight-strip">${rows}</div>
    </section>`;
}

function renderPackageCard(pkg, givesUp) {
  if (!pkg) return '';
  const selected = pkg.id === selectedPackageId || pkg.recommended;
  const tradeoffList = (pkg.tradeoffs || givesUp || []).map(t => `<li>${t}</li>`).join('');
  return `
    <div class="package-card package-card--${pkg.id || 'default'} ${selected ? 'selected' : ''} ${pkg.recommended ? 'recommended' : ''}" data-package-id="${pkg.id}">
      ${pkg.recommended ? `<span class="package-rec-badge">${tr('results.recommended', 'Recommended')}</span>` : ''}
      <div class="package-badge">${pkg.badge}</div>
      <h3>${pkg.label}</h3>
      <p class="package-sub">${pkg.subtitle}</p>
      ${pkg.product_spec ? `<p class="package-spec-line">${pkg.product_spec.num_panels}× ${pkg.product_spec.panel?.brand} · ${pkg.product_spec.system_kwp_actual} kWp</p>` : ''}
      <div class="package-price">${formatCurrency(pkg.upfront_cost)}</div>
      <div class="package-metrics">
        <div><span>${tr('results.monthly_savings', 'Monthly savings')}</span><strong>${formatCurrency(pkg.monthly_savings)}</strong></div>
        <div><span>${tr('results.annual_savings', 'Annual savings')}</span><strong>${formatCurrency(pkg.annual_savings)}</strong></div>
        <div><span>${tr('results.export_income', 'Export income')}</span><strong>${formatCurrency(pkg.export_income_annual)}/yr</strong></div>
        <div><span>${tr('results.battery', 'Battery')}</span><strong>${pkg.battery_kwh ? pkg.battery_kwh + ' kWh' : tr('results.none_short', 'None')}</strong></div>
        <div><span>${tr('results.self_consumption', 'Self-consumption')}</span><strong>${pkg.self_consumption_ratio}%</strong></div>
        <div><span>${tr('results.payback', 'Payback')}</span><strong>${pkg.payback_years} yrs</strong></div>
        <div><span>${tr('results.net_10yr', '10-yr net benefit')}</span><strong class="text-green">${formatCurrency(pkg.savings_10yr)}</strong></div>
        <div><span>${tr('results.net_20yr', '20-yr net benefit')}</span><strong>${formatCurrency(pkg.savings_20yr)}</strong></div>
        <div><span>${tr('results.backup', 'Backup')}</span><strong>${pkg.backup_capable ? tr('results.yes', 'Yes') : tr('results.no', 'No')}</strong></div>
        <div><span>${tr('results.warranty', 'Warranty')}</span><strong>${pkg.warranty_years} yrs</strong></div>
        <div><span>${tr('results.co2_saved', 'CO2 saved')}</span><strong>${pkg.co2_reduction_tonnes} t/yr</strong></div>
        <div><span>${tr('results.component_tier', 'Component tier')}</span><strong>${packageComponentTier(pkg)}</strong></div>
      </div>
      ${tradeoffList ? `<div class="package-tradeoffs"><strong>${tr('results.you_give_up', 'You give up')}:</strong><ul>${tradeoffList}</ul></div>` : ''}
      <button class="btn btn-outline btn-sm btn-block select-pkg-btn">${tr('results.select_package', 'Select this package')}</button>
    </div>`;
}

function renderUsageBreakdown(breakdown) {
  if (!breakdown.length) return '';
  const maxCost = breakdown[0]?.annual_cost_eur || 1;
  const bars = breakdown.map(b => `
    <div class="usage-row">
      <div class="usage-label">${b.icon} ${b.label}</div>
      <div class="usage-bar-wrap">
        <div class="usage-bar" style="width:${(b.annual_cost_eur / maxCost) * 100}%"></div>
      </div>
      <div class="usage-cost">${formatCurrency(b.annual_cost_eur)}/yr · ${b.pct}%</div>
    </div>
    <div class="usage-tips">${b.tips.slice(0, 2).map(t => `<span class="tip-chip">${t}</span>`).join('')}</div>
  `).join('');
  return `
    <section class="result-section">
      <div class="results-panel usage-panel">
        <span class="results-panel-kicker">${tr('results.usage_kicker', 'Your consumption')}</span>
        <h2 class="results-panel-title">${tr('results.usage_breakdown', 'Where your electricity goes')}</h2>
        <p class="results-panel-sub">${tr('results.usage_breakdown_sub', 'Focus on the highest-cost areas first - especially helpful for low-income households and apartments.')}</p>
        <div class="usage-breakdown-body">${bars}</div>
      </div>
    </section>`;
}

function renderMeterTimeline(mt) {
  if (!mt.current) return '';
  return `
    <section class="result-section compact-section">
      <div class="timeline-panel">
        <div class="timeline-panel-header">
          <h2 class="timeline-panel-title">${tr('results.cost_timeline', 'Electricity cost timeline')}</h2>
          <p class="timeline-panel-sub">${mt.note || ''}</p>
        </div>
        <div class="timeline-comparison">
          <div class="timeline-stat">
            <span class="timeline-stat-label">${tr('results.current', 'Current')}</span>
            <span class="timeline-stat-value">${formatCurrency(mt.current.annual_cost)}<span class="timeline-stat-unit">/yr</span></span>
            <span class="timeline-stat-foot">${formatNumber(mt.current.monthly_kwh)} kWh/month</span>
          </div>
          <div class="timeline-stat timeline-stat--risk">
            <span class="timeline-stat-label">${tr('results.ten_year_without_solar', '10 years without solar')}</span>
            <span class="timeline-stat-value">${formatCurrency(mt.ten_year_cost_without)}</span>
            <span class="timeline-stat-foot">${tr('results.cumulative_price_rise', 'Cumulative - 4%/yr price rise')}</span>
          </div>
          <div class="timeline-stat timeline-stat--win">
            <span class="timeline-stat-label">${tr('results.ten_year_with_solar', '10 years with solar')}</span>
            <span class="timeline-stat-value">${formatCurrency(mt.ten_year_cost_with)}</span>
            <span class="timeline-stat-foot">${tr('results.save', 'Save')} ${formatCurrency(mt.ten_year_savings)}</span>
          </div>
        </div>
        <div class="timeline-panel-foot">
          <span class="timeline-foot-icon" aria-hidden="true">i</span>
          <p><strong>${tr('results.smart_meter', 'Smart meter connection')}:</strong> ${tr('results.smart_meter_sub', 'Link your meter later for actual half-hourly data and personalised forecasts.')}</p>
        </div>
      </div>
    </section>`;
}

function renderFinancialModel(fm) {
  if (!fm) return '';
  const fin = fm.financing || {};
  const scenarios = Object.entries(fm.scenarios || {}).slice(0, 6).map(([k, s]) =>
    `<tr><td>${s.production} prod / ${s.electricity_price} price</td><td>${formatCurrency(s.annual_savings_yr1)}/yr</td><td>${s.payback_years} yrs</td><td>${formatCurrency(s.net_10yr)}</td></tr>`
  ).join('');
  return `
    <section class="result-section financial-model-section">
      <div class="results-panel financial-model-panel">
        <span class="results-panel-kicker">${tr('results.financial_model_kicker', 'Detailed projections')}</span>
        <h2 class="results-panel-title">${tr('results.full_financial_model', 'Full financial model')}</h2>
        <div class="financial-model-body">
          <div class="metrics-grid financial-model-metrics">
            <div class="metric-card metric-card--cost"><div class="value">${formatCurrency(fm.upfront_cost)}</div><div class="label">${tr('results.upfront_cost', 'Upfront cost')}</div></div>
            <div class="metric-card metric-card--finance"><div class="value">${formatCurrency(fin.monthly_payment)}/mo</div><div class="label">${tr('results.financing', 'Financing')} (${fin.apr_pct}% APR)</div></div>
            <div class="metric-card metric-card--maint"><div class="value">${formatCurrency(fm.maintenance_annual)}</div><div class="label">${tr('results.maintenance', 'Maintenance')}/yr</div></div>
          </div>
          <p class="financial-model-hint">Battery replacement ~year ${fm.battery_replacement?.year} (${formatCurrency(fm.battery_replacement?.estimated_cost || 0)}). Inverter ~year ${fm.inverter_replacement?.year}.</p>
          <table class="components-table financial-model-table">
            <thead><tr><th>${tr('results.scenario', 'Scenario')}</th><th>${tr('results.year1_savings', 'Year-1 savings')}</th><th>${tr('results.payback', 'Payback')}</th><th>${tr('results.net_10yr_short', '10-yr net')}</th></tr></thead>
            <tbody>${scenarios}</tbody>
          </table>
        </div>
      </div>
    </section>`;
}

function confidenceScorePalette(score) {
  return scoreColorPalette(score);
}

function renderConfidence(conf) {
  const score = conf.score ?? 0;
  const level = conf.level || 'medium';
  const factors = conf.factors || [];
  const missing = conf.missing_data || [];
  const palette = confidenceScorePalette(score);
  const scoreLabel = conf.score_label || tr('results.completeness_index', 'Information completeness index');

  const factorRows = factors.map(f => `
    <div class="conf-factor conf-factor-ok">
      <span class="conf-factor-icon" aria-hidden="true">✓</span>
      <span class="conf-factor-name">${f.item}</span>
    </div>
  `).join('');

  const missingChips = missing.map(m =>
    `<span class="conf-missing-chip">${m}</span>`
  ).join('');

  return `
    <section class="result-section confidence-section">
      <div class="confidence-panel confidence-panel-${level}">
        <header class="confidence-panel-header">
          <div class="confidence-panel-header-main">
            <div class="confidence-panel-icon" aria-hidden="true">🎯</div>
            <div>
              <h2 class="confidence-panel-title">${tr('results.installation_check', 'Digital suitability check')}</h2>
              <p class="confidence-panel-sub">${tr('results.installation_check_sub', 'How complete is the information behind this estimate?')}</p>
            </div>
          </div>
        </header>
        <div class="confidence-panel-body">
          <div class="confidence-score-block" style="--score-color:${palette.color};--score-glow:${palette.glow};--score-soft:${palette.soft}">
            <div class="confidence-ring" style="--score:${score};--ring-color:${palette.color};--ring-track:${palette.track}" aria-hidden="true">
              <div class="confidence-ring-inner">
                <span class="confidence-ring-value" style="color:${palette.color}">${score}</span>
                <span class="confidence-ring-of">${tr('results.index_suffix', 'index')}</span>
              </div>
            </div>
            <span class="confidence-level-tag" style="color:${palette.color}">${scoreLabel} · ${conf.label || 'Medium'}</span>
            <span class="confidence-accuracy">${conf.estimated_accuracy || '±15%'} ${tr('results.estimate_variance', 'estimate variance')}</span>
          </div>
          <div class="confidence-details">
            <p class="confidence-summary">${conf.summary || ''}</p>
            ${factors.length ? `<div class="confidence-factors">${factorRows}</div>` : ''}
            ${missing.length ? `
              <div class="confidence-missing">
                <span class="confidence-missing-title">${tr('results.improve_estimate', 'Improve your estimate')}</span>
                <div class="confidence-missing-chips">${missingChips}</div>
              </div>
            ` : ''}
          </div>
        </div>
        <div class="confidence-disclaimer">
          <span class="confidence-disclaimer-icon" aria-hidden="true">i</span>
          <p>${conf.survey_disclaimer || tr('results.survey_disclaimer', 'Final feasibility must be confirmed on site by an installer.')}</p>
        </div>
        <div class="confidence-disclaimer confidence-disclaimer-secondary">
          <span class="confidence-disclaimer-icon" aria-hidden="true">☀</span>
          <p>${conf.pvgis_limitation || ''}</p>
        </div>
      </div>
    </section>`;
}

function renderApartmentPath(ap) {
  if (!ap) return '';
  const opts = (ap.options || []).map(o => `
    <div class="lead-card">
      <h4>${o.name}</h4>
      <p>${o.description}</p>
      <p><strong>Est. savings:</strong> ${formatCurrency(o.annual_savings_eur)}/yr · Cost: ${o.typical_cost_eur ? formatCurrency(o.typical_cost_eur) : 'Free'}</p>
    </div>
  `).join('');
  return `
    <section class="result-section">
      <h2 class="section-title">${tr('results.no_rooftop_options', 'Options without rooftop solar')}</h2>
      <p class="section-sub">${ap.message || ''}</p>
      ${opts}
    </section>`;
}

function renderEnergyEconomics(eco, battCompare) {
  if (!eco) return '';
  const scPct = eco.self_consumption_share_of_savings_pct || 0;
  const feedPct = 100 - scPct;
  const ratioMsg = tr('results.self_use_worth_more', 'Each kWh you use yourself is worth about {ratio}× more than exporting it.')
    .replace('{ratio}', eco.export_premium_ratio || '—');

  const optIcons = ['🔋', '🚗', '🌡️', '📊', '⚡'];
  const optTones = ['battery', 'ev', 'heat', 'meter', 'tariff'];
  const optItems = [
    tr('results.opt_battery', 'Battery storage'),
    tr('results.opt_ev', 'Charge EV during solar peak hours'),
    tr('results.opt_heat_pump', 'Run heat pump when panels produce'),
    tr('results.opt_smart_meter', 'Smart meter & energy management system'),
    tr('results.opt_dynamic_tariff', 'Dynamic electricity tariff'),
  ].map((t, i) => `<li class="energy-econ-tip energy-econ-tip--${optTones[i]}"><span class="energy-econ-tip-icon" aria-hidden="true">${optIcons[i]}</span><span>${t}</span></li>`).join('');

  let battSection = '';
  if (battCompare?.with_battery) {
    const noB = battCompare.without_battery;
    const yesB = battCompare.with_battery;
    battSection = `
      <div class="energy-econ-battery">
        <h3>${tr('results.battery_compare_title', 'With vs without battery')}</h3>
        <p class="section-sub">${tr('results.battery_compare_sub', '')}</p>
        <div class="battery-compare-grid">
          <div class="battery-compare-col">
            <strong>${tr('results.without_battery', 'Without battery')}</strong>
            <span>${noB.self_consumption_ratio}% ${tr('results.self_consumption', 'Self-consumption')}</span>
            <span>${formatCurrency(noB.annual_savings)}/yr</span>
          </div>
          <div class="battery-compare-col highlight">
            <strong>${tr('results.with_battery', 'With battery')}</strong>
            <span>${yesB.self_consumption_ratio}% ${tr('results.self_consumption', 'Self-consumption')}</span>
            <span>${formatCurrency(yesB.annual_savings)}/yr</span>
          </div>
        </div>
      </div>`;
  }

  return `
    <section class="result-section">
      <div class="energy-econ-panel">
        <span class="energy-econ-kicker">${tr('results.energy_econ_kicker', 'Where your savings come from')}</span>
        <h2 class="energy-econ-title">${tr('results.energy_economics_title', 'Self-use vs grid export')}</h2>
        <p class="energy-econ-sub">${tr('results.energy_economics_sub', '')}</p>
        <p class="energy-econ-insight">${tr('results.energy_economics_insight', '')}</p>

        <div class="energy-econ-cards">
          <div class="energy-econ-card energy-econ-card--self-use">
            <span class="energy-econ-card-label">${tr('results.self_use_savings', 'Self-consumption savings')}</span>
            <strong class="energy-econ-card-value">${formatCurrency(eco.self_consumption_savings_annual)}</strong>
            <span class="energy-econ-card-meta">${eco.self_consumed_kwh?.toLocaleString()} ${tr('results.kwh_self_used', 'kWh on-site')} · ${eco.electricity_price_ct} ct/kWh</span>
            <span class="energy-econ-card-share">${Math.round(scPct)}% ${tr('results.of_savings', 'of savings')}</span>
          </div>
          <div class="energy-econ-card energy-econ-card--feed-in">
            <span class="energy-econ-card-label">${tr('results.feed_in_income', 'Feed-in income')}</span>
            <strong class="energy-econ-card-value">${formatCurrency(eco.feed_in_income_annual)}</strong>
            <span class="energy-econ-card-meta">${eco.exported_kwh?.toLocaleString()} ${tr('results.kwh_exported', 'kWh exported')} · ${eco.feed_in_rate_ct} ct/kWh</span>
            <span class="energy-econ-card-share">${Math.round(feedPct)}% ${tr('results.of_savings', 'of savings')}</span>
          </div>
        </div>

        <div class="energy-econ-total">
          <span>${tr('results.total_annual_benefit', 'Total annual benefit')}</span>
          <strong>${formatCurrency(eco.annual_savings_total)}</strong>
        </div>

        <p class="energy-econ-ratio">${ratioMsg}</p>

        <div class="energy-econ-warning">
          <strong>⚠ ${tr('results.feed_in_income', 'Feed-in')}</strong>
          <p>${tr('results.feed_in_warning', '')}</p>
        </div>

        <div class="energy-econ-optimize">
          <h3>${tr('results.optimization_title', 'Ways to improve your result')}</h3>
          <ul class="energy-econ-tips">${optItems}</ul>
        </div>

        ${battSection}

        <div class="energy-econ-tax">
          <h3>${tr('results.tax_note_title', 'Tax information')}</h3>
          <p>${tr('results.tax_note_body', '')}</p>
        </div>
      </div>
    </section>`;
}

function renderProjectTracker(steps) {
  const items = steps.map(s => {
    const title = tr(s.title_key || '', s.title || '');
    const detail = tr(s.detail_key || '', s.detail || '');
    const deadline = s.deadline_key ? `<p class="tracker-deadline">${tr(s.deadline_key, '')}</p>` : '';
    const warning = s.warning_key ? `<p class="tracker-warning">${tr(s.warning_key, '')}</p>` : '';
    return `
    <div class="tracker-step tracker-step--${(s.status || 'info').toLowerCase()}">
      <div class="tracker-step-top">
        <span class="tracker-num" aria-hidden="true">${s.step}</span>
        <span class="tracker-status">${s.status}</span>
      </div>
      <p class="tracker-title">${title}</p>
      <p class="tracker-detail">${detail}</p>
      ${deadline}${warning}
    </div>`;
  }).join('');
  return `
    <section class="result-section checklist-section">
      <div class="results-panel legal-checklist-panel">
        <span class="results-panel-kicker">${tr('results.legal_kicker', 'After you decide')}</span>
        <h2 class="results-panel-title">${tr('results.legal_checklist', 'Grid, registration and legal checklist')}</h2>
        <p class="results-panel-sub">${tr('results.legal_checklist_sub', 'Track each step from installer selection through feed-in setup and handover.')}</p>
        <div class="tracker-grid">${items}</div>
      </div>
    </section>`;
}

function renderProfileAndTech(d) {
  const profile = d.quote_ready_profile;
  if (!profile) return renderTechDetails(d);

  const goals = (profile.project?.goals || []).map(g => formatDisplayLabel(g)).join(', ');
  const docs = (profile.documents_needed || []).map(doc =>
    `<span class="doc-chip">${doc}</span>`
  ).join('');

  const why = (d.why_recommend || []).map(r =>
    `<li class="why-item">${r.replace(/\*\*/g, '')}</li>`
  ).join('');

  const components = (d.components || []).slice(0, 6).map(c =>
    `<tr><td>${c.name}</td><td class="col-qty">${c.quantity}</td><td class="col-cost">${formatCurrency(c.estimated_cost_eur)}</td></tr>`
  ).join('');

  const monthly = renderMonthlyChart(d.monthly_production_kwh, true);

  return `
    <section class="result-section compact-section">
      <div class="results-panel profile-tech-panel">
        <span class="results-panel-kicker">${tr('results.profile_kicker', 'For installers')}</span>
        <h2 class="results-panel-title">${tr('results.quote_ready_profile', 'Quote-ready profile and technical details')}</h2>
        <p class="results-panel-sub">${tr('results.quote_ready_profile_sub', 'Everything installers need for an accurate quote - sent with your request.')}</p>

      <div class="profile-stats-grid">
        <div class="profile-stat">
          <span class="profile-stat-label">${tr('results.profile.property', 'Property')}</span>
          <span class="profile-stat-value">${formatDisplayLabel(profile.property?.type)} · ${formatDisplayLabel(profile.property?.roof_type)}</span>
        </div>
        <div class="profile-stat">
          <span class="profile-stat-label">${tr('results.profile.annual_use', 'Annual use')}</span>
          <span class="profile-stat-value">${profile.consumption?.annual_kwh?.toLocaleString() || '—'} kWh/yr</span>
        </div>
        <div class="profile-stat">
          <span class="profile-stat-label">${tr('results.profile.goals', 'Goals')}</span>
          <span class="profile-stat-value">${goals || '—'}</span>
        </div>
        <div class="profile-stat">
          <span class="profile-stat-label">${tr('results.profile.system_size', 'System size')}</span>
          <span class="profile-stat-value">${profile.recommendation_summary?.system_kwp || '—'} kWp + ${profile.recommendation_summary?.battery_kwh || 0} kWh batt.</span>
        </div>
        <div class="profile-stat">
          <span class="profile-stat-label">${tr('results.profile.est_cost', 'Est. cost')}</span>
          <span class="profile-stat-value">${formatCurrency(profile.recommendation_summary?.estimated_cost || 0)}</span>
        </div>
        <div class="profile-stat">
          <span class="profile-stat-label">${tr('results.profile.confidence', 'Confidence')}</span>
          <span class="profile-stat-value">${formatDisplayLabel(profile.recommendation_summary?.confidence)}</span>
        </div>
      </div>

      ${docs ? `<div class="documents-bar"><span class="documents-label">${tr('results.profile.documents', 'Documents needed')}:</span>${docs}</div>` : ''}

      <div class="details-split">
        <div class="result-card detail-card">
          <h3>${tr('results.profile.why_title', 'Why we recommend this')}</h3>
          <ul class="why-list">${why}</ul>
        </div>
        <div class="result-card detail-card">
          <h3>${tr('results.profile.components', 'Key components')}</h3>
          <table class="components-table components-table-compact">
            <thead><tr><th>${tr('results.profile.component', 'Component')}</th><th>${tr('results.profile.qty', 'Qty')}</th><th>${tr('results.profile.est', 'Est.')}</th></tr></thead>
            <tbody>${components}</tbody>
          </table>
        </div>
      </div>

      ${monthly}
      </div>
    </section>`;
}

function renderTechDetails(d) {
  const why = (d.why_recommend || []).map(r => `<li class="why-item">${r.replace(/\*\*/g, '')}</li>`).join('');
  const components = (d.components || []).slice(0, 6).map(c =>
    `<tr><td>${c.name}</td><td class="col-qty">${c.quantity}</td><td class="col-cost">${formatCurrency(c.estimated_cost_eur)}</td></tr>`
  ).join('');
  return `
    <section class="result-section compact-section">
      <div class="results-panel profile-tech-panel">
        <span class="results-panel-kicker">${tr('results.profile_kicker', 'For installers')}</span>
        <h2 class="results-panel-title">${tr('results.tech_details', 'Technical details')}</h2>
      <div class="details-split">
        <div class="result-card detail-card">
          <h3>${tr('results.profile.why_title', 'Why we recommend this')}</h3>
          <ul class="why-list">${why}</ul>
        </div>
        <div class="result-card detail-card">
          <h3>${tr('results.profile.components', 'Key components')}</h3>
          <table class="components-table components-table-compact">
            <thead><tr><th>${tr('results.profile.component', 'Component')}</th><th>${tr('results.profile.qty', 'Qty')}</th><th>${tr('results.profile.est', 'Est.')}</th></tr></thead>
            <tbody>${components}</tbody>
          </table>
        </div>
      </div>
      ${renderMonthlyChart(d.monthly_production_kwh, true)}
      </div>
    </section>`;
}

function renderMonthlyChart(monthly, compact = false) {
  if (!monthly?.length) return '';
  const max = Math.max(...monthly);
  const barH = compact ? 88 : 120;
  const bars = monthly.map((v, i) => {
    const h = max > 0 ? Math.max(4, (v / max) * barH) : 4;
    return `<div class="chart-col" role="presentation">
      <div class="chart-bar" style="height:${h}px" title="${MONTHS[i]}: ${Math.round(v)} kWh"></div>
      <div class="chart-label">${MONTHS[i]}</div>
    </div>`;
  }).join('');
  const peak = Math.round(max);
  const peakLabel = tr('results.profile.peak', 'peak');
  const perMonth = tr('results.profile.per_month', 'kWh per month');
  return `<div class="result-card detail-card chart-card">
    <h3>${tr('results.profile.monthly_prod', 'Monthly production')}</h3>
    <p class="chart-axis-hint">${perMonth} · ${peakLabel} ${peak.toLocaleString()} kWh</p>
    <div class="chart-container chart-compact" role="img" aria-label="Monthly solar production chart">${bars}</div>
  </div>`;
}

function setupQuoteModal(data) {
  const modal = document.getElementById('quoteModal');
  const ci = data.calculator_inputs || {};
  const loc = data.location || {};
  document.getElementById('closeQuoteModal')?.addEventListener('click', () => modal.classList.add('hidden'));
  modal?.querySelector('.modal-backdrop')?.addEventListener('click', () => modal.classList.add('hidden'));

  const timeframeEl = document.getElementById('quote_timeframe');
  const seriousWrap = document.getElementById('confirmSeriousWrap');
  const toggleSerious = () => {
    if (!timeframeEl || !seriousWrap) return;
    seriousWrap.classList.toggle('hidden', timeframeEl.value !== 'not_sure');
  };
  timeframeEl?.addEventListener('change', toggleSerious);
  toggleSerious();

  document.getElementById('quoteForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const errBox = document.getElementById('quoteFormError');
    errBox?.classList.add('hidden');
    const supplierIds = [...document.querySelectorAll('.matched-supplier input:checked')].map(c => c.value);
    const brandedId = document.querySelector('.branded-supplier-id')?.value;
    const finalSupplierIds = brandedId ? [brandedId] : supplierIds;
    if (!finalSupplierIds.length) {
      errBox.textContent = tr('results.select_installer', 'Please select at least one installer.');
      errBox.classList.remove('hidden');
      return;
    }
    const firstName = form.customer_first_name.value.trim();
    const lastName = form.customer_name.value.trim();
    data.selected_package_id = selectedPackageId;
    const customer = await fetchCurrentCustomer();
    const intakeSlug = sessionStorage.getItem('intakeInstallerSlug') || data.source_installer_slug || '';
    const payload = {
      customer_id: customer?.id || '',
      customer_first_name: firstName,
      customer_name: lastName ? `${firstName} ${lastName}` : firstName,
      customer_email: form.customer_email.value.trim(),
      customer_phone: form.customer_phone.value.trim(),
      customer_postcode: form.customer_postcode.value.trim(),
      customer_town: form.customer_town.value.trim(),
      full_address: form.full_address?.value.trim() || '',
      preferred_contact_time: form.preferred_contact_time.value,
      owner_status: form.owner_status.value,
      installation_timeframe: form.installation_timeframe.value,
      confirm_serious: form.confirm_serious?.checked || false,
      battery_interest: form.battery_interest.value,
      financing_interest: form.financing_interest.value,
      consent_contact: form.consent_contact.checked,
      consent_share_installers: form.consent_share_installers.checked,
      message: form.message.value,
      recommendation: data,
      supplier_ids: finalSupplierIds,
      selected_package_id: selectedPackageId,
      selected_package: data.three_packages?.packages?.[selectedPackageId],
    };
    if (intakeSlug) payload.source_installer_slug = intakeSlug;
    try {
      const resp = await fetch('/api/quotes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const result = await resp.json();
      if (!resp.ok) {
        let msg = result.error_key ? tr(result.error_key, result.error) : (result.error || 'Failed');
        if (result.qualification?.rejection_reasons?.length) {
          const reasons = result.qualification.rejection_reasons.map(k => tr(k, k)).join('\n');
          msg += '\n\n' + reasons;
        }
        throw new Error(msg);
      }
      form.classList.add('hidden');
      const success = document.getElementById('quoteSuccess');
      success.classList.remove('hidden');
      if (result.quote?.status_timeline) {
        success.innerHTML = `<h3>${tr('results.quote_sent', 'Quote request sent!')}</h3>${renderQuoteStatusTimeline(result.quote.status_timeline)}<p><a href="/account">${tr('results.track_account', 'Track status in your account')} →</a></p><p style="margin-top:1rem"><a href="/compare-quotes" class="btn btn-outline btn-sm">${tr('results.go_to_compare', 'Compare quotes')}</a></p>`;
      }
      localStorage.setItem('lastQuoteId', result.quote_id);
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove('hidden');
    }
  });

  loadMatchedSuppliers(data);
  prefillQuoteForm(data, ci, loc);
}

function prefillQuoteForm(data, ci, loc) {
  const quoteForm = document.getElementById('quoteForm');
  if (!quoteForm) return;
  fetchCurrentCustomer().then((customerData) => {
    if (!customerData) return;
    if (customerData.name) {
      const parts = customerData.name.trim().split(/\s+/);
      quoteForm.customer_first_name.value = parts[0] || '';
      quoteForm.customer_name.value = parts.slice(1).join(' ') || '';
    }
    if (customerData.email) quoteForm.customer_email.value = customerData.email;
    if (customerData.phone) quoteForm.customer_phone.value = customerData.phone;
    if (customerData.postcode) quoteForm.customer_postcode.value = customerData.postcode;
  });

  const locName = loc.name || ci.location_name || '';
  const plzMatch = locName.match(/\b(\d{5})\b/);
  if (plzMatch && !quoteForm.customer_postcode.value) {
    quoteForm.customer_postcode.value = plzMatch[1];
  }
  const townPart = locName.split(',')[0]?.replace(/\d{5}/, '').trim();
  if (townPart && quoteForm.customer_town) quoteForm.customer_town.value = townPart;

  if (ci.owner_status && quoteForm.owner_status) quoteForm.owner_status.value = ci.owner_status;
  if (ci.installation_timeframe && quoteForm.installation_timeframe) {
    quoteForm.installation_timeframe.value = ci.installation_timeframe;
    document.getElementById('confirmSeriousWrap')?.classList.toggle('hidden', ci.installation_timeframe !== 'not_sure');
  }
  if (ci.battery_interest && quoteForm.battery_interest) quoteForm.battery_interest.value = ci.battery_interest;
  if (ci.financing_interest && quoteForm.financing_interest) quoteForm.financing_interest.value = ci.financing_interest;
}

function renderQuoteStatusTimeline(timeline) {
  return `<div class="quote-status-track">${(timeline || []).map(s =>
    `<div class="quote-status-step ${s.done ? 'done' : ''} ${s.current ? 'current' : ''}"><span>${s.label}</span></div>`
  ).join('')}</div>`;
}

async function loadMatchedSuppliers(data) {
  const container = document.getElementById('matchedSuppliers');
  const intakeSlug = sessionStorage.getItem('intakeInstallerSlug') || data.source_installer_slug;
  if (intakeSlug) {
    try {
      const resp = await fetch(`/api/installers/${encodeURIComponent(intakeSlug)}`);
      const installer = await resp.json();
      if (resp.ok) {
        container.innerHTML = `<p class="form-hint"><strong>${tr('results.branded_single', 'Direct request to')}:</strong> ${installer.company_name}</p>
          <input type="hidden" class="branded-supplier-id" value="${installer.id}">`;
        return;
      }
    } catch { /* fall through */ }
  }
  const list = data.matched_suppliers?.length ? data.matched_suppliers : null;
  try {
    let suppliers = list;
    if (!suppliers) {
      const resp = await fetch('/api/suppliers');
      suppliers = await resp.json();
      suppliers = suppliers.filter(s => s.verified).sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
    }
    container.innerHTML = '<p style="font-size:.85rem"><strong>' + tr('results.select_installers', 'Select installers to contact') + ':</strong></p>' +
      suppliers.map(s => `
        <label class="matched-supplier">
          <input type="checkbox" value="${s.id}" checked>
          <span>${s.company_name}</span>
          ${s.fit_label ? `<span class="verified-badge">${s.fit_label}</span>` : `<span class="verified-badge">${tr('results.verified_badge', 'Verified')}</span>`}
          <span class="form-hint">${s.fit_score ? `${tr('results.fit_label', 'Fit')} ${s.fit_score}/100` : (s.quality_score != null ? `${tr('results.quality_label', 'Quality')} ${s.quality_score}/100` : tr('suppliers.directory_listing', 'Public directory listing'))}${s.display_rating != null && s.display_reviews > 0 ? ` · ★ ${s.display_rating}` : ''}</span>
        </label>
      `).join('');
  } catch { container.innerHTML = `<p class="form-hint">${tr('results.suppliers_load_error', 'Could not load suppliers.')}</p>`; }
}

function openQuoteModal() { document.getElementById('quoteModal').classList.remove('hidden'); }

function setupPDFDownload(data) {
  const run = async () => {
    const includeContact = document.getElementById('pdfIncludeContact')?.checked;
    const customer = {};
    if (includeContact) {
      const name = prompt(tr('results.pdf_name_prompt', 'Your name (optional):')) || '';
      const email = prompt(tr('results.pdf_email_prompt', 'Your email (optional):')) || '';
      if (name) customer.name = name.trim();
      if (email) customer.email = email.trim();
    }
    await downloadPDF(data, customer);
  };
  document.getElementById('downloadPdfBtn')?.addEventListener('click', run);
  document.getElementById('downloadPdfBtnTop')?.addEventListener('click', run);
  document.getElementById('emailReportBtn')?.addEventListener('click', async () => {
    const email = prompt(tr('results.email_report_prompt', 'Installer email:'));
    if (!email?.trim()) return;
    data.selected_package_id = selectedPackageId;
    try {
      const resp = await fetch('/api/report/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: email.trim(),
          recommendation: data,
          customer: {},
          selected_package: data.three_packages?.packages?.[selectedPackageId],
        }),
      });
      const result = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        alert(tr('results.email_report_error', 'Could not send report.'));
        return;
      }
      if (result.mode === 'outbox') {
        alert(tr('results.email_report_outbox', 'SMTP not configured — report saved on server for delivery.'));
      } else {
        alert(tr('results.email_report_sent', 'Report sent successfully.'));
      }
    } catch {
      alert(tr('results.email_report_error', 'Could not send report.'));
    }
  });
}

async function downloadPDF(data, customer = {}) {
  data.selected_package_id = selectedPackageId;
  const resp = await fetch('/api/report/pdf', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recommendation: data, customer, selected_package: data.three_packages?.packages?.[selectedPackageId] }),
  });
  if (!resp.ok) { alert('PDF error'); return; }
  fetch('/api/beta/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: 'pdf_download', payload: {} }),
  }).catch(() => {});
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'solar-decision-report.pdf';
  a.click();
}
