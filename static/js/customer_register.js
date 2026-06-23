document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('customerRegisterForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('registerError');
    errEl.classList.add('hidden');

    const interests = [...form.querySelectorAll('input[name="interests"]:checked')].map(i => i.value);
    const password = form.password.value;
    const password2 = form.password2.value;

    if (password.length < 8) {
      errEl.textContent = tr('auth.password_short', 'Password must be at least 8 characters.');
      errEl.classList.remove('hidden');
      return;
    }
    if (password !== password2) {
      errEl.textContent = tr('auth.password_mismatch', 'Passwords do not match.');
      errEl.classList.remove('hidden');
      return;
    }

    const payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      postcode: form.postcode.value.trim(),
      housing_type: form.housing_type.value,
      interests,
      password,
    };

    if (!payload.name || !payload.email || !payload.phone || !payload.postcode) {
      errEl.textContent = tr('cr.js.required', 'Please fill in all required fields.');
      errEl.classList.remove('hidden');
      return;
    }

    try {
      const resp = await fetch('/api/customers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || tr('cr.js.registration_failed', 'Registration failed'));

      localStorage.setItem('customerId', data.id);
      localStorage.setItem('customerData', JSON.stringify(data));
      form.classList.add('hidden');
      document.querySelector('.register-note')?.classList.add('hidden');
      document.querySelector('.register-switch')?.classList.add('hidden');
      document.getElementById('registerSuccess').classList.remove('hidden');
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove('hidden');
    }
  });
});
