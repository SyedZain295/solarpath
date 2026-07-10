/** Persist beta invite token and append to internal links. */
(function () {
  const STORAGE_KEY = 'betaInviteToken';
  const STORAGE_AT = 'betaInviteTokenAt';
  const TTL_MS = 30 * 24 * 60 * 60 * 1000;

  function defaultInvite() {
    return window.BETA_INVITE_DEFAULT || '';
  }

  function readStoredInvite() {
    try {
      const at = parseInt(localStorage.getItem(STORAGE_AT) || '0', 10);
      const token = localStorage.getItem(STORAGE_KEY) || '';
      if (token && at && Date.now() - at > TTL_MS) {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(STORAGE_AT);
        return '';
      }
      return token;
    } catch (_) {
      return '';
    }
  }

  function storeInvite(invite) {
    if (!invite) return;
    try {
      sessionStorage.setItem(STORAGE_KEY, invite);
      localStorage.setItem(STORAGE_KEY, invite);
      localStorage.setItem(STORAGE_AT, String(Date.now()));
    } catch (_) { /* private mode */ }
  }

  function appendInvite(href) {
    const invite = defaultInvite();
    if (!invite || !href || typeof href !== 'string') return href;
    if (!href.startsWith('/') || href.startsWith('//')) return href;
    if (href.includes('invite=') || href.includes('token=')) return href;
    const hashIdx = href.indexOf('#');
    const base = hashIdx >= 0 ? href.slice(0, hashIdx) : href;
    const hash = hashIdx >= 0 ? href.slice(hashIdx) : '';
    const join = base.includes('?') ? '&' : '?';
    return `${base}${join}invite=${encodeURIComponent(invite)}${hash}`;
  }

  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get('invite') || params.get('token');
  if (fromUrl) {
    storeInvite(fromUrl);
  } else {
    const stored = readStoredInvite();
    if (stored) {
      try { sessionStorage.setItem(STORAGE_KEY, stored); } catch (_) {}
    }
  }

  function patchLinks(root) {
    const invite = defaultInvite();
    if (!invite) return;
    (root || document).querySelectorAll('a[href^="/"]').forEach((a) => {
      const href = a.getAttribute('href');
      if (!href) return;
      const next = appendInvite(href);
      if (next !== href) a.setAttribute('href', next);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => patchLinks(document));
  } else {
    patchLinks(document);
  }

  window.solarPathAppendInvite = appendInvite;
})();
