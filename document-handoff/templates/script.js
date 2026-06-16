document.addEventListener('DOMContentLoaded', () => {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      const link = document.querySelector(`#sidebar a[href="#${e.target.id}"]`);
      if (link) link.classList.toggle('active', e.isIntersecting);
    });
  }, { threshold: 0.1, rootMargin: '-80px 0px -80%' });
  document.querySelectorAll('section[id]').forEach(s => obs.observe(s));
});
