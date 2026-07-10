// Project status dashboard – homeowner + paperwork checklist (I18N)

const PROJECT_STEP_KEYS = [
  'project.js.step_quote',
  'project.js.step_contract',
  'project.js.step_grid',
  'project.js.step_install',
  'project.js.step_meter',
  'project.js.step_mastr',
  'project.js.step_commission',
  'project.js.step_warranty',
];

const REQUIRED_DOCS = [
  { id: 'quote', key: 'project.doc.quote' },
  { id: 'contract', key: 'project.doc.contract' },
  { id: 'grid', key: 'project.doc.grid' },
  { id: 'mastr', key: 'project.doc.mastr' },
  { id: 'commission', key: 'project.doc.commission' },
  { id: 'warranty', key: 'project.doc.warranty' },
  { id: 'invoice', key: 'project.doc.invoice' },
];

function docStateKey(email) {
  return `projectDocs_${email || 'guest'}`;
}

function loadDocState(email) {
  return JSON.parse(localStorage.getItem(docStateKey(email)) || '{}');
}

function saveDocState(email, state) {
  localStorage.setItem(docStateKey(email), JSON.stringify(state));
}

document.addEventListener('DOMContentLoaded', async () => {
  const loading = document.getElementById('projectLoading');
  const content = document.getElementById('projectContent');
  const empty = document.getElementById('projectEmpty');

  const customer = await fetchCurrentCustomer();
  let quote = null;

  try {
    if (customer) {
      const resp = await fetch('/api/quotes', { credentials: 'same-origin' });
      if (resp.ok) {
        const quotes = await resp.json();
        if (Array.isArray(quotes) && quotes.length) {
          quote = quotes.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))[0];
        }
      }
    }
  } catch { /* ignore */ }

  loading?.classList.add('hidden');

  if (!quote && !sessionStorage.getItem('solarRecommendation')) {
    empty?.classList.remove('hidden');
    return;
  }

  const rec = quote?.recommendation || JSON.parse(sessionStorage.getItem('solarRecommendation') || '{}');
  const lp = quote?.lead_profile || {};
  const checklist = rec.legal_checklist || [];
  const docState = loadDocState(customer?.email);

  const title = quote
    ? tr('project.js.with_installer', 'Project with {name}').replace('{name}', quote.source_installer_name || tr('project.js.title', 'Your installer'))
    : tr('project.js.title', 'Your solar project');

  const steps = checklist.length
    ? checklist.map(s => ({
        step: s.step,
        title: tr(s.title_key || '', s.title || ''),
        detail: tr(s.detail_key || '', s.detail || ''),
        status: s.status || 'pending',
      }))
    : PROJECT_STEP_KEYS.map((key, i) => ({
        step: i + 1,
        title: tr(key, key),
        detail: '',
        status: 'pending',
      }));

  const docRows = REQUIRED_DOCS.map(d => {
    const done = !!docState[d.id];
    return `<label class="doc-check-row ${done ? 'done' : 'missing'}">
      <input type="checkbox" data-doc-id="${d.id}" ${done ? 'checked' : ''}> ${tr(d.key, d.id)}
    </label>`;
  }).join('');

  const missing = REQUIRED_DOCS.filter(d => !docState[d.id]);
  const missingBlock = missing.length
    ? `<div class="missing-docs-box"><strong>${tr('project.missing_docs', 'Missing documents')}:</strong> ${missing.map(d => tr(d.key, d.id)).join(', ')}</div>`
    : `<p class="form-hint">${tr('project.js.all_docs', 'All required documents marked received.')}</p>`;

  content.innerHTML = `
    <h2>${title}</h2>
    ${quote ? `<p class="form-hint">${tr('project.js.quote_id', 'Quote')}: ${quote.id} · ${new Date(quote.created_at).toLocaleDateString()}</p>` : ''}
    <div class="project-stats">
      <div><span>${tr('project.js.system', 'System')}</span><strong>${lp.preferences?.system_kwp || rec.system_kwp || '—'} kWp</strong></div>
      <div><span>${tr('project.js.annual_use', 'Annual use')}</span><strong>${lp.energy?.annual_kwh?.toLocaleString() || rec.financials?.annual_consumption_kwh?.toLocaleString() || '—'} kWh</strong></div>
      <div><span>${tr('project.js.status', 'Status')}</span><strong>${quote?.status || tr('project.js.planning', 'Planning')}</strong></div>
    </div>
    <h3>${tr('project.required_docs', 'Required documents')}</h3>
    <div class="doc-checklist">${docRows}</div>
    ${missingBlock}
    <h3>${tr('project.js.checklist_title', 'Checklist')}</h3>
    <div class="tracker-grid">${steps.map(s => `
      <div class="tracker-step">
        <div class="tracker-step-top">
          <span class="tracker-num">${s.step}</span>
          <span class="tracker-status">${s.status}</span>
        </div>
        <p class="tracker-title">${s.title}</p>
        ${s.detail ? `<p class="tracker-detail">${s.detail}</p>` : ''}
      </div>
    `).join('')}</div>
    <div class="maintenance-reminder">
      <h3>${tr('project.maintenance', 'Maintenance')}</h3>
      <p>${tr('project.maintenance_sub', '')}</p>
    </div>
    <p class="form-hint" style="margin-top:1rem"><a href="/account">${tr('project.js.documents_link', 'Documents')} →</a></p>
    <p style="margin-top:1rem">
      <a href="/compare-quotes" class="btn btn-outline btn-sm">${tr('results.go_to_compare', 'Compare quotes')}</a>
      <a href="/suppliers" class="btn btn-outline btn-sm">${tr('nav.suppliers', 'Installers')}</a>
    </p>
  `;
  content.classList.remove('hidden');

  content.querySelectorAll('.doc-checklist input').forEach(cb => {
    cb.addEventListener('change', () => {
      const state = loadDocState(customer?.email);
      state[cb.dataset.docId] = cb.checked;
      saveDocState(customer?.email, state);
      location.reload();
    });
  });
});
