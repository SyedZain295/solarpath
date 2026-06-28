// Roof photo upload — shared between calculator and results quote flow

const ROOF_PHOTO_SET_KEY = 'roofPhotoSetId';

function getRoofPhotoSetId() {
  try {
    return sessionStorage.getItem(ROOF_PHOTO_SET_KEY) || localStorage.getItem(ROOF_PHOTO_SET_KEY) || '';
  } catch {
    return '';
  }
}

function setRoofPhotoSetId(setId) {
  if (!setId) return;
  try {
    sessionStorage.setItem(ROOF_PHOTO_SET_KEY, setId);
    localStorage.setItem(ROOF_PHOTO_SET_KEY, setId);
  } catch { /* ignore */ }
}

function roofPhotoImageUrl(photoId, setId, quoteId) {
  const q = new URLSearchParams();
  if (setId) q.set('set_id', setId);
  if (quoteId) q.set('quote_id', quoteId);
  const qs = q.toString();
  return `/api/roof-photos/${encodeURIComponent(photoId)}/image${qs ? `?${qs}` : ''}`;
}

async function uploadRoofPhotos(fileList, { setId = '', postcode = '', customerEmail = '' } = {}) {
  const files = [...(fileList || [])].filter((f) => f && f.size);
  if (!files.length) return null;

  const fd = new FormData();
  files.forEach((f) => fd.append('photos', f));
  if (setId || getRoofPhotoSetId()) fd.append('set_id', setId || getRoofPhotoSetId());
  if (postcode) fd.append('postcode', postcode);
  if (customerEmail) fd.append('customer_email', customerEmail);

  const resp = await fetch('/api/roof-photos/upload', {
    method: 'POST',
    body: fd,
    credentials: 'same-origin',
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || tr('roof.upload_fail', 'Upload failed'));
  if (data.set_id) setRoofPhotoSetId(data.set_id);
  return data;
}

function renderRoofPhotoPreview(container, summary, { quoteId = '' } = {}) {
  if (!container) return;
  const photos = summary?.photos || [];
  if (!photos.length) {
    container.innerHTML = '';
    container.classList.add('hidden');
    return;
  }
  const setId = summary.set_id || getRoofPhotoSetId();
  container.classList.remove('hidden');
  container.innerHTML = `
    <p class="form-hint">${tr('roof.uploaded_count', '{n} photo(s) ready for installers').replace('{n}', photos.length)}</p>
    <div class="roof-photo-preview-grid">
      ${photos.map((p) => `
        <a href="${roofPhotoImageUrl(p.id, setId, quoteId)}" target="_blank" rel="noopener" class="roof-photo-thumb">
          <img src="${roofPhotoImageUrl(p.id, setId, quoteId)}" alt="${p.original_name || 'Roof photo'}" loading="lazy">
        </a>`).join('')}
    </div>`;
}

function wireRoofPhotoInput(inputEl, previewEl, statusEl, { getPostcode, onUploaded } = {}) {
  if (!inputEl) return;
  inputEl.addEventListener('change', async (e) => {
    const files = e.target.files;
    if (!files?.length) return;
    if (statusEl) statusEl.textContent = tr('roof.uploading', 'Uploading…');
    try {
      const postcode = typeof getPostcode === 'function' ? getPostcode() : '';
      const summary = await uploadRoofPhotos(files, { postcode });
      if (previewEl) renderRoofPhotoPreview(previewEl, summary);
      const hasCb = document.getElementById('has_roof_photos');
      if (hasCb) hasCb.checked = true;
      if (typeof onUploaded === 'function') onUploaded(summary);
      if (statusEl) {
        statusEl.textContent = tr('roof.upload_ok', 'Photos saved — installers will see them with your quote request.');
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = err.message || tr('roof.upload_fail', 'Upload failed');
    }
    e.target.value = '';
  });
}
