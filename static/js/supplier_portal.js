// Supplier portal – registration & dashboard

document.addEventListener('DOMContentLoaded', () => {
  setupRegistration();
  setupDashboard();
});

function setupRegistration() {
  const form = document.getElementById('supplierRegisterForm');
  if (!form) return;

  const params = new URLSearchParams(window.location.search);
  const planParam = params.get('plan');
  if (planParam) {
    const radio = form.querySelector(`input[name="plan"][value="${planParam}"]`);
    if (radio) radio.checked = true;
  }

  const checkout = JSON.parse(sessionStorage.getItem('supplierCheckout') || 'null');
  if (checkout?.email && form.email) {
    form.email.value = checkout.email;
  }

  if (params.get('checkout') && checkout) {
    const note = document.createElement('p');
    note.className = 'checkout-success-note';
    note.textContent = tr('sd.js.checkout_note', 'Payment step complete ({id}). Finish your profile below.').replace('{id}', checkout.checkout_id);
    form.prepend(note);
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const params = new URLSearchParams(window.location.search);
    const checkout = JSON.parse(sessionStorage.getItem('supplierCheckout') || 'null');
    const checkoutId = params.get('checkout') || checkout?.checkout_id;
    if (!checkoutId) {
      alert(tr('sd.js.checkout_required', 'Please complete checkout before registering.'));
      window.location.href = '/suppliers/checkout';
      return;
    }

    const splitList = (val) => val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];

    const payload = {
      checkout_id: checkoutId,
      company_name: form.company_name.value,
      email: form.email.value,
      phone: form.phone.value,
      website: form.website.value,
      description: form.description.value,
      regions: splitList(form.regions.value),
      locations_served: splitList(form.postcodes.value),
      certifications: splitList(form.certifications.value),
      financing_options: splitList(form.financing.value),
      installation_availability: form.installation_availability.value,
      plan: form.querySelector('input[name="plan"]:checked')?.value || 'basic',
      earliest_survey_date: form.earliest_survey_date?.value || '',
      earliest_install_weeks: parseInt(form.earliest_install_weeks?.value, 10) || null,
      residential_available: form.residential_available?.checked !== false,
      commercial_available: form.commercial_available?.checked || false,
      battery_capable: form.battery_capable?.checked !== false,
      ev_charger_capable: form.ev_charger_capable?.checked || false,
      heat_pump_capable: form.heat_pump_capable?.checked || false,
      agricultural_available: form.agricultural_available?.checked || false,
    };

    try {
      const resp = await fetch('/api/suppliers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const err = await parseJsonResponse(resp);
        throw new Error(err.error || tr('sd.js.registration_failed', 'Registration failed'));
      }
      const supplier = await parseJsonResponse(resp);
      localStorage.setItem('supplierId', supplier.id);
      localStorage.setItem('supplierData', JSON.stringify(supplier));
      form.classList.add('hidden');
      document.querySelector('.register-switch')?.classList.add('hidden');
      document.getElementById('registerSuccess').classList.remove('hidden');
      try {
        const linkResp = await fetch(`/api/suppliers/${supplier.id}/intake-link`);
        const linkData = await linkResp.json();
        const intakeEl = document.getElementById('registerIntakeLink');
        if (linkResp.ok && linkData.intake_url && intakeEl) {
          intakeEl.classList.remove('hidden');
          intakeEl.innerHTML = `<strong>${tr('sd.intake_url', 'Your intake URL')}:</strong> <a href="${linkData.intake_url}">${linkData.intake_url}</a>`;
        }
      } catch { /* optional */ }
    } catch (err) {
      alert(tr('common.error_prefix', 'Error') + ': ' + err.message);
    }
  });
}

function setupDashboard() {
  const supplierId = localStorage.getItem('supplierId');
  const supplierData = localStorage.getItem('supplierData');

  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab)?.classList.add('active');
    });
  });

  if (supplierId) {
    document.getElementById('supplierId').value = supplierId;
    if (supplierData) {
      const s = JSON.parse(supplierData);
      fillProfileForm(s);
      renderProducts(s.products || []);
    }
    loadLeads(supplierId);
    loadIntakeLink(supplierId);
    loadAnalytics(supplierId);
  } else {
    loadIntakeLink(null);
  }

  document.getElementById('copyIntakeLink')?.addEventListener('click', () => {
    const input = document.getElementById('intakeLinkUrl');
    if (!input?.value) return;
    navigator.clipboard?.writeText(input.value).then(() => {
      alert(tr('sd.js.link_copied', 'Link copied to clipboard'));
    }).catch(() => {
      input.select();
      document.execCommand('copy');
    });
  });

  document.getElementById('profileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supplierId) { alert(tr('sd.js.register_first', 'Please register first.')); return; }

    const payload = {
      company_name: document.getElementById('dash_company').value,
      email: document.getElementById('dash_email').value,
      phone: document.getElementById('dash_phone').value,
      description: document.getElementById('dash_description').value,
      earliest_survey_date: document.getElementById('dash_survey_date')?.value || '',
      earliest_install_weeks: parseInt(document.getElementById('dash_install_weeks')?.value, 10) || null,
      residential_available: document.getElementById('dash_residential')?.checked !== false,
      commercial_available: document.getElementById('dash_commercial')?.checked || false,
      battery_capable: document.getElementById('dash_battery')?.checked !== false,
      ev_charger_capable: document.getElementById('dash_ev')?.checked || false,
      heat_pump_capable: document.getElementById('dash_hp')?.checked || false,
    };

    try {
      const resp = await fetch(`/api/suppliers/${supplierId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(tr('sd.js.update_failed', 'Update failed'));
      const updated = await resp.json();
      localStorage.setItem('supplierData', JSON.stringify(updated));
      alert(tr('sd.js.profile_updated', 'Profile updated!'));
    } catch (err) {
      alert(tr('common.error_prefix', 'Error') + ': ' + err.message);
    }
  });

  document.getElementById('addProductForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supplierId) { alert(tr('sd.js.register_first', 'Please register first.')); return; }

    const s = JSON.parse(localStorage.getItem('supplierData') || '{}');
    const products = s.products || [];
    products.push({
      id: crypto.randomUUID?.().slice(0, 8) || String(Date.now()),
      name: document.getElementById('prod_name').value,
      brand: document.getElementById('prod_brand')?.value || '',
      model: document.getElementById('prod_model')?.value || '',
      type: document.getElementById('prod_type').value,
      price_per_unit: parseFloat(document.getElementById('prod_price').value) || 0,
      warranty_years: parseInt(document.getElementById('prod_warranty').value) || 10,
    });

    try {
      const resp = await fetch(`/api/suppliers/${supplierId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ products }),
      });
      if (!resp.ok) throw new Error(tr('sd.js.add_product_failed', 'Failed to add product'));
      const updated = await resp.json();
      localStorage.setItem('supplierData', JSON.stringify(updated));
      renderProducts(updated.products);
      e.target.reset();
    } catch (err) {
      alert(tr('common.error_prefix', 'Error') + ': ' + err.message);
    }
  });

  document.getElementById('csvUploadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supplierId) return;
    const file = document.getElementById('csvFile')?.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const replace = document.getElementById('csvReplace')?.checked ? '1' : '0';
    const msg = document.getElementById('csvUploadMsg');
    try {
      const resp = await fetch(`/api/suppliers/${supplierId}/price-list/upload?replace=${replace}`, {
        method: 'POST',
        credentials: 'same-origin',
        body: fd,
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Upload failed');
      localStorage.setItem('supplierData', JSON.stringify(data.supplier));
      renderProducts(data.supplier.products);
      msg.textContent = tr('sd.js.csv_imported', 'Imported {n} products').replace('{n}', data.imported);
    } catch (err) {
      msg.textContent = err.message;
    }
  });

  document.getElementById('structuredQuoteForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supplierId) {
      alert(tr('sd.js.register_first', 'Please register first.'));
      return;
    }
    const form = e.target;
    const msg = document.getElementById('structuredQuoteMsg');
    const payload = {
      quote_request_id: form.quote_request_id.value.trim(),
      system_kwp: parseFloat(form.system_kwp.value),
      total_eur: parseInt(form.total_eur.value, 10),
      panel_model: form.panel_model.value.trim(),
      inverter_model: form.inverter_model.value.trim(),
      battery_model: form.battery_model.value.trim(),
      warranty_years: form.warranty_years.value ? parseInt(form.warranty_years.value, 10) : null,
      install_weeks: form.install_weeks.value ? parseInt(form.install_weeks.value, 10) : null,
      exclusions: form.exclusions.value.trim(),
      notes: form.notes.value.trim(),
    };
    try {
      const resp = await fetch(`/api/suppliers/${supplierId}/structured-quotes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Submit failed');
      msg.classList.remove('hidden');
      msg.textContent = tr('sd.js.quote_submitted', 'Structured quote saved ({id}).').replace('{id}', data.id);
      form.reset();
    } catch (err) {
      msg.classList.remove('hidden');
      msg.textContent = err.message;
    }
  });
}

function fillProfileForm(s) {
  const fields = { dash_company: 'company_name', dash_email: 'email', dash_phone: 'phone', dash_description: 'description',
    dash_survey_date: 'earliest_survey_date', dash_install_weeks: 'earliest_install_weeks' };
  for (const [id, key] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (el && s[key] != null) el.value = s[key];
  }
  const checks = {
    dash_residential: 'residential_available', dash_commercial: 'commercial_available',
    dash_battery: 'battery_capable', dash_ev: 'ev_charger_capable', dash_hp: 'heat_pump_capable',
  };
  for (const [id, key] of Object.entries(checks)) {
    const el = document.getElementById(id);
    if (el) el.checked = s[key] !== false && s[key] !== undefined ? !!s[key] : el.defaultChecked;
  }
}

function renderProducts(products) {
  const container = document.getElementById('productsList');
  if (!container) return;
  if (!products.length) {
    container.innerHTML = `<p class="empty-state">${tr('sd.js.no_products', 'No products yet. Add your first product below.')}</p>`;
    return;
  }
  container.innerHTML = products.map(p => `
    <div class="lead-card">
      <h4>${p.brand ? p.brand + ' ' : ''}${p.name || p.model}</h4>
      <p>${tr('sd.js.type', 'Type')}: ${p.type} · ${tr('sd.js.price', 'Price')}: ${formatCurrency(p.price_per_unit)} · ${tr('sd.js.warranty', 'Warranty')}: ${p.warranty_years} ${tr('sd.js.years', 'years')}${p.stock ? ` · ${p.stock}` : ''}</p>
      <button type="button" class="btn btn-outline btn-sm delete-product-btn" data-product-id="${encodeURIComponent(String(p.id || p.name || ''))}">${tr('sd.js.delete', 'Delete')}</button>
    </div>
  `).join('');
  container.querySelectorAll('.delete-product-btn').forEach(btn => {
    btn.addEventListener('click', () => deleteProduct(decodeURIComponent(btn.dataset.productId || '')));
  });
}

async function deleteProduct(productId) {
  const supplierId = localStorage.getItem('supplierId');
  if (!supplierId || !confirm(tr('sd.js.confirm_delete', 'Delete this product?'))) return;
  try {
    const resp = await fetch(`/api/suppliers/${supplierId}/products/${encodeURIComponent(productId)}`, {
      method: 'DELETE',
      credentials: 'same-origin',
    });
    if (!resp.ok) throw new Error('Delete failed');
    const updated = await resp.json();
    localStorage.setItem('supplierData', JSON.stringify(updated));
    renderProducts(updated.products || []);
  } catch (err) {
    alert(err.message);
  }
}

async function loadAnalytics(supplierId) {
  try {
    const data = await fetch(`/api/suppliers/${supplierId}/analytics`, { credentials: 'same-origin' }).then(r => r.json());
    const pv = document.getElementById('profileViews');
    const cr = document.getElementById('conversionRate');
    if (pv) pv.textContent = data.profile_views ?? '0';
    if (cr) cr.textContent = data.conversion_rate_pct != null ? `${data.conversion_rate_pct}%` : '—';
  } catch { /* ignore */ }
}

async function loadIntakeLink(supplierId) {
  const input = document.getElementById('intakeLinkUrl');
  const empty = document.getElementById('intakeEmpty');
  const box = document.getElementById('intakeLinkBox');
  const errEl = document.getElementById('intakeLinkError');
  if (!input) return;

  if (!supplierId) {
    empty?.classList.remove('hidden');
    box?.classList.add('hidden');
    return;
  }
  empty?.classList.add('hidden');
  box?.classList.remove('hidden');
  errEl?.classList.add('hidden');

  try {
    const resp = await fetch(`/api/suppliers/${supplierId}/intake-link`);
    const data = await resp.json();
    if (resp.ok && data.intake_url) {
      input.value = data.intake_url;
    } else {
      errEl?.classList.remove('hidden');
    }
  } catch {
    errEl?.classList.remove('hidden');
  }
}

async function loadLeads(supplierId) {
  const container = document.getElementById('leadsList');
  if (!container) return;

  try {
    const resp = await fetch(`/api/quotes?supplier_id=${encodeURIComponent(supplierId)}`, { credentials: 'same-origin' });
    const quotes = await resp.json();
    if (!resp.ok || !Array.isArray(quotes)) {
      throw new Error(quotes?.error || tr('sd.js.error_loading', 'Error loading leads.'));
    }

    document.getElementById('totalLeads').textContent = quotes.length;
    document.getElementById('pendingLeads').textContent = quotes.filter(q =>
      ['matched', 'received', 'pending'].includes(q.status)
    ).length;

    if (!quotes.length) {
      container.innerHTML = `<p class="empty-state">${tr('sd.no_leads', 'No leads yet. Complete your profile to start receiving quote requests.')}</p>`;
      return;
    }

    container.innerHTML = quotes.map(q => {
      const tier = q.lead_tier || 'basic';
      const tierClass = tier.replace('_', '-');
      const fit = q.matched_suppliers?.find(m => m.id === supplierId);
      const lp = q.lead_profile || {};
      const energy = lp.energy || {};
      const prefs = lp.preferences || {};
      const qual = q.qualification?.qualified ? tr('sd.js.qualified_lead', 'Qualified lead') : tier;
      return `
      <div class="lead-card ${q.qualification?.qualified ? 'lead-qualified' : ''}">
        <h4>${q.customer_first_name || q.customer_name}
          <span class="lead-tier-pill ${tierClass}">${qual}</span>
          ${fit ? `<span class="fit-badge">${fit.fit_score}/100 ${tr('sd.js.fit', 'fit')}</span>` : ''}
        </h4>
        <p>📧 ${q.customer_email} · 📞 ${q.customer_phone} · 📍 ${q.customer_postcode || ''} ${q.customer_town || ''}</p>
        ${q.preferred_contact_time ? `<p class="form-hint">${tr('sd.js.contact_time', 'Preferred')}: ${q.preferred_contact_time}</p>` : ''}
        <p class="lead-summary">${energy.annual_kwh ? `~${energy.annual_kwh.toLocaleString()} kWh/yr` : ''} · ${prefs.system_kwp || q.recommendation?.system_kwp || '—'} kWp · ${(energy.goals || []).slice(0, 2).join(', ')}</p>
        <p>${q.message || ''}</p>
        <div class="quote-status-track compact">${(q.status_timeline || []).map(s =>
          `<span class="quote-status-step ${s.done ? 'done' : ''} ${s.current ? 'current' : ''}">${s.label_key ? tr(s.label_key, s.label) : s.label}</span>`
        ).join('')}</div>
        <p class="form-hint">${tr('sd.js.received', 'Received')}: ${new Date(q.created_at).toLocaleDateString()}</p>
        ${q.recommendation ? `<p class="form-hint">${tr('sd.js.system', 'System')}: ${q.recommendation.system_kwp} kWp · ${(q.recommendation.readiness && q.recommendation.readiness.label) || ''}</p>` : ''}
        <button type="button" class="btn btn-outline btn-sm" onclick="markLeadViewed('${q.id}')">${tr('sd.js.mark_viewed', 'Mark as viewed')}</button>
      </div>`;
    }).join('');
  } catch {
    container.innerHTML = `<p class="empty-state">${tr('sd.js.error_loading', 'Error loading leads.')}</p>`;
  }
}

async function markLeadViewed(quoteId) {
  try {
    await fetch(`/api/quotes/${quoteId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ status: 'viewed' }),
    });
    const supplierId = localStorage.getItem('supplierId');
    if (supplierId) loadLeads(supplierId);
  } catch { /* ignore */ }
}

async function parseJsonResponse(resp) {
  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(resp.ok ? tr('calc.js.invalid_response', 'Invalid server response') : tr('calc.js.server_error', 'Server error ({status}). Please try again.').replace('{status}', resp.status));
  }
}
