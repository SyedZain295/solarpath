// Home page – pricing card clicks + scroll reveal

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.pricing-card-clickable').forEach((card) => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
      if (e.target.closest('a')) return;
      const plan = card.dataset.plan;
      if (plan) window.location.href = `/suppliers/checkout?plan=${plan}`;
    });
  });

  const revealEls = document.querySelectorAll('.section-reveal, .stagger-children');
  if (revealEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    revealEls.forEach((el) => observer.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('is-visible'));
  }
});
