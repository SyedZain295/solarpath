// Electricity bill upload — OCR prefill for calculator usage step

function billUploadHeaders() {
  const headers = {};
  const beta = sessionStorage.getItem('betaInviteToken') || window.BETA_INVITE_DEFAULT || '';
  if (beta) headers['X-Beta-Invite'] = beta;
  return headers;
}

async function uploadElectricityBill(file) {
  if (!file || !file.size) return null;
  const fd = new FormData();
  fd.append('file', file);
  const resp = await fetch('/api/bill-upload', {
    method: 'POST',
    body: fd,
    headers: billUploadHeaders(),
    credentials: 'same-origin',
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || tr('calc.bill_upload.fail', 'Could not read bill'));
  return data;
}

function applyBillParseResult(data, { billEl, kwhEl, priceEl } = {}) {
  const parsed = data?.parsed || {};
  let filled = 0;
  if (parsed.monthly_kwh != null && kwhEl) {
    kwhEl.value = Math.round(Number(parsed.monthly_kwh));
    filled += 1;
  }
  if (parsed.monthly_bill_eur != null && billEl) {
    billEl.value = Math.round(Number(parsed.monthly_bill_eur));
    filled += 1;
  }
  if (parsed.monthly_kwh > 0 && parsed.monthly_bill_eur > 0 && priceEl) {
    const ct = (Number(parsed.monthly_bill_eur) / Number(parsed.monthly_kwh)) * 100;
    if (ct >= 8 && ct <= 65) {
      priceEl.value = ct.toFixed(1);
    }
  }
  return { filled, confidence: parsed.confidence, parsed };
}

function formatBillUploadStatus(data, filled) {
  const parsed = data?.parsed || {};
  const conf = parsed.confidence != null ? Math.round(parsed.confidence * 100) : null;
  if (filled >= 2) {
    return tr(
      'calc.bill_upload.ok_both',
      'Filled bill and kWh from your upload ({conf}% confidence). Check values before continuing.'
    ).replace('{conf}', String(conf ?? '—'));
  }
  if (filled === 1) {
    return tr(
      'calc.bill_upload.ok_partial',
      'Partially filled from bill ({conf}% confidence) — add the missing value if needed.'
    ).replace('{conf}', String(conf ?? '—'));
  }
  return tr(
    'calc.bill_upload.ok_none',
    'Upload received but we could not extract numbers — enter bill or kWh manually.'
  );
}

function wireBillUploadInput(inputEl, { billEl, kwhEl, priceEl, statusEl, onParsed, cardEl } = {}) {
  if (!inputEl) return;
  const card = cardEl || document.getElementById('billUploadCard');
  inputEl.addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const name = (file.name || '').toLowerCase();
    if (!name.endsWith('.pdf') && !file.type.includes('pdf') && !file.type.includes('text')) {
      if (statusEl) {
        statusEl.textContent = tr('calc.bill_upload.pdf_only', 'Please upload a PDF bill (or enter values manually).');
        statusEl.classList.add('bill-upload-status--warn');
      }
      e.target.value = '';
      return;
    }
    card?.classList.add('bill-upload-card--loading');
    card?.classList.remove('bill-upload-card--ok');
    if (statusEl) {
      statusEl.textContent = tr('calc.bill_upload.reading', 'Reading bill…');
      statusEl.classList.remove('bill-upload-status--ok', 'bill-upload-status--warn');
    }
    try {
      const data = await uploadElectricityBill(file);
      const { filled, parsed } = applyBillParseResult(data, { billEl, kwhEl, priceEl });
      if (statusEl) {
        statusEl.textContent = formatBillUploadStatus(data, filled);
        statusEl.classList.toggle('bill-upload-status--ok', filled > 0);
        statusEl.classList.toggle('bill-upload-status--warn', filled === 0);
      }
      card?.classList.toggle('bill-upload-card--ok', filled > 0);
      if (typeof onParsed === 'function') onParsed({ data, filled, parsed });
    } catch (err) {
      if (statusEl) {
        statusEl.textContent = err.message || tr('calc.bill_upload.fail', 'Could not read bill');
        statusEl.classList.add('bill-upload-status--warn');
      }
    } finally {
      card?.classList.remove('bill-upload-card--loading');
      e.target.value = '';
    }
  });
}
