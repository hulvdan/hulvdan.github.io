// ---------- gallery (PhotoSwipe) ----------
// Every card / image grid / article is its own gallery, so arrows never leave the project.
const PHOTOSWIPE = "https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/photoswipe.esm.min.js";
const GALLERY = ".card, .gifs, .article";
const ITEM = "[data-full], [data-video]";
// Gallery button titles, by <html lang>.
const UI = {
  en: ["Previous", "Next", "Close"],
  ru: ["Назад", "Вперёд", "Закрыть"],
  de: ["Zurück", "Weiter", "Schließen"],
  fr: ["Précédent", "Suivant", "Fermer"],
  es: ["Anterior", "Siguiente", "Cerrar"],
};
const [PREV, NEXT, CLOSE] = UI[document.documentElement.lang] || UI.en;

// Other markdown images in articles open in the gallery too.
document.querySelectorAll(".article img:not([data-full]):not([data-full] img)").forEach((img) => {
  img.dataset.full = img.src;
});

const icon = (shape) =>
  `<svg class="pswp__icn" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">${shape}</svg>`;

// Resolves to whether the browser decodes WebP (1x1 lossless probe).
const webpSupport = new Promise((resolve) => {
  const probe = new Image();
  probe.onload = () => resolve(probe.width > 0);
  probe.onerror = () => resolve(false);
  probe.src = "data:image/webp;base64,UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==";
});
const fullUrl = (owner, webp) =>
  owner.dataset.webp && webp ? `${owner.dataset.full}.webp` : owner.dataset.full;

// ---------- thumbnails first ----------
// `img.hires` starts as a small static thumbnail; the full image / animated gif is swapped
// in once it's downloaded. Its url comes from the closest `[data-full]`.
const upgrade = async (img) => {
  const owner = img.closest("[data-full]");
  if (!owner) return;
  const url = fullUrl(owner, await webpSupport);
  const full = new Image();
  full.onload = () => {
    img.parentElement.querySelectorAll("picture > source").forEach((s) => s.remove());
    img.src = url;
  };
  full.src = url;
};
const hiresIO = new IntersectionObserver(
  (entries) =>
    entries.forEach((en) => {
      if (en.isIntersecting) {
        hiresIO.unobserve(en.target);
        upgrade(en.target);
      }
    }),
  { rootMargin: "300px" },
);
document.querySelectorAll("img.hires").forEach((img) => hiresIO.observe(img));

const toSlide = (el, webp) => {
  const img = el.tagName === "IMG" ? el : el.querySelector("img");
  if (el.dataset.video) {
    const src = `https://www.youtube-nocookie.com/embed/${el.dataset.video}?autoplay=1`;
    return {
      html: `<div class="pswp-video"><iframe data-src="${src}" allow="autoplay; fullscreen" allowfullscreen></iframe></div>`,
      element: img,
    };
  }
  return {
    src: fullUrl(el, webp),
    width: +el.dataset.w || img?.naturalWidth || 1600,
    height: +el.dataset.h || img?.naturalHeight || 900,
    // Shown while the original is downloading. `currentSrc` is empty for images that haven't loaded yet (lazy).
    msrc: img?.currentSrc || img?.src,
    element: img,
    thumbCropped: true,
    alt: img?.alt || "",
  };
};

const openGallery = async (item) => {
  const gallery = item.closest(GALLERY) || document.body;
  const items = [...gallery.querySelectorAll(ITEM)];
  const title =
    gallery.querySelector(".body h3, h1")?.textContent ||
    gallery.closest("section")?.querySelector("h2")?.textContent ||
    "";
  const [{ default: PhotoSwipe }, webp] = await Promise.all([import(PHOTOSWIPE), webpSupport]);
  const pswp = new PhotoSwipe({
    dataSource: items.map((el) => toSlide(el, webp)),
    index: items.indexOf(item),
    bgOpacity: 1,
    showHideAnimationType: "zoom",
    imageClickAction: "zoom",
    tapAction: "toggle-controls",
    // Keep the image clear of the buttons, so a click near an edge never hits a control.
    paddingFn: (viewport) =>
      viewport.x > 860
        ? { top: 90, bottom: 90, left: 110, right: 110 }
        : { top: 80, bottom: 160, left: 0, right: 0 },
    zoom: false, // clicking the image zooms already
    // Mouse wheel zooms towards the cursor, a click zooms into the clicked spot, drag pans.
    // Levels are relative to "fit", so small gifs zoom as well as big screenshots.
    wheelToZoom: true,
    secondaryZoomLevel: (zoom) => zoom.fit * 2.5,
    maxZoomLevel: (zoom) => zoom.fit * 6,
    arrowPrevTitle: PREV,
    arrowNextTitle: NEXT,
    closeTitle: CLOSE,
    arrowPrevSVG: icon('<polygon points="21,5 7,16 21,27"/>'),
    arrowNextSVG: icon('<polygon points="11,5 25,16 11,27"/>'),
    closeSVG: icon('<path d="M8 8 24 24M24 8 8 24" fill="none" stroke-width="5"/>'),
  });
  pswp.on("uiRegister", () => {
    pswp.ui.registerElement({
      name: "caption",
      order: 9,
      isButton: false,
      appendTo: "root",
      onInit: (el) => (el.textContent = title.trim()),
    });
  });
  // Only the current slide's video gets a `src`: neighbours are preloaded and would autoplay.
  const syncVideos = () =>
    pswp.element?.querySelectorAll("iframe[data-src]").forEach((frame) => {
      if (pswp.currSlide?.container.contains(frame)) {
        if (!frame.getAttribute("src")) frame.src = frame.dataset.src;
      } else frame.removeAttribute("src");
    });
  pswp.on("change", syncVideos);
  pswp.on("contentAppend", () => setTimeout(syncVideos));
  // Arrows / keyboard slide like a swipe instead of jumping.
  pswp.next = () => pswp.mainScroll.moveIndexBy(1, true);
  pswp.prev = () => pswp.mainScroll.moveIndexBy(-1, true);
  pswp.init();
};

// The plate is taken at press time: the title shakes and jitters on hover, so by the time
// `click` fires (and its target is resolved) the cursor may sit over a neighbour.
let pressedPlate = null;
document.addEventListener("pointerdown", (e) => {
  pressedPlate = e.target.closest(".ransom b");
});

document.addEventListener("click", (e) => {
  const item = e.target.closest(ITEM);
  if (item) {
    e.preventDefault();
    openGallery(item);
    return;
  }

  // ---------- shake on title click ----------
  const title = e.target.closest(".body h3, .ransom, .tagline, .intro");
  if (title) {
    title.classList.remove("shake");
    void title.offsetWidth;
    title.classList.add("shake");
  }

  if (title?.matches(".ransom") && location.hash)
    history.replaceState(null, "", location.pathname + location.search);
  // Hero name: only the letter under the cursor changes. A click beside the plates
  // (the row is as wide as the page) changes nothing.
  if (pressedPlate) {
    lockWidth(pressedPlate);
    curse(pressedPlate, 1);
  }
  if (title?.matches(".tagline")) curse(title, 1);
  if (title?.matches(".intro")) curse(title, 3 + Math.floor(Math.random() * 3));
});

// ---------- hero curses on click ----------
// Every click turns random letters into comic-style swear symbols, never the same as
// their neighbours. Already cursed letters get re-cursed, so it keeps changing.
const GRAWLIX = "#%$^&@*!?-+\\/=[]{}()|";
const randomOf = (list) => list[Math.floor(Math.random() * list.length)];
const curse = (root, count) => {
  // Candidates: every letter in plain text, plus every symbol cursed earlier.
  const spots = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node; (node = walker.nextNode()); ) {
    if (node.parentElement.classList.contains("grawlix")) {
      spots.push([node, 0]);
      continue;
    }
    for (let i = 0; i < node.data.length; i++)
      if (/\p{L}/u.test(node.data[i])) spots.push([node, i]);
  }
  // Distinct spots, last first: splitting a text node keeps the offsets before the split valid.
  const picked = new Set();
  while (picked.size < Math.min(count, spots.length))
    picked.add(Math.floor(Math.random() * spots.length));
  [...picked].sort((a, b) => b - a).forEach((k) => curseSpot(...spots[k]));
};
// A symbol is narrower, wider or taller than the letter it replaces: keep the plate's size (in em,
// so it still scales with the title).
const lockWidth = (plate) => {
  if (plate.style.width) return;
  const em = parseFloat(getComputedStyle(plate).fontSize);
  plate.style.width = `${plate.offsetWidth / em}em`;
  plate.style.height = `${plate.offsetHeight / em}em`;
};
const curseSpot = (node, i) => {
  let sym = node.parentElement;
  if (!sym.classList.contains("grawlix")) {
    const letter = node.splitText(i);
    letter.splitText(1);
    sym = document.createElement("i");
    letter.replaceWith(sym);
  }
  const taken = [
    sym.textContent,
    sym.previousSibling?.textContent.at(-1),
    sym.nextSibling?.textContent[0],
  ];
  let ch;
  do ch = randomOf(GRAWLIX);
  while (taken.includes(ch));
  sym.className = "";
  void sym.offsetWidth;
  sym.className = "grawlix";
  sym.textContent = ch;
  sym.style.setProperty("--r", `${Math.round(Math.random() * 50 - 25)}deg`);
};

// ---------- reveal on scroll ----------
const makeRevealObserver = (options) => {
  const observer = new IntersectionObserver(
    (entries) =>
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add("in");
          observer.unobserve(en.target);
        }
      }),
    options,
  );
  return observer;
};
const io = makeRevealObserver({ threshold: 0.15 });
// Section headers trigger only once they're well inside the viewport,
// so the first one isn't already revealed on the top of the page.
const ioHead = makeRevealObserver({ threshold: 0.15, rootMargin: "0px 0px -25% 0px" });
document
  .querySelectorAll(".reveal")
  .forEach((el) => (el.classList.contains("sec-head") ? ioHead : io).observe(el));

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

// ---------- language dropdown: closes on outside click / Esc ----------
const langMenu = document.querySelector(".lang-menu");
if (langMenu) {
  document.addEventListener("click", (e) => {
    if (!langMenu.contains(e.target)) langMenu.open = false;
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") langMenu.open = false;
  });
}
