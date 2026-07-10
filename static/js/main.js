// SolarPath – sitewide micro-interactions

document.addEventListener('DOMContentLoaded', () => {
  document.documentElement.classList.add('js');
  initMobileNav();
  initAppReveals();
});

function initMobileNav() {
  const menuBtn = document.querySelector('.mobile-menu-btn');
  const navPanel = document.getElementById('navMenu') || document.querySelector('.nav-panel');
  const navInner = document.querySelector('.nav-inner');

  function closeNav() {
    if (!navPanel?.classList.contains('nav-open')) return;
    navPanel.classList.remove('nav-open');
    navInner?.classList.remove('nav-open');
    menuBtn?.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-menu-open');
  }

  if (menuBtn && navPanel) {
    menuBtn.addEventListener('click', () => {
      const open = navPanel.classList.toggle('nav-open');
      navInner?.classList.toggle('nav-open', open);
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('nav-menu-open', open);
    });

    navPanel.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => closeNav()));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeNav(); });
  }
}

function initAppReveals() {
  if (document.body.classList.contains('home-page')) return;
  const panels = document.querySelectorAll('.glass-panel');
  panels.forEach((panel, i) => {
    panel.classList.add('panel-enter');
    panel.style.animationDelay = `${Math.min(i * 0.07, 0.35)}s`;
  });
}

function tr(key, fallback = '') {
  return (window.APP_TRANSLATIONS && window.APP_TRANSLATIONS[key]) || fallback || key;
}

function clearCustomerCache() {
  localStorage.removeItem('customerId');
  localStorage.removeItem('customerData');
}

async function fetchCurrentCustomer() {
  try {
    const resp = await fetch('/api/me', { credentials: 'same-origin' });
    if (!resp.ok) {
      clearCustomerCache();
      return null;
    }
    const data = await resp.json();
    if (!data.authenticated || !data.customer) {
      clearCustomerCache();
      return null;
    }
    localStorage.setItem('customerId', data.customer.id);
    localStorage.setItem('customerData', JSON.stringify(data.customer));
    return data.customer;
  } catch {
    return null;
  }
}

function formatCurrency(n) {
  const locale = window.APP_LANG === 'de' ? 'de-DE' : 'en-IE';
  return '€' + Number(n).toLocaleString(locale, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatNumber(n) {
  const locale = window.APP_LANG === 'de' ? 'de-DE' : 'en-IE';
  return Number(n).toLocaleString(locale);
}

function scoreColorPalette(score) {
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  const hue = Math.round((s / 100) * 120);
  const color = `hsl(${hue}, 55%, 38%)`;
  const colorDark = `hsl(${hue}, 58%, 26%)`;
  const colorMid = `hsl(${hue}, 52%, 40%)`;
  const colorLight = `hsl(${hue}, 48%, 48%)`;
  const glow = `hsla(${hue}, 70%, 45%, 0.28)`;
  const soft = `hsl(${hue}, 70%, 94%)`;
  const track = `hsl(${hue}, 30%, 90%)`;
  return {
    color,
    glow,
    soft,
    track,
    ringFill: colorMid,
    ringTrack: track,
    headerGradient: `linear-gradient(135deg, ${colorDark} 0%, ${colorMid} 52%, ${colorLight} 100%)`,
    bg: soft,
    border: `hsl(${hue}, 55%, 75%)`,
    text: color,
  };
}
