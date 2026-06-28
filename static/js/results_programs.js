// Results — incentives & financing offers (live API panels)

function programsFetchHeaders() {
  const headers = { Accept: 'application/json' };
  const beta = sessionStorage.getItem('betaInviteToken') || window.BETA_INVITE_DEFAULT || '';
  if (beta) headers['X-Beta-Invite'] = beta;
  return headers;
}

function extractPostcodeFromRecommendation(d) {
  const ci = d.calculator_inputs || {};
  if (ci.postcode) return String(ci.postcode).trim().slice(0, 5);
  const name = d.location?.name || ci.location_name || '';
  const m = String(name).match(/\b(\d{5})\b/);
  return m ? m[1] : '';
}

function systemCostForOffers(d) {
  const pkg = d.three_packages?.packages?.[selectedPackageId] || d.selected_package || {};
  return (
    pkg.upfront_cost
    || d.financials?.system_cost_typical
    || d.system_recommendation?.estimated_cost_eur
    || 15000
  );
}

function renderIncentivesPanel(data) {
  if (!data?.programs?.length) {
    return `<p class="form-hint">${tr('results.incentives_none', 'No programs loaded for this postcode.')}</p>`;
  }
  const cards = data.programs.map((p) => {
    const typeLabel = tr(`results.incentive.type.${p.type}`, formatDisplayLabel(p.type));
    const statusLabel = tr(`results.incentive.status.${p.status}`, formatDisplayLabel(p.status));
    const link = p.url
      ? `<a href="${p.url}" target="_blank" rel="noopener noreferrer" class="program-link">${tr('results.incentive.learn_more', 'Learn more')} →</a>`
      : '';
    return `
      <article class="program-card program-card--${p.type || 'other'}">
        <div class="program-card-head">
          <span class="program-type-badge">${typeLabel}</span>
          <span class="program-status program-status--${(p.status || 'active').replace(/\s+/g, '_')}">${statusLabel}</span>
        </div>
        <h3 class="program-name">${p.name}</h3>
        <p class="program-detail">${p.detail || ''}</p>
        ${link}
      </article>`;
  }).join('');
  return `
    <p class="results-panel-sub">${tr('results.incentives_sub', 'Programs that may apply in {region} — verify eligibility before you commit.').replace('{region}', data.region || 'Germany')}</p>
    <div class="programs-grid">${cards}</div>
    <p class="scenario-disclaimer">${data.disclaimer || ''}</p>`;
}

function renderFinancingOffersPanel(data) {
  if (!data?.offers?.length) {
    return `<p class="form-hint">${tr('results.financing_offers_none', 'Financing offers unavailable.')}</p>`;
  }
  const cards = data.offers.map((o, idx) => `
    <article class="fin-offer-card${idx === 0 ? ' fin-offer-card--highlight' : ''}">
      <div class="fin-offer-head">
        <h3>${o.provider}</h3>
        ${o.badge ? `<span class="fin-offer-badge">${o.badge}</span>` : ''}
      </div>
      <div class="fin-offer-stats">
        <span><strong>${o.apr_pct}%</strong> ${tr('results.financing_apr', 'APR')}</span>
        <span><strong>${formatCurrency(o.monthly_eur)}</strong>/${tr('results.financing_per_month', 'mo')}</span>
        <span>${o.term_years} ${tr('results.financing_years', 'yr')}</span>
      </div>
      <p class="fin-offer-meta">${tr('results.financing_total', 'Total paid')}: ${formatCurrency(o.total_paid_eur)}</p>
    </article>`).join('');
  const baseline = data.baseline_monthly_eur != null
    ? `<p class="form-hint">${tr('results.financing_baseline', 'Our default model')}: ${data.baseline_apr_pct}% APR · ${formatCurrency(data.baseline_monthly_eur)}/${tr('results.financing_per_month', 'mo')}</p>`
    : '';
  return `
    <p class="results-panel-sub">${tr('results.financing_offers_sub', 'Illustrative green-loan comparison for ~{amount} — not an offer of credit.').replace('{amount}', formatCurrency(data.amount_eur))}</p>
    ${baseline}
    <div class="fin-offers-grid">${cards}</div>
    <p class="scenario-disclaimer">${data.disclaimer || ''}</p>`;
}

function renderProgramsPlaceholders() {
  return `
    <section class="result-section compact-section" id="incentivesSection">
      <div class="results-panel programs-panel">
        <span class="results-panel-kicker">${tr('results.incentives_kicker', 'Funding & policy')}</span>
        <h2 class="results-panel-title">${tr('results.incentives_title', 'Grants & incentives')}</h2>
        <div id="incentivesPanel"><p class="form-hint programs-loading">${tr('results.programs_loading', 'Loading programs…')}</p></div>
      </div>
    </section>
    <section class="result-section compact-section" id="financingOffersSection">
      <div class="results-panel programs-panel">
        <span class="results-panel-kicker">${tr('results.financing_offers_kicker', 'Loan comparison')}</span>
        <h2 class="results-panel-title">${tr('results.financing_offers_title', 'Green financing options')}</h2>
        <div id="financingOffersPanel"><p class="form-hint programs-loading">${tr('results.programs_loading', 'Loading programs…')}</p></div>
      </div>
    </section>`;
}

async function loadIncentivesAndFinancing(d) {
  const incEl = document.getElementById('incentivesPanel');
  const finEl = document.getElementById('financingOffersPanel');
  if (!incEl && !finEl) return;

  const postcode = extractPostcodeFromRecommendation(d);
  const amount = Math.round(systemCostForOffers(d));
  const term = d.financing_comparison?.loan?.term_years || 10;
  const headers = programsFetchHeaders();

  const tasks = [];
  if (incEl) {
    tasks.push(
      fetch(`/api/incentives?postcode=${encodeURIComponent(postcode)}`, { headers, credentials: 'same-origin' })
        .then((r) => r.json())
        .then((data) => { incEl.innerHTML = renderIncentivesPanel(data); })
        .catch(() => {
          incEl.innerHTML = `<p class="form-hint">${tr('results.incentives_error', 'Could not load incentives.')}</p>`;
        }),
    );
  }
  if (finEl) {
    tasks.push(
      fetch(`/api/financing-offers?amount=${amount}&term_years=${term}`, { headers, credentials: 'same-origin' })
        .then((r) => r.json())
        .then((data) => { finEl.innerHTML = renderFinancingOffersPanel(data); })
        .catch(() => {
          finEl.innerHTML = `<p class="form-hint">${tr('results.financing_offers_error', 'Could not load financing offers.')}</p>`;
        }),
    );
  }
  await Promise.all(tasks);
}
