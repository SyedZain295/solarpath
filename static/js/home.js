// Home page – pricing card clicks + scroll reveal

document.addEventListener('DOMContentLoaded', () => {
  const withInvite = (path) => (
    typeof window.solarPathAppendInvite === 'function'
      ? window.solarPathAppendInvite(path)
      : path
  );

  document.querySelectorAll('.pricing-card-clickable').forEach((card) => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
      if (e.target.closest('a')) return;
      const plan = card.dataset.plan;
      if (plan) window.location.href = withInvite(`/suppliers/checkout?plan=${plan}`);
    });
  });

  const revealEls = document.querySelectorAll('.section-reveal, .stagger-children');
  const revealNow = (el) => el.classList.add('is-visible');

  const revealInViewport = () => {
    revealEls.forEach((el) => {
      if (el.classList.contains('is-visible')) return;
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.92 && rect.bottom > 0) {
        revealNow(el);
      }
    });
  };

  if (!revealEls.length) return;

  revealInViewport();

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            revealNow(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -20px 0px' }
    );
    revealEls.forEach((el) => {
      if (!el.classList.contains('is-visible')) observer.observe(el);
    });
  } else {
    revealEls.forEach(revealNow);
  }

  window.addEventListener('load', revealInViewport);
  setTimeout(revealInViewport, 120);
});
