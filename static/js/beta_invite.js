/** Persist beta invite token from URL for API calls (mobile-friendly). */
(function () {
  const params = new URLSearchParams(window.location.search);
  const invite = params.get('invite') || params.get('token');
  if (invite) {
    try {
      sessionStorage.setItem('betaInviteToken', invite);
    } catch (_) { /* private mode */ }
  }
})();
