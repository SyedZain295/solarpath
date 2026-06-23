/** Branded installer intake – persist ref through calculator → results → quote */

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const ref = params.get('ref') || document.body.dataset.intakeRef || '';
  if (ref) {
    sessionStorage.setItem('intakeInstallerSlug', ref);
  }
});
