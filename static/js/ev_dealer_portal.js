// Solar Path EV — dealer portal (Phase 2)

function initEvDealerRegister() {
  const form = document.getElementById('evDealerRegisterForm');
  const ok = document.getElementById('evDealerRegisterOk');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const resp = await fetch('/api/ev-dealer/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: document.getElementById('dr_company').value,
        email: document.getElementById('dr_email').value,
        phone: document.getElementById('dr_phone').value,
        location: document.getElementById('dr_location').value,
        password: document.getElementById('dr_password').value,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      alert(data.error || 'Registration failed');
      return;
    }
    form.classList.add('hidden');
    ok.classList.remove('hidden');
    ok.innerHTML = `<p>${tr('evm.dealer_register_ok', 'Account created.')}</p><p>${tr('evm.dealer_status_label', 'Status')}: <strong>${data.dealer.status}</strong></p><p><a href="/ev/dealer/login" class="btn btn-primary btn-sm">${tr('evm.dealer_login_btn', 'Sign in')}</a></p>`;
  });
}

function initEvDealerLogin() {
  const form = document.getElementById('evDealerLoginForm');
  const err = document.getElementById('evDealerLoginError');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    err?.classList.add('hidden');
    const resp = await fetch('/api/ev-dealer/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('dl_email').value,
        password: document.getElementById('dl_password').value,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      if (err) {
        err.textContent = data.error || 'Login failed';
        err.classList.remove('hidden');
      }
      return;
    }
    const next = new URLSearchParams(window.location.search).get('next') || '/ev/dealer/dashboard';
    window.location.href = next;
  });
}

function initEvDealerDashboard() {
  document.getElementById('evDealerLogout')?.addEventListener('click', async () => {
    await fetch('/api/ev-dealer/logout', { method: 'POST' });
    window.location.href = '/ev/dealer/login';
  });

  document.querySelectorAll('.evm-dash-tabs .tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.evm-dash-tabs .tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`)?.classList.add('active');
    });
  });

  loadDealerInventory();
  loadDealerLeads();
  loadDealerBilling();
  handleFeaturedReturn();
  document.getElementById('dealerVehicleForm')?.addEventListener('submit', saveDealerVehicle);
}

function handleFeaturedReturn() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('featured') === 'success') {
    alert(tr('evm.featured_success', 'Featured listing activated — thank you!'));
    window.history.replaceState({}, '', '/ev/dealer/dashboard');
    loadDealerInventory();
    loadDealerBilling();
  }
}

async function loadDealerBilling() {
  const el = document.getElementById('dealerBillingPanel');
  if (!el) return;
  const resp = await fetch('/api/ev-dealer/billing');
  if (!resp.ok) return;
  const data = await resp.json();
  const events = data.events || [];
  const history = events.length
    ? events.slice().reverse().map((e) => `<li>${e.created_at?.slice(0, 10) || ''} · ${e.type} · €${e.amount_eur || 0} · ${e.status}</li>`).join('')
    : `<li>${tr('evm.no_billing', 'No billing events yet.')}</li>`;
  el.innerHTML = `
    <p><strong>${tr('evm.featured_price', 'Featured listing')}</strong>: €${data.featured_price_eur || 49} / ${data.featured_duration_days || 30} ${tr('evm.days', 'days')}</p>
    <p>${tr('evm.total_spent', 'Total spent')}: €${data.total_spent_eur || 0}</p>
    <ul class="evm-billing-history">${history}</ul>`;
}

async function promoteFeatured(vehicleId) {
  const useStripe = document.getElementById('dealerBillingPanel')?.dataset.stripe === '1';
  if (useStripe) {
    const resp = await fetch('/api/ev-dealer/billing/featured-checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_id: vehicleId }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      alert(data.error || 'Checkout failed');
      return;
    }
    if (data.checkout_url) window.location.href = data.checkout_url;
    return;
  }
  const resp = await fetch('/api/ev-dealer/billing/featured-demo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vehicle_id: vehicleId }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    alert(data.error || 'Failed');
    return;
  }
  loadDealerInventory();
  loadDealerBilling();
  alert(tr('evm.featured_demo_ok', 'Featured listing activated (demo invoice).'));
}

async function loadDealerInventory() {
  const el = document.getElementById('dealerInventoryList');
  if (!el) return;
  const resp = await fetch('/api/ev-dealer/me');
  if (resp.status === 401) {
    window.location.href = '/ev/dealer/login';
    return;
  }
  const data = await resp.json();
  const items = data.vehicles || [];
  if (!items.length) {
    el.innerHTML = `<p class="form-hint">${tr('evm.no_inventory', 'No vehicles yet — add your first listing.')}</p>`;
    return;
  }
  el.innerHTML = items.map((v) => `
    <div class="evm-inventory-row">
      <div>
        <strong>${v.make} ${v.model}</strong> · ${formatEur(v.price_eur)}
        ${v.featured ? `<span class="evm-featured-badge">${tr('evm.featured', 'Featured')}</span>` : ''}
        <span class="evm-inv-status">${v.vehicle_status || v.status}</span>
      </div>
      <div class="evm-inventory-actions">
        ${!v.featured && (v.vehicle_status === 'published' || v.status === 'published') ? `<button type="button" class="btn btn-primary btn-sm" data-feature="${v.id}">${tr('evm.promote_featured', 'Feature listing')}</button>` : ''}
        <button type="button" class="btn btn-outline btn-sm" data-edit="${v.id}">${tr('common.edit', 'Edit')}</button>
        <button type="button" class="btn btn-outline btn-sm" data-del="${v.id}">${tr('common.delete', 'Delete')}</button>
      </div>
    </div>`).join('');

  el.querySelectorAll('[data-feature]').forEach((btn) => {
    btn.addEventListener('click', () => promoteFeatured(btn.dataset.feature));
  });

  el.querySelectorAll('[data-edit]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const v = items.find((x) => x.id === btn.dataset.edit);
      if (v) populateVehicleForm(v);
      document.querySelector('.evm-dash-tabs [data-tab="add"]')?.click();
    });
  });
  el.querySelectorAll('[data-del]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm(tr('evm.confirm_delete', 'Delete this listing?'))) return;
      await fetch(`/api/ev-dealer/vehicles/${btn.dataset.del}`, { method: 'DELETE' });
      loadDealerInventory();
    });
  });
}

function populateVehicleForm(v) {
  document.getElementById('veh_edit_id').value = v.id || '';
  document.getElementById('veh_make').value = v.make || '';
  document.getElementById('veh_model').value = v.model || '';
  document.getElementById('veh_trim').value = v.trim || '';
  document.getElementById('veh_year').value = v.year || '';
  document.getElementById('veh_price').value = v.price_eur || '';
  document.getElementById('veh_mileage').value = v.mileage_km || '';
  document.getElementById('veh_battery').value = v.battery_kwh || '';
  document.getElementById('veh_consumption').value = v.consumption_kwh_100km || 17;
  document.getElementById('veh_winter_min').value = v.winter_range_km_min || '';
  document.getElementById('veh_winter_max').value = v.winter_range_km_max || '';
  document.getElementById('veh_dc').value = v.dc_fast_charge_kw || '';
  document.getElementById('veh_ac').value = v.ac_charge_kw || 11;
  document.getElementById('veh_location').value = v.location || '';
  const cert = v.battery_certificate || {};
  document.getElementById('veh_cert_uploaded').checked = !!cert.uploaded;
  document.getElementById('veh_cert_provider').value = cert.provider || '';
  document.getElementById('veh_cert_date').value = cert.test_date || '';
  document.getElementById('veh_cert_soh').value = cert.state_of_health_pct ?? '';
  document.getElementById('veh_cert_url').value = cert.document_url || '';
  document.getElementById('veh_warr_years').value = v.battery_warranty_years_remaining || '';
  document.getElementById('veh_warr_km').value = v.battery_warranty_km_remaining || '';
  document.getElementById('veh_photos').value = (v.photo_urls || []).join('\n');
  const featEl = document.getElementById('veh_featured');
  if (featEl) featEl.checked = !!v.featured;
  document.getElementById('veh_status').value = v.vehicle_status || v.status || 'draft';
}

function vehicleFormPayload() {
  return {
    make: document.getElementById('veh_make').value,
    model: document.getElementById('veh_model').value,
    trim: document.getElementById('veh_trim').value,
    year: document.getElementById('veh_year').value,
    price_eur: document.getElementById('veh_price').value,
    mileage_km: document.getElementById('veh_mileage').value,
    battery_kwh: document.getElementById('veh_battery').value,
    consumption_kwh_100km: document.getElementById('veh_consumption').value,
    winter_range_km_min: document.getElementById('veh_winter_min').value,
    winter_range_km_max: document.getElementById('veh_winter_max').value,
    dc_fast_charge_kw: document.getElementById('veh_dc').value,
    ac_charge_kw: document.getElementById('veh_ac').value,
    location: document.getElementById('veh_location').value,
    certificate_uploaded: document.getElementById('veh_cert_uploaded').checked,
    cert_provider: document.getElementById('veh_cert_provider').value,
    cert_test_date: document.getElementById('veh_cert_date').value,
    cert_soh: document.getElementById('veh_cert_soh').value,
    cert_document_url: document.getElementById('veh_cert_url').value,
    battery_warranty_years_remaining: document.getElementById('veh_warr_years').value,
    battery_warranty_km_remaining: document.getElementById('veh_warr_km').value,
    photo_urls: document.getElementById('veh_photos').value,
    featured: document.getElementById('veh_featured')?.checked || false,
    status: document.getElementById('veh_status').value,
  };
}

async function saveDealerVehicle(e) {
  e.preventDefault();
  const editId = document.getElementById('veh_edit_id').value;
  const payload = vehicleFormPayload();

  const photoFiles = document.getElementById('veh_photo_files')?.files;
  if (photoFiles?.length) {
    const fd = new FormData();
    [...photoFiles].forEach((f) => fd.append('photos', f));
    const up = await fetch('/api/ev-dealer/upload-photos', { method: 'POST', body: fd });
    const upData = await up.json();
    if (up.ok && upData.urls?.length) {
      const existing = payload.photo_urls ? payload.photo_urls.split('\n').map((s) => s.trim()).filter(Boolean) : [];
      payload.photo_urls = [...existing, ...upData.urls].join('\n');
    }
  }

  const certFile = document.getElementById('veh_cert_file')?.files?.[0];
  if (certFile) {
    const fd = new FormData();
    fd.append('cert', certFile);
    const up = await fetch('/api/ev-dealer/upload-cert', { method: 'POST', body: fd });
    const upData = await up.json();
    if (up.ok && upData.url) {
      payload.cert_document_url = upData.url;
      payload.certificate_uploaded = true;
    }
  }

  const url = editId ? `/api/ev-dealer/vehicles/${editId}` : '/api/ev-dealer/vehicles';
  const method = editId ? 'PUT' : 'POST';
  const resp = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (!resp.ok) {
    alert(data.error || 'Save failed');
    return;
  }
  document.getElementById('veh_edit_id').value = '';
  e.target.reset();
  document.getElementById('veh_ac').value = 11;
  document.getElementById('veh_consumption').value = 17;
  loadDealerInventory();
  document.querySelector('.evm-dash-tabs [data-tab="inventory"]')?.click();
  alert(tr('evm.vehicle_saved', 'Vehicle saved.'));
}

async function loadDealerLeads() {
  const el = document.getElementById('dealerLeadsList');
  if (!el) return;
  const resp = await fetch('/api/ev-dealer/leads');
  if (!resp.ok) return;
  const data = await resp.json();
  const leads = data.leads || [];
  if (!leads.length) {
    el.innerHTML = `<p class="form-hint">${tr('evm.no_leads', 'No buyer leads yet.')}</p>`;
    return;
  }
  el.innerHTML = leads.map((l) => `
    <div class="evm-lead-card ${l.qualified ? 'evm-lead-card--qualified' : ''}">
      <div class="evm-lead-top">
        <strong>${l.buyer_name}</strong>
        <span class="evm-lead-badge">${l.qualified ? tr('evm.qualified_lead', 'Qualified') : tr('evm.unqualified_lead', 'Incomplete')}</span>
        <span class="evm-lead-status">${l.status}</span>
      </div>
      <p>${l.vehicle_label || ''} · ${l.buyer_email} · ${l.buyer_phone || '—'} · ${l.buyer_postcode || '—'}</p>
      ${l.message ? `<p class="form-hint">${l.message}</p>` : ''}
      <div class="evm-lead-actions">
        <button type="button" class="btn btn-outline btn-sm" data-status="contacted" data-id="${l.id}">${tr('evm.mark_contacted', 'Mark contacted')}</button>
        <button type="button" class="btn btn-outline btn-sm" data-status="closed" data-id="${l.id}">${tr('evm.mark_closed', 'Close')}</button>
      </div>
    </div>`).join('');

  el.querySelectorAll('[data-status]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await fetch(`/api/ev-dealer/leads/${btn.dataset.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: btn.dataset.status }),
      });
      loadDealerLeads();
    });
  });
}

function formatEur(n) {
  if (typeof formatCurrency === 'function') return formatCurrency(n);
  return `€${Number(n || 0).toLocaleString()}`;
}
