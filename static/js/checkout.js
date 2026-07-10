document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('checkoutForm');
  if (!form) return;

  setupCardFormatting();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('checkoutError');
    errEl.classList.add('hidden');

    const useStripe = form.dataset.stripe === '1';

    if (!useStripe) {
      const expError = validateExpiry(form.card_exp.value);
      if (expError) {
        errEl.textContent = expError;
        errEl.classList.remove('hidden');
        form.card_exp.focus();
        return;
      }

      const cardDigits = form.card_number.value.replace(/\D/g, '');
      if (cardDigits.length < 16) {
        errEl.textContent = tr('sc.js.invalid_card', 'Please enter a valid 16-digit card number.');
        errEl.classList.remove('hidden');
        form.card_number.focus();
        return;
      }
    }

    const payload = {
      plan: form.plan.value,
      email: form.checkout_email.value.trim(),
    };

    const submitBtn = form.querySelector('[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
      const resp = await fetch('/api/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const text = await resp.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        const msg = tr('sc.js.server_error', 'Server error ({status}). Please try again.');
        throw new Error(msg.replace('{status}', resp.status));
      }
      if (!resp.ok) throw new Error(data.error || tr('sc.js.checkout_failed', 'Checkout failed'));

      sessionStorage.setItem('supplierCheckout', JSON.stringify({
        checkout_id: data.checkout_id,
        plan: data.plan,
        email: payload.email,
      }));
      if (data.stripe && data.redirect.startsWith('http')) {
        window.location.href = data.redirect;
      } else {
        window.location.href = data.redirect;
      }
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove('hidden');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
});

function setupCardFormatting() {
  const nameInput = document.getElementById('card_name');
  const numberInput = document.getElementById('card_number');
  const expInput = document.getElementById('card_exp');
  const cvcInput = document.getElementById('card_cvc');

  if (!numberInput || !expInput) return;

  nameInput?.addEventListener('input', updateCardPreview);
  numberInput.addEventListener('input', () => {
    const formatted = formatCardNumber(numberInput.value);
    numberInput.value = formatted;
    updateCardBrand(formatted);
    updateCardPreview();
  });
  expInput.addEventListener('input', () => {
    expInput.value = formatExpiry(expInput.value);
    updateCardPreview();
  });
  expInput.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && expInput.value.endsWith('/')) {
      e.preventDefault();
      expInput.value = expInput.value.slice(0, -1);
      updateCardPreview();
    }
  });
  cvcInput?.addEventListener('input', () => {
    cvcInput.value = cvcInput.value.replace(/\D/g, '').slice(0, 4);
  });

  updateCardPreview();
}

function formatCardNumber(value) {
  const digits = value.replace(/\D/g, '').slice(0, 16);
  return digits.replace(/(\d{4})(?=\d)/g, '$1 ').trim();
}

function formatExpiry(value) {
  let digits = value.replace(/\D/g, '').slice(0, 4);

  if (digits.length === 0) return '';

  if (digits.length === 1) {
    if (parseInt(digits, 10) > 1) return `0${digits}/`;
    return digits;
  }

  let mm = digits.slice(0, 2);
  const mmNum = parseInt(mm, 10);
  if (mmNum === 0) mm = '01';
  else if (mmNum > 12) mm = '12';

  const yy = digits.slice(2, 4);
  return yy.length ? `${mm}/${yy}` : `${mm}/`;
}

function validateExpiry(value) {
  if (!/^\d{2}\/\d{2}$/.test(value)) {
    return tr('sc.js.expiry_format', 'Enter expiry as MM/YY (e.g. 10/32).');
  }
  const [mm, yy] = value.split('/').map((n) => parseInt(n, 10));
  if (mm < 1 || mm > 12) return tr('sc.js.expiry_month', 'Expiry month must be between 01 and 12.');
  const now = new Date();
  const expEnd = new Date(2000 + yy, mm, 0, 23, 59, 59);
  if (expEnd < now) return tr('sc.js.expired', 'This card appears to be expired.');
  return null;
}

function updateCardBrand(numberValue) {
  const brandEl = document.querySelector('.payment-card-type');
  if (!brandEl) return;
  const d = numberValue.replace(/\D/g, '');
  if (d.startsWith('4')) brandEl.textContent = 'VISA';
  else if (/^5[1-5]/.test(d) || /^2[2-7]/.test(d)) brandEl.textContent = 'MC';
  else if (d.startsWith('3')) brandEl.textContent = 'AMEX';
  else brandEl.textContent = 'CARD';
}

function updateCardPreview() {
  const name = document.getElementById('card_name')?.value.trim() || 'YOUR NAME';
  const raw = document.getElementById('card_number')?.value.replace(/\D/g, '') || '';
  const exp = document.getElementById('card_exp')?.value || 'MM/YY';

  const nameEl = document.getElementById('cardPreviewName');
  const numEl = document.getElementById('cardPreviewNumber');
  const expEl = document.getElementById('cardPreviewExp');

  if (nameEl) nameEl.textContent = name.toUpperCase().slice(0, 26) || 'YOUR NAME';

  if (numEl) {
    if (!raw.length) {
      numEl.textContent = '•••• •••• •••• ••••';
    } else {
      const padded = (raw + '••••••••••••••••').slice(0, 16);
      const groups = padded.match(/.{1,4}/g) || [];
      numEl.textContent = groups.join(' ');
    }
  }

  if (expEl) expEl.textContent = exp.length >= 5 ? exp : (exp || 'MM/YY');
}
