document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('loginForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('loginError');
    errEl.classList.add('hidden');

    try {
      const resp = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          email: form.email.value.trim(),
          password: form.password.value,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || tr('auth.login_failed', 'Login failed'));
      if (data.customer) {
        localStorage.setItem('customerId', data.customer.id);
        localStorage.setItem('customerData', JSON.stringify(data.customer));
      }
      window.location.href = '/account';
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove('hidden');
    }
  });
});
