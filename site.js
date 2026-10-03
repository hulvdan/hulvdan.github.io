// ---------- lightbox ----------
// Plain markdown images in articles open in the lightbox too.
document.querySelectorAll(".article img:not([data-full] img)").forEach((img) => {
  img.dataset.full = img.src;
});

const items = [...document.querySelectorAll("[data-full], [data-video]")];
const lb = document.getElementById("lb");
const lbImg = document.getElementById("lbImg");
const lbVideo = document.getElementById("lbVideo");
let cur = 0;
const show = (i) => {
  cur = (i + items.length) % items.length;
  const { full, video } = items[cur].dataset;
  lbImg.hidden = !full;
  lbVideo.hidden = !video;
  if (full) lbImg.src = full;
  lbVideo.src = video ? `https://www.youtube-nocookie.com/embed/${video}?autoplay=1` : "";
};

document.addEventListener("click", (e) => {
  const item = e.target.closest("[data-full], [data-video]");
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
lb.addEventListener("close", () => (lbVideo.src = ""));
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

// ---------- anchors ----------
// Web fonts and images load after the browser's initial jump to `#id` and can push the
// target down. Repeat the jump once they're in, unless the visitor already scrolled.
if (location.hash) {
  let userScrolled = false;
  for (const ev of ["wheel", "touchstart", "keydown"])
    addEventListener(ev, () => (userScrolled = true), { once: true, passive: true });

  const jumpToHash = () => {
    if (userScrolled) return;
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    target?.scrollIntoView({ behavior: "instant", block: "start" });
  };
  jumpToHash();
  document.fonts?.ready.then(jumpToHash);
  addEventListener("load", jumpToHash);
}
