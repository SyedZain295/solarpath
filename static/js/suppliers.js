// Bavaria installer search — city, postcode, pagination



const PAGE_SIZE = 50;

const REGION = 'Bayern';

let currentOffset = 0;

let currentTotal = 0;

let regionTotal = 4145;



document.addEventListener('DOMContentLoaded', () => {

  loadStats();

  bindControls();

  runSearch(0);

});



function bindControls() {

  document.getElementById('filterBtn')?.addEventListener('click', () => runSearch(0));



  document.getElementById('prevPage')?.addEventListener('click', () => {

    if (currentOffset >= PAGE_SIZE) runSearch(currentOffset - PAGE_SIZE);

  });

  document.getElementById('nextPage')?.addEventListener('click', () => {

    if (currentOffset + PAGE_SIZE < currentTotal) runSearch(currentOffset + PAGE_SIZE);

  });



  document.querySelectorAll('.city-chip').forEach(chip => {

    chip.addEventListener('click', () => {

      document.querySelectorAll('.city-chip').forEach(c => c.classList.remove('active'));

      chip.classList.add('active');

      document.getElementById('filterCity').value = chip.dataset.city || '';

      document.getElementById('filterPostcode').value = '';

      runSearch(0);

    });

  });

}



async function loadStats() {

  const banner = document.getElementById('coverageText');

  try {

    const resp = await fetch('/api/suppliers/stats');

    const stats = await resp.json();

    regionTotal = stats.total || regionTotal;

    const top = (stats.top_cities || []).slice(0, 3).map(c => c.city).join(', ');

    banner.textContent = `${formatNum(regionTotal)} installers in Bavaria${top ? ` · ${top}` : ''}`;

  } catch {

    banner.textContent = `${formatNum(regionTotal)}+ installers in Bavaria`;

  }

}



function buildParams(offset) {

  const params = new URLSearchParams();

  params.set('limit', String(PAGE_SIZE));

  params.set('offset', String(offset));

  params.set('state', REGION);



  const city = document.getElementById('filterCity')?.value.trim() || '';

  const postcode = document.getElementById('filterPostcode')?.value.trim() || '';

  const radius = document.getElementById('filterRadius')?.value || '50';



  if (postcode) {

    params.set('postcode', postcode);

    params.set('radius_km', radius);

  } else if (city) {

    params.set('city', city);

    params.set('radius_km', radius);

  }



  return params;

}



async function runSearch(offset) {

  currentOffset = offset;

  const container = document.getElementById('suppliersList');

  const copy = container.dataset;

  container.innerHTML = `<div class="loading-state"><div class="loading-spinner"></div><p>${copy.loading}</p></div>`;



  try {

    const resp = await fetch('/api/suppliers?' + buildParams(offset).toString());

    const body = await resp.json();

    if (!resp.ok) throw new Error(body.error || copy.error);



    const suppliers = body.items || body;

    currentTotal = body.total ?? suppliers.length;

    if (body.region_total) regionTotal = body.region_total;



    updateSummary(body, suppliers.length);

    updatePagination();



    if (!suppliers.length) {

      container.innerHTML = `<p class="empty-state">${copy.empty} <a href="/suppliers/register">${copy.register} →</a></p>`;

      return;

    }



    container.innerHTML = suppliers.map(s => renderCard(s, copy)).join('');

  } catch (err) {

    container.innerHTML = `<p class="empty-state">${err.message || copy.error}</p>`;

    document.getElementById('resultSummary').hidden = true;

    document.getElementById('suppliersPagination').hidden = true;

  }

}



function renderRating(s, copy) {

  if (s.display_rating != null && s.display_reviews > 0) {

    const label = (copy.reviews || '{n} reviews').replace('{n}', s.display_reviews);

    return `<div class="supplier-rating">★ ${s.display_rating} <span class="supplier-rating-count">(${label})</span></div>`;

  }

  return `<div class="supplier-rating supplier-rating--none">${copy.noReviews || 'No reviews yet'}</div>`;

}



function renderContact(s, copy) {

  const parts = [];

  if (s.display_phone) parts.push(`📞 ${esc(s.display_phone)}`);

  if (s.display_email) parts.push(`✉️ ${esc(s.display_email)}`);

  if (s.display_website) {

    const url = s.display_website.startsWith('http') ? s.display_website : `https://${s.display_website}`;

    parts.push(`🌐 <a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${copy.website || 'Website'}</a>`);

  }

  if (parts.length) return parts.join(' · ');

  if (s.is_directory_listing) return `<span class="form-hint">${copy.contactDirectory || 'Contact not listed — request a quote to connect.'}</span>`;

  return `<span class="form-hint">${copy.contactUnavailable || 'Contact on request'}</span>`;

}



function renderCard(s, copy) {

  const qualityLine = s.quality_score != null

    ? `${copy.quality}: <strong>${s.quality_score}/100</strong>`

    : (s.is_demo_listing ? `<span class="form-hint demo-listing-badge">${esc(s.listing_label || 'Demo listing (beta sample)')}</span>`
      : (s.is_directory_listing ? `<span class="form-hint">${copy.directoryListing || 'Public directory listing'}</span>` : ''));



  return `

    <div class="supplier-card ${s.verified ? 'verified' : ''} ${s.is_directory_listing ? 'directory-listing' : ''} ${s.is_demo_listing ? 'demo-listing' : ''}">

      <div class="supplier-header">

        <div>

          <div class="supplier-name">${esc(s.company_name)}</div>

          ${renderRating(s, copy)}

        </div>

        ${s.verified ? `<span class="verified-badge">${copy.verified || '✓ Verified'}</span>` : ''}

      </div>

      <p class="supplier-meta">${esc(s.description || '')}</p>

      <div class="supplier-meta">

        📍 ${esc((s.regions || []).join(', '))}<br>

        ${s.distance_km != null ? `📏 ${copy.nearest}: <strong>${s.distance_km} km</strong> (${esc(s.nearest_postcode || '—')})<br>` : ''}

        ${renderContact(s, copy)}<br>

        ${qualityLine}

      </div>

      <div class="supplier-tags">

        ${(s.certifications || []).map(c => `<span class="tag">${esc(c)}</span>`).join('')}

        ${s.verified ? `<span class="tag tag-verified">${esc(s.plan)} plan</span>` : ''}

      </div>

      ${s.installation_availability ? `<p class="form-hint">⏱ ${copy.installation}: ${esc(s.installation_availability)}</p>` : ''}

      <div style="margin-top:1rem">

        <a href="/calculator" class="btn btn-primary btn-sm">${copy.estimate}</a>

      </div>

    </div>`;

}



function updateSummary(body, shown) {

  const el = document.getElementById('resultSummary');

  const container = document.getElementById('suppliersList');

  const from = currentOffset + 1;

  const to = currentOffset + shown;

  let scope = body.city || (body.postcode ? `PLZ ${body.postcode}` : container.dataset.region || 'Bayern');

  const center = body.search_center ? ` · ${body.search_center}` : '';

  el.textContent = `${container.dataset.showing || 'Showing'} ${from}–${to} ${container.dataset.of || 'of'} ${formatNum(currentTotal)} near ${scope}${center} (${formatNum(regionTotal)} in Bavaria)`;

  el.hidden = false;

}



function updatePagination() {

  const pag = document.getElementById('suppliersPagination');

  const prev = document.getElementById('prevPage');

  const next = document.getElementById('nextPage');

  const info = document.getElementById('pageInfo');

  const pages = Math.max(1, Math.ceil(currentTotal / PAGE_SIZE));

  const page = Math.floor(currentOffset / PAGE_SIZE) + 1;



  pag.hidden = currentTotal <= PAGE_SIZE;

  prev.disabled = currentOffset <= 0;

  next.disabled = currentOffset + PAGE_SIZE >= currentTotal;

  info.textContent = `Page ${page} / ${pages}`;

}



function formatNum(n) {

  return Number(n).toLocaleString();

}



function esc(text) {

  return String(text ?? '')

    .replace(/&/g, '&amp;')

    .replace(/</g, '&lt;')

    .replace(/>/g, '&gt;')

    .replace(/"/g, '&quot;');

}


