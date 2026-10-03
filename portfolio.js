// ---------- lightbox ----------
const items = [...document.querySelectorAll("[data-full]")];
const lb = document.getElementById("lb");
const lbImg = document.getElementById("lbImg");
let cur = 0;
const show = (i) => {
  cur = (i + items.length) % items.length;
  lbImg.src = items[cur].dataset.full;
};

document.addEventListener("click", (e) => {
  const item = e.target.closest("[data-full]");
  if (item) {
    show(items.indexOf(item));
    lb.showModal();
    return;
  }

  // ---------- shake on title click ----------
  const title = e.target.closest(".body h3, .ransom");
  if (title) {
    title.classList.remove("shake");
    void title.offsetWidth;
    title.classList.add("shake");
  }
});

document.getElementById("lbPrev").onclick = () => show(cur - 1);
document.getElementById("lbNext").onclick = () => show(cur + 1);
document.getElementById("lbClose").onclick = () => lb.close();
lb.addEventListener("click", (e) => {
  if (e.target === lb) lb.close();
});
addEventListener("keydown", (e) => {
  if (!lb.open) return;
  if (e.key === "ArrowLeft") show(cur - 1);
  if (e.key === "ArrowRight") show(cur + 1);
});

// ---------- reveal on scroll ----------
const io = new IntersectionObserver(
  (entries) =>
    entries.forEach((en) => {
      if (en.isIntersecting) {
        en.target.classList.add("in");
        io.unobserve(en.target);
      }
    }),
  { threshold: 0.15 },
);
document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

setTimeout(() => document.querySelector(".wipe")?.remove(), 1100);
