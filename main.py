#
## Imports
import hashlib
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import cache
from itertools import chain
from pathlib import Path

import markdown2
import typer
from cogapp import Cog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape
from PIL import Image

##

app = typer.Typer()


def hashed_name(path: str) -> str:
    p = Path(path)
    return f"{p.stem}-{hashlib.md5(p.read_bytes()).hexdigest()[:8]}{p.suffix}"


# Files copied to `docs` under a content-hashed name.
HASHED_FILES = ["pygments.css", "site.css", "site.js"]


@app.command()
def build():
    hashed = {x: hashed_name(x) for x in HASHED_FILES}

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    hashed_urls = {k: f"/{v}" for k, v in hashed.items()}

    ## Making thumbnails
    for filepath in Path("docs/assets").iterdir():
        if not filepath.name.endswith((".jpg", ".jpeg", ".png", ".gif")):
            continue
        if "th__" in filepath.stem:
            continue

        th_filepath = filepath.parent / ("th__" + filepath.stem + ".jpg")
        if th_filepath.exists():
            continue

        img = Image.open(filepath)
        if filepath.name.endswith(".gif"):
            img.putpalette(img.getpalette())  # ty:ignore[invalid-argument-type]
            new_im = Image.new("RGB", img.size)
            new_im.paste(img)
            img = new_im

        if img.mode == "RGBA":
            img = img.convert("RGB")

        w, h = img.size
        MAX_SIZE = 300
        if h > w:
            if h > MAX_SIZE:
                r = h / MAX_SIZE
                h = MAX_SIZE
                w = int(w / r)
        else:
            if w > MAX_SIZE:
                r = w / MAX_SIZE
                w = MAX_SIZE
                h = int(h / r)

        img = img.resize((w, h))
        print(f"Saving '{th_filepath}'...")
        img.save(th_filepath, optimize=True)
    ##

    make_webps()

    for x in chain.from_iterable(
        Path("docs").glob(f"{Path(f).stem}-*{Path(f).suffix}") for f in HASHED_FILES
    ):
        x.unlink(missing_ok=True)
    for source, name in hashed.items():
        shutil.copyfile(source, Path("docs") / name)

    pairs = [
        (
            x,
            Path("docs")
            / x.parent.relative_to("pages")
            / (x.stem.split("__", 1)[0] + ".html"),
        )
        for x in Path("pages").rglob("*.md")
    ]
    for source_path, output_path in pairs:
        print(f'Generating from "{source_path}" - "{output_path}"...')

        markdown_contents = (
            source_path.read_text(encoding="utf-8")
            .replace("/docs/index.html", "/")
            .replace("/docs/en.html", "/en")
            .replace("docs/assets/", "assets/")
        )

        os.makedirs(output_path.parent, exist_ok=True)
        if markdown_contents.startswith(PORTFOLIO_LAYOUT):
            hero, sections = parse_portfolio(markdown_contents)
            rendered = env.get_template("portfolio.html").render(
                hashed=hashed_urls,
                hero=hero,
                sections=sections,
                ransom_letters=ransom_letters,
                size_attrs=size_attrs,
                picture=picture,
                thumb_url=thumb_url,
            )
        else:
            title = next(
                (
                    line.removeprefix("# ").strip()
                    for line in markdown_contents.split("\n")
                    if line.startswith("# ")
                ),
                "",
            )
            rendered = env.get_template("page.html").render(
                hashed=hashed_urls,
                title=title,
                content=render_page_content(markdown_contents),
            )
        output_path.write_text(rendered, encoding="utf-8", newline="\n")

        print(f'Generated "{source_path}" - "{output_path}"!')


def process_line(line: str) -> str:
    if line.startswith("!SPOILER_START"):
        line = line.removeprefix("!SPOILER_START")
        if line.strip() == "":
            line = "Подробнее"
        return f"<details><summary>{line}</summary>"
    elif line.startswith("!SPOILER_END"):
        return "</details>"
    if line.startswith("!FLEX_WRAP_START"):
        return """<div class="hulvdan_flex hulvdan_flex_wrap">"""
    elif line.startswith("!FLEX_START"):
        return """<div class="hulvdan_flex">"""
    elif line.startswith("!FLEX_END"):
        return "</div>"

    line = line.replace(" -> ", " ➜ ").replace(r" \-\> ", " -> ")

    if line.startswith("!IMAGES "):
        images = [i.strip() for i in line.removeprefix("!IMAGES ").split() if i]
        return '<div class="gallery">{}</div>'.format(
            "".join(
                f'<button data-full="/assets/{i}"{size_attrs(i)} aria-label="Открыть">'
                f"{picture('/' + thumb_url(i), hires=i.endswith('.gif'))}</button>"
                for i in images
            )
        )

    if line.startswith("!YOUTUBE_"):
        video_id = line.split("_", 1)[-1].strip()

        loop = 0
        if video_id.startswith("!LOOP_"):
            video_id = video_id.split("_", 1)[-1].strip()
            loop = 1

        return (
            f'<div class="video"><iframe allowfullscreen loop={loop}'
            f' src="https://www.youtube-nocookie.com/embed/{video_id}"></iframe></div>'
        )

    if line.startswith("!PAGE "):
        page_number = line.strip().split(" ", 1)[-1].strip()
        return f'<p class="page-number">{page_number}</p>'

    return line


def article_image(m: re.Match) -> str:
    url, alt = m[1], m[2]
    if not url.startswith("/assets/"):
        return m[0]
    name = url.removeprefix("/assets/")
    tag = picture("/" + thumb_url(name), alt, lazy=False, hires=True)
    return str(tag).replace("<img ", f'<img data-full="{url}"{size_attrs(name)} ', 1)


def render_page_content(markdown_contents: str) -> Markup:
    markdown_contents = re.sub(r"#{[^}]*}#", "", markdown_contents)
    markdown_contents = "\n".join(
        process_line(line) for line in markdown_contents.split("\n")
    )
    html = markdown2.markdown(
        markdown_contents.replace(" - ", " — "),
        extras=["markdown-in-html", "fenced-code-blocks"],
    )
    html = re.sub(r'<img src="([^"]+)" alt="([^"]*)" />', article_image, html)
    return Markup(html)


## Portfolio layout
# Pages starting with `!LAYOUT portfolio` are rendered with `templates/portfolio.html`.
#
# `# Name` + `!TAGLINE` + text + `!CONTACT <kind> <url>` before the first `##` form the hero.
# Each `## Section` becomes a block:
#   - with `### Title` cards (`!STICKER`, `!GENRE`, `!DATE`, `!COVER`,
#     `!IMAGES a.png youtube:<id>`,
#     `!TAGS a, b`, `!VIDEO <label> <youtube id>`, `!LINK <label> <url>`, `- note`);
#   - `!IMAGES` -> image grid;
#   - `- [text](url)` lines -> list of links;
#   - anything else -> plain markdown.

PORTFOLIO_LAYOUT = "!LAYOUT portfolio"

CONTACTS = {
    "github": "GitHub",
    "itch": "itch.io",
    "mail": "Почта",
}

LINK_ICONS = {
    "Steam": "steam",
    "itch.io": "itch",
    "Reddit": "reddit",
    "GitHub": "github",
}

TAG_URLS = {
    "Godot": "https://godotengine.org",
    "Python": "https://www.python.org",
    "Clip Studio": "https://www.clipstudio.net",
    "Reaper": "https://www.reaper.fm",
    "AutoHotkey": "https://www.autohotkey.com",
    "C++": "https://bkaradzic.github.io/posts/orthodoxc++/",
    "SDL": "https://www.libsdl.org",
    "bgfx": "https://github.com/bkaradzic/bgfx",
    "miniaudio": "https://miniaud.io",
    "flatbuffers": "https://flatbuffers.dev",
    "LDtk": "https://ldtk.io",
    "Raylib": "https://www.raylib.com",
    "glm": "https://github.com/g-truc/glm",
    "OpenGL": "https://www.opengl.org",
    "Unity": "https://unity.com",
    "C#": "https://learn.microsoft.com/dotnet/csharp/",
    "FMOD": "https://www.fmod.com",
    "Pillow": "https://python-pillow.org",
    "PyQt": "https://www.riverbankcomputing.com/software/pyqt/",
}

# (font, background, foreground) for each letter of the hero title.
RANSOM_STYLES = [
    ("Anton", "#f5eeb0", "#000"),
    ("Archivo Black", "#000", "#f5eeb0"),
    ("Playfair Display", "#fabf61", "#000"),
    ("Rubik Mono One", "#000", "#fabf61"),
    ("Anton", "#fabf61", "#000"),
    ("Archivo Black", "#f5eeb0", "#000"),
    ("Playfair Display", "#000", "#fabf61"),
]
RANSOM_ROTATIONS = [-7, 4, -3, 6, -5, 3, -8]


@dataclass
class Link:
    label: str
    url: str
    icon: str = ""


@dataclass
class Hero:
    name: str = ""
    tagline: str = ""
    intro: Markup = field(default_factory=Markup)
    contacts: list[Link] = field(default_factory=list)


@dataclass
class Card:
    title: str
    id: str = ""
    sticker: str = ""
    genre: str = ""
    date: str = ""
    cover: str = ""
    images: list[str] = field(default_factory=list)
    tags: list[Link] = field(default_factory=list)
    actions: list[Link] = field(default_factory=list)
    notes: list[Markup] = field(default_factory=list)


@dataclass
class Section:
    title: str
    id: str = ""
    cards: list[Card] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    body: Markup = field(default_factory=Markup)


def slugify(text: str) -> str:
    return re.sub(r"[^\w]+", "-", text.lower().replace("'", "")).strip("-")


def assign_ids(sections: list[Section]) -> None:
    """Gives sections and cards unique anchor ids made from their titles."""
    used: set[str] = set()

    def unique(title: str) -> str:
        base = slugify(title)
        slug, n = base, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        return slug

    for section in sections:
        section.id = unique(section.title)
        for card in section.cards:
            card.id = unique(card.title)


## WebP
# Every image in docs/assets gets a `<name>.webp` next to it (`a.png` -> `a.png.webp`).
# Pages serve it through `<picture>`, browsers without WebP fall back to the original.
# WEBP_MANIFEST maps each source to its md5 and whether its WebP was kept (a WebP that
# isn't smaller than the original is dropped). Hashes, not mtimes: git checkouts reset mtimes.

WEBP_SOURCES = (".png", ".jpg", ".jpeg", ".gif")
WEBP_MANIFEST = Path("docs/assets/.webp.json")


def webp_path(source: Path) -> Path:
    return source.with_name(source.name + ".webp")


def webp_sources() -> list[Path]:
    return sorted(
        x for x in Path("docs/assets").iterdir() if x.suffix.lower() in WEBP_SOURCES
    )


def file_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_webp_manifest() -> dict[str, dict]:
    if not WEBP_MANIFEST.exists():
        return {}
    return json.loads(WEBP_MANIFEST.read_text(encoding="utf-8"))


def webp_is_fresh(source: Path, manifest: dict[str, dict]) -> bool:
    entry = manifest.get(source.name)
    return (
        entry is not None
        and entry["md5"] == file_md5(source)
        and (not entry["webp"] or webp_path(source).exists())
    )


def convert_to_webp(source: Path) -> bool:
    """Returns whether the WebP turned out smaller and was kept."""
    out = webp_path(source)
    with Image.open(source) as img:
        if source.suffix == ".gif":
            img.save(out, "WEBP", save_all=True, lossless=True, method=4)
        elif source.suffix == ".png":
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if img.has_transparency_data else "RGB")
            img.save(out, "WEBP", lossless=True, method=4)
        else:
            img.save(out, "WEBP", quality=82, method=4)

    if out.stat().st_size < source.stat().st_size:
        return True
    out.unlink()
    return False


def make_webps() -> None:
    manifest = load_webp_manifest()
    sources = webp_sources()
    todo = [x for x in sources if not webp_is_fresh(x, manifest)]
    if todo:
        print(f"Converting {len(todo)} images to WebP...")
        with ProcessPoolExecutor(max_workers=6) as executor:
            kept = list(executor.map(convert_to_webp, todo))
        for x, k in zip(todo, kept, strict=True):
            manifest[x.name] = {"md5": file_md5(x), "webp": k}

    # Forget deleted sources and their WebPs.
    names = {x.name for x in sources}
    for name in [n for n in manifest if n not in names]:
        del manifest[name]
        webp_path(Path("docs/assets") / name).unlink(missing_ok=True)

    text = json.dumps(dict(sorted(manifest.items())), indent=2) + "\n"
    if not WEBP_MANIFEST.exists() or WEBP_MANIFEST.read_text(encoding="utf-8") != text:
        WEBP_MANIFEST.write_text(text, encoding="utf-8", newline="\n")


def thumb_url(name: str) -> str:
    """Static thumbnail of an asset (gifs too), or the asset itself when there is none."""
    th = f"th__{Path(name).stem}.jpg"
    return f"assets/{th if (Path('docs/assets') / th).exists() else name}"


def picture(url: str, alt: str = "", lazy: bool = True, hires: bool = False) -> Markup:
    """`<img>` for an asset url, wrapped in `<picture>` with a WebP source when there is one.

    `hires`: the url is a thumbnail, `site.js` swaps in the full image (from the closest
    `[data-full]`) once it's downloaded.
    """
    url = str(url)
    loading = ' loading="lazy"' if lazy else ""
    cls = ' class="hires"' if hires else ""
    img = f'<img{cls}{loading} src="{escape(url)}" alt="{escape(alt)}" />'
    if not webp_path(Path("docs") / url.lstrip("/")).exists():
        return Markup(img)
    return Markup(
        f'<picture><source type="image/webp" srcset="{escape(url)}.webp" />{img}</picture>'
    )


##


@cache
def image_size(name: str) -> tuple[int, int]:
    with Image.open(Path("docs/assets") / name) as img:
        return img.size


def size_attrs(name: str) -> Markup:
    """`data-w` / `data-h` (+ `data-webp`) of an asset, the gallery needs them for slides."""
    w, h = image_size(name)
    attrs = f' data-w="{w}" data-h="{h}"'
    if webp_path(Path("docs/assets") / name).exists():
        attrs += ' data-webp="1"'
    return Markup(attrs)


def md_inline(text: str) -> Markup:
    rendered = markdown2.markdown(text).strip()
    rendered = rendered.replace(
        '<a href="http', '<a target="_blank" rel="noopener" href="http'
    )
    return Markup(re.sub(r"^<p>(.*)</p>$", r"\1", rendered, flags=re.DOTALL))


def directive(line: str, name: str) -> str | None:
    prefix = f"!{name} "
    return line.removeprefix(prefix).strip() if line.startswith(prefix) else None


def split_label_value(text: str) -> tuple[str, str]:
    label, value = text.rsplit(" ", 1)
    return label.strip(), value.strip()


def ransom_letters(name: str) -> list[tuple[str, str]]:
    """Returns (letter, inline style) pairs for the hero title."""
    letters = []
    for i, ch in enumerate(name.upper()):
        font, bg, fg = RANSOM_STYLES[i % len(RANSOM_STYLES)]
        rot = RANSOM_ROTATIONS[i % len(RANSOM_ROTATIONS)]
        style = (
            f"font-family:'{font}';background:{bg};color:{fg};"
            f"transform:rotate({rot}deg) translateY({6 if i % 2 else -4}px);"
        )
        if font == "Playfair Display":
            style += "font-style:italic;font-weight:900;"
        letters.append((ch, style))
    return letters


def parse_hero(lines: list[str]) -> Hero:
    hero, text = Hero(), []
    for line in lines:
        if line.startswith("# "):
            hero.name = line.removeprefix("# ").strip()
        elif (v := directive(line, "TAGLINE")) is not None:
            hero.tagline = v
        elif (v := directive(line, "CONTACT")) is not None:
            kind, url = v.split(" ", 1)
            hero.contacts.append(Link(CONTACTS[kind], url.strip(), kind))
        else:
            text.append(line)
    hero.intro = Markup(markdown2.markdown("\n".join(text)).strip())
    return hero


def parse_card(title: str, lines: list[str]) -> Card:
    card = Card(title)
    for line in lines:
        if (v := directive(line, "STICKER")) is not None:
            card.sticker = v
        elif (v := directive(line, "GENRE")) is not None:
            card.genre = v
        elif (v := directive(line, "DATE")) is not None:
            card.date = v
        elif (v := directive(line, "COVER")) is not None:
            card.cover = v
        elif (v := directive(line, "IMAGES")) is not None:
            card.images += v.split()
        elif (v := directive(line, "TAGS")) is not None:
            tags = [t.strip() for t in v.split(",") if t.strip()]
            card.tags += [Link(t, TAG_URLS.get(t, "")) for t in tags]
        elif (v := directive(line, "VIDEO")) is not None:
            label, video_id = split_label_value(v)
            card.actions.append(Link(label, f"https://youtu.be/{video_id}", "youtube"))
        elif (v := directive(line, "LINK")) is not None:
            label, url = split_label_value(v)
            icon = LINK_ICONS.get(label.split(" ")[0], "")
            card.actions.append(Link(label, url, icon))
        elif line.startswith("- "):
            card.notes.append(md_inline(line.removeprefix("- ").strip()))
        elif line.strip():
            card.notes.append(md_inline(line.strip()))

    if not card.cover:
        card.cover, card.images = card.images[0], card.images[1:]
    return card


def parse_section(title: str, lines: list[str]) -> Section:
    section = Section(title)

    if any(line.startswith("### ") for line in lines):
        card_title, card_lines = "", []
        for line in lines + ["### "]:
            if line.startswith("### "):
                if card_title:
                    section.cards.append(parse_card(card_title, card_lines))
                card_title, card_lines = line.removeprefix("### ").strip(), []
            else:
                card_lines.append(line)
        return section

    section.images = [
        i for line in lines for i in (directive(line, "IMAGES") or "").split()
    ]
    for line in lines:
        if m := re.fullmatch(r"- \[(.+)\]\((.+)\)", line.strip()):
            section.links.append(Link(md_inline(m[1]), m[2]))
    if not section.images and not section.links:
        section.body = Markup(markdown2.markdown("\n".join(lines)))
    return section


def parse_portfolio(markdown_contents: str) -> tuple[Hero, list[Section]]:
    text = re.sub(r"<!--.*?-->", "", markdown_contents, flags=re.DOTALL)
    text = re.sub(r"#{[^}]*}#", "", text)
    text = text.replace(" -> ", " ➜ ").replace(" - ", " — ")
    lines = [
        line
        for line in text.split("\n")
        if not line.startswith((PORTFOLIO_LAYOUT, "!SPOILER_START", "!SPOILER_END"))
    ]

    first_section = next(
        (i for i, line in enumerate(lines) if line.startswith("## ")), len(lines)
    )
    sections, title, section_lines = [], "", []
    for line in lines[first_section:] + ["## "]:
        if line.startswith("## "):
            if title:
                sections.append(parse_section(title, section_lines))
            title, section_lines = line.removeprefix("## ").strip(), []
        else:
            section_lines.append(line)

    assign_ids(sections)
    return parse_hero(lines[:first_section]), sections


##


@app.command()
def check_images():
    """Fails unless every image has an up-to-date, tracked WebP."""
    errors = []
    manifest = load_webp_manifest()
    for x in webp_sources():
        if not webp_is_fresh(x, manifest):
            errors.append(f"{x}: WebP is missing or stale")

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "docs/assets"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    errors += [f"{x}: not added to git" for x in untracked]

    if errors:
        print("\n".join(errors))
        print("\nRun `uv run python main.py build` and `git add docs/assets`")
        raise typer.Exit(1)


@app.command()
def cog():
    """Regenerates `[[[cog ... ]]]` blocks in the site pages."""
    files = [x.as_posix() for x in Path("pages").rglob("*.md")]
    markers = "[[[cog cog]]] [[[end]]]"
    ret = Cog().main(
        ["cog", "-n", "utf-8", "-U", "-r", "-P", "--markers", markers, *files]
    )
    raise typer.Exit(ret)


@app.command()
def gitf():  ##
    for i in range(2):
        try:
            subprocess.run("git add -A", check=True)
            subprocess.run("git commit -m f", check=True)
            break
        except Exception:
            if i:
                raise
            continue
    subprocess.run("git push", check=False)
    ##


if __name__ == "__main__":
    app()
