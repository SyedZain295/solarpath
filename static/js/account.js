document.addEventListener('DOMContentLoaded', async () => {
  const guest = document.getElementById('accountGuest');
  const content = document.getElementById('accountContent');

  const customer = await fetchCurrentCustomer();
  if (!customer) {
    guest.classList.remove('hidden');
    return;
  }

  content.classList.remove('hidden');
  document.getElementById('accountProfile').innerHTML = `
    <h2>${customer.name}</h2>
    <p>${customer.email} · ${customer.postcode || ''}</p>
  `;

  document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
    clearCustomerCache();
    window.location.href = '/login';
  });

  const [assessments, quotes, docs] = await Promise.all([
    fetch('/api/assessments', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : []).catch(() => []),
    fetch('/api/quotes', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : []).catch(() => []),
    fetch('/api/documents', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : []).catch(() => []),
  ]);

  const recent = assessments.slice(-5).reverse();
  const assessEl = document.getElementById('assessmentsList');
  if (!recent.length) {
    assessEl.innerHTML = `<p class="form-hint">${tr('account.js.no_assessments', 'No saved assessments yet.')} <a href="/calculator">${tr('account.js.run_calculator', 'Run the calculator')}</a>.</p>`;
  } else {
    assessEl.innerHTML = recent.map((a, i) => {
      const r = a.recommendation || {};
      return `<div class="account-card">
        <strong>${new Date(a.created_at).toLocaleDateString()}</strong>
        <span>${r.system_kwp || '—'} kWp · ${(r.readiness && r.readiness.label) || tr('account.js.assessment', 'Assessment')}</span>
        <button type="button" class="btn btn-outline btn-sm view-assess-btn" data-idx="${i}">${tr('account.js.view_results', 'View results')}</button>
      </div>`;
    }).join('');
    assessEl.querySelectorAll('.view-assess-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        sessionStorage.setItem('solarRecommendation', JSON.stringify(recent[btn.dataset.idx].recommendation));
        window.location.href = '/results';
      });
    });
  }

  const quotesEl = document.getElementById('quotesList');
  if (!quotes.length) {
    quotesEl.innerHTML = `<p class="form-hint">${tr('account.js.no_quotes', 'No quote requests yet.')}</p>`;
  } else {
    quotesEl.innerHTML = quotes.map(q => `
      <div class="account-card">
        <strong>${q.id}</strong> · ${q.lead_tier || 'basic'} ${tr('account.js.lead', 'lead')}
        <div class="quote-status-track compact">${(q.status_timeline || []).map(s =>
          `<span class="quote-status-step ${s.done ? 'done' : ''} ${s.current ? 'current' : ''}">${s.label}</span>`
        ).join('')}</div>
      </div>
    `).join('');
  }

  renderDocs(Array.isArray(docs) ? docs : []);

  document.getElementById('docForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const resp = await fetch('/api/documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        title: f.title.value,
        doc_type: f.doc_type.value,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      alert(err.error || tr('account.js.doc_failed', 'Could not save document.'));
      return;
    }
    f.reset();
    const listResp = await fetch('/api/documents', { credentials: 'same-origin' });
    if (listResp.ok) {
      renderDocs(await listResp.json());
    }
  });
});

function renderDocs(docs) {
  const el = document.getElementById('documentsList');
  if (!el || !Array.isArray(docs) || !docs.length) {
    if (el) el.innerHTML = `<p class="form-hint">${tr('account.js.no_docs', 'No documents stored yet.')}</p>`;
    return;
  }
  el.innerHTML = docs.map(d => `
    <div class="account-card"><strong>${d.title}</strong> <span class="form-hint">${d.doc_type} · ${new Date(d.created_at).toLocaleDateString()}</span></div>
  `).join('');
}
