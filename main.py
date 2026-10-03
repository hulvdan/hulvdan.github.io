#
## Imports
import hashlib
import html
import os
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from itertools import chain
from pathlib import Path

import markdown2
import png
import typer
from PIL import Image

##

app = typer.Typer()


def hashed_name(path: str) -> str:
    p = Path(path)
    return "{}-{}{}".format(
        p.stem, hashlib.md5(p.read_bytes()).hexdigest()[:8], p.suffix
    )


# Files copied to `docs` under a content-hashed name.
HASHED_FILES = ["style.css", "pygments.css", "portfolio.css", "portfolio.js"]


@app.command()
def build():
    hashed = {x: hashed_name(x) for x in HASHED_FILES}

    template_data = (
        Path("index_template.html")
        .read_text()
        .replace("{{ STYLE_CSS }}", f"/{hashed['style.css']}")
        .replace("{{ PYGMENTS_CSS }}", f"/{hashed['pygments.css']}")
    )
    portfolio_template_data = (
        Path("portfolio_template.html")
        .read_text(encoding="utf-8")
        .replace("{{ PORTFOLIO_CSS }}", f"/{hashed['portfolio.css']}")
        .replace("{{ PORTFOLIO_JS }}", f"/{hashed['portfolio.js']}")
    )

    ## Making thumbnails
    for filepath in Path("docs/assets").iterdir():
        if not filepath.name.endswith((".jpg", ".png")):
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
        img.save(th_filepath, progressive=True, optimize=True)
    ##

    for x in chain.from_iterable(
        Path("docs").glob("{}-*{}".format(Path(f).stem, Path(f).suffix))
        for f in HASHED_FILES
    ):
        x.unlink()
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
            output_path.write_text(
                portfolio_template_data.replace(
                    "{content}", render_portfolio(markdown_contents)
                ),
                encoding="utf-8",
            )
            print(f'Generated "{source_path}" - "{output_path}"!')
            continue

        write_file(
            template_data=template_data,
            markdown_contents=markdown_contents,
            output_file_path=output_path,
        )

        print(f'Generated "{source_path}" - "{output_path}"!')


next_nanogallery_id = 0


def process_line(line: str) -> str:
    if line.startswith("!SPOILER_START"):
        line = line.removeprefix("!SPOILER_START")
        if line.strip() == "":
            line = "Подробнее"
        return f"<details><summary>{line}</summary>"
    elif line.startswith("!SPOILER_END"):
        return "</details>"
    if line.startswith("!FLEX_WRAP_START"):
        return """<div class="hulvdan_flex hulvdan_flex_wrap" ''>"""
    elif line.startswith("!FLEX_START"):
        return (
            """<div class="hulvdan_flex" style='display: flex; align-items="center"'>"""
        )
    elif line.startswith("!FLEX_END"):
        return "</div>"

    global next_nanogallery_id

    line = line.replace(" -> ", " ➜ ").replace(r" \-\> ", " -> ")

    if line.startswith("!IMAGES "):
        images = [i.strip() for i in line.removeprefix("!IMAGES ").split() if i]
        line = """<div id="ng{}" data-nanogallery2='{{
            "thumbnailWidth": "150",
            "thumbnailHeight": "100",
            "thumbnailAlignment": "left",
            "thumbnailOpenImage": true,
            "thumbnailHoverEffect2": "imageScale150",
            "thumbnailSliderDelay": 0,
            "thumbnailWaitImageLoaded": false,
            "thumbnailBorderHorizontal": 0,
            "thumbnailBorderVertical": 0,
            "thumbnailGutterWidth": 4,
            "thumbnailGutterHeight": 4,
            "locationHash": false,
            "viewerTools": {{ "topLeft":  "", "topRight": "closeButton" }}
        }}'>{}</div>"""
        line = line.format(
            next_nanogallery_id,
            "".join(
                '<a href="assets/{}" data-ngthumb="assets/th__{}.jpg"></a>'.format(
                    i, Path(i).stem
                )
                for i in images
            ),
        )
        next_nanogallery_id += 1

    if line.startswith("!YOUTUBE_"):
        video_id = line.split("_", 1)[-1].strip()

        loop = 0
        if video_id.startswith("!LOOP_"):
            video_id = video_id.split("_", 1)[-1].strip()
            loop = 1

        # random_value = "".join(
        #     random.choice(string.ascii_letters + string.digits) for _ in range(8)
        # )
        return f"""<p><iframe
            allowfullscreen="true"
            frameborder="0"
            width="480"
            rel=0
            loop={loop}
            style="max-width: 100%; aspect-ratio: 16 / 9;"
            src="https://www.youtube.com/embed/{video_id}"
            ></iframe></p>"""

    if line.startswith("!PAGE "):
        page_number = line.strip().split(" ", 1)[-1].strip()
        return f'<p class="page-number">{page_number}</p>'

    return line


def write_file(*, template_data: str, markdown_contents: str, output_file_path):
    markdown_contents = re.sub(r"#{[^}]*}#", "", markdown_contents)
    markdown_contents = "\n".join(
        process_line(line) for line in markdown_contents.split("\n")
    )

    content = markdown2.markdown(
        markdown_contents.replace(" - ", " — "),
        extras=["markdown-in-html", "fenced-code-blocks"],
    )
    rendered_html = template_data.format(content=content)

    with open(output_file_path, "w", encoding="utf-8") as out_file:
        out_file.write(rendered_html)


## Portfolio layout
# Pages starting with `!LAYOUT portfolio` are rendered with `portfolio_template.html`.
#
# `# Name` + `!TAGLINE` + text + `!CONTACT <kind> <url>` before the first `##` form the hero.
# Each `## Section` becomes a block:
#   - with `### Title` cards (`!STICKER`, `!GENRE`, `!DATE`, `!COVER`, `!IMAGES`,
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

MANY_THUMBS = 4


def md_inline(text: str) -> str:
    rendered = markdown2.markdown(text).strip()
    return re.sub(r"^<p>(.*)</p>$", r"\1", rendered, flags=re.S)


def asset(name: str) -> str:
    return f"assets/{name}"


def thumb(name: str) -> str:
    if name.endswith((".jpg", ".png")):
        return asset(f"th__{Path(name).stem}.jpg")
    return asset(name)


def external(url: str) -> str:
    return ' target="_blank" rel="noopener"' if url.startswith("http") else ""


def directive(line: str, name: str) -> str | None:
    prefix = f"!{name} "
    return line.removeprefix(prefix).strip() if line.startswith(prefix) else None


def split_label_value(text: str) -> tuple[str, str]:
    label, value = text.rsplit(" ", 1)
    return label.strip(), value.strip()


def render_ransom(name: str) -> str:
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
        letters.append(f'<b aria-hidden="true" style="{style}">{html.escape(ch)}</b>')
    return '<h1 class="ransom" aria-label="{}">{}</h1>'.format(
        html.escape(name), "".join(letters)
    )


def render_contacts(contacts: list[tuple[str, str]]) -> str:
    buttons = "".join(
        '<a class="btn icon-only" href="{url}"{ext} aria-label="{label}" title="{label}">'
        '<span class="ico ico-{kind}"></span></a>'.format(
            url=html.escape(url), ext=external(url), label=CONTACTS[kind], kind=kind
        )
        for kind, url in contacts
    )
    return f'<div class="socials">{buttons}</div>'


def render_hero(lines: list[str]) -> tuple[str, list[tuple[str, str]]]:
    name, tagline, contacts, text = "", "", [], []
    for line in lines:
        if line.startswith("# "):
            name = line.removeprefix("# ").strip()
        elif (v := directive(line, "TAGLINE")) is not None:
            tagline = v
        elif (v := directive(line, "CONTACT")) is not None:
            kind, url = v.split(" ", 1)
            contacts.append((kind, url.strip()))
        else:
            text.append(line)

    intro = markdown2.markdown("\n".join(text)).strip()
    hero = (
        '<header class="hero"><div>'
        f"{render_ransom(name)}"
        f'<div class="tagline"><span>{html.escape(tagline)}</span></div>'
        f'<div class="intro">{intro}</div>'
        f"{render_contacts(contacts)}"
        "</div></header>"
    )
    return hero, contacts


def render_card(index: int, title: str, lines: list[str]) -> str:
    sticker, genre, date, cover = "", "", "", ""
    images: list[str] = []
    tags: list[str] = []
    actions: list[str] = []
    notes: list[str] = []
    for line in lines:
        if (v := directive(line, "STICKER")) is not None:
            sticker = v
        elif (v := directive(line, "GENRE")) is not None:
            genre = v
        elif (v := directive(line, "DATE")) is not None:
            date = v
        elif (v := directive(line, "COVER")) is not None:
            cover = v
        elif (v := directive(line, "IMAGES")) is not None:
            images += v.split()
        elif (v := directive(line, "TAGS")) is not None:
            tags += [t.strip() for t in v.split(",") if t.strip()]
        elif (v := directive(line, "VIDEO")) is not None:
            label, video_id = split_label_value(v)
            url = f"https://youtu.be/{video_id}"
            actions.append(
                f'<a class="btn accent" href="{url}"{external(url)}>'
                f'<span class="ico ico-youtube"></span>{html.escape(label)}</a>'
            )
        elif (v := directive(line, "LINK")) is not None:
            label, url = split_label_value(v)
            icon = LINK_ICONS.get(label.split(" ")[0])
            icon_html = f'<span class="ico ico-{icon}"></span>' if icon else ""
            actions.append(
                f'<a class="btn accent" href="{html.escape(url)}"{external(url)}>'
                f"{icon_html}{html.escape(label)}</a>"
            )
        elif line.startswith("- "):
            notes.append(line.removeprefix("- ").strip())
        elif line.strip():
            notes.append(line.strip())

    if not cover:
        cover, images = images[0], images[1:]

    thumbs = "".join(
        f'<button data-full="{asset(i)}" aria-label="Скриншот">'
        f'<img loading="lazy" src="{thumb(i)}" alt="" /></button>'
        for i in images
    )
    many = len(images) > MANY_THUMBS
    tags_html = "".join(
        "<li>{}</li>".format(
            f'<a href="{TAG_URLS[t]}"{external(TAG_URLS[t])}>{html.escape(t)}</a>'
            if t in TAG_URLS
            else f"<span>{html.escape(t)}</span>"
        )
        for t in tags
    )

    parts = [
        f'<article class="card reveal{" from-right" if index % 2 else ""}">',
        '<div class="frame"></div>',
        '<div class="media">',
        f'<span class="sticker">{html.escape(sticker)}</span>' if sticker else "",
        f'<button class="cover" data-full="{asset(cover)}" aria-label="Открыть {html.escape(title)}">'
        f'<img loading="lazy" src="{asset(cover)}" alt="{html.escape(title)}" /></button>',
        f'<div class="thumbs">{thumbs}</div>' if thumbs and not many else "",
        "</div>",
        '<div class="body">',
        f"<h3>{html.escape(title)}</h3>",
        f'<div class="genre">{html.escape(genre)}</div>' if genre else "",
        f'<p class="date">{html.escape(date)}</p>' if date else "",
        '<ul class="notes">{}</ul>'.format(
            "".join(f"<li>{md_inline(n)}</li>" for n in notes)
        )
        if notes
        else "",
        f'<ul class="tags">{tags_html}</ul>' if tags else "",
        f'<div class="actions">{"".join(actions)}</div>' if actions else "",
        "</div>",
        f'<div class="thumbs grid">{thumbs}</div>' if many else "",
        "</article>",
    ]
    return "\n".join(p for p in parts if p)


def render_section(title: str, lines: list[str]) -> str:
    head = f'<div class="sec-head reveal"><h2>{html.escape(title)}</h2></div>'

    if any(line.startswith("### ") for line in lines):
        cards, card_title, card_lines = [], "", []
        for line in lines + ["### "]:
            if line.startswith("### "):
                if card_title:
                    cards.append(render_card(len(cards), card_title, card_lines))
                card_title, card_lines = line.removeprefix("### ").strip(), []
            else:
                card_lines.append(line)
        body = '<div class="cards">{}</div>'.format("\n".join(cards))
    elif images := [
        i for line in lines for i in (directive(line, "IMAGES") or "").split()
    ]:
        body = '<div class="gifs">{}</div>'.format(
            "".join(
                f'<button class="reveal" data-full="{asset(i)}" aria-label="Открыть">'
                f'<img loading="lazy" src="{asset(i)}" alt="" /></button>'
                for i in images
            )
        )
    elif links := [
        m.groups()
        for line in lines
        if (m := re.fullmatch(r"- \[(.+)\]\((.+)\)", line.strip()))
    ]:
        body = '<ol class="requests">{}</ol>'.format(
            "".join(
                f'<li class="reveal"><a href="{html.escape(url)}"{external(url)}>'
                f"<span>{md_inline(text)}</span></a></li>"
                for text, url in links
            )
        )
    else:
        body = markdown2.markdown("\n".join(lines))

    return f"<section>\n{head}\n{body}\n</section>"


def render_portfolio(markdown_contents: str) -> str:
    text = re.sub(r"<!--.*?-->", "", markdown_contents, flags=re.S)
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
    hero, contacts = render_hero(lines[:first_section])
    parts = [hero]

    title, section_lines = "", []
    for line in lines[first_section:] + ["## "]:
        if line.startswith("## "):
            if title:
                parts.append(render_section(title, section_lines))
            title, section_lines = line.removeprefix("## ").strip(), []
        else:
            section_lines.append(line)

    parts.append(f'<div class="outro reveal">{render_contacts(contacts)}</div>')
    return "\n\n".join(parts)


##


def is_interlaced(img: Image.Image) -> bool:
    if img.format == "JPEG":
        return bool(img.info.get("progressive") or img.info.get("progression"))
    if img.format == "PNG":
        return bool(img.info.get("interlace"))
    # GIF isn't supported: Pillow ignores `interlace` when saving animated GIFs.
    return True


def save_interlaced_png(img: Image.Image, fp) -> None:
    # Pillow can't write interlaced PNGs.
    if img.mode == "P" and "transparency" not in img.info:
        palette = img.getpalette() or []
        kwargs = dict(
            palette=[tuple(palette[i : i + 3]) for i in range(0, len(palette), 3)]
        )
    else:
        if img.mode not in ("L", "LA", "RGB", "RGBA"):
            img = img.convert("RGBA" if img.has_transparency_data else "RGB")
        kwargs = dict(
            greyscale=img.mode in ("L", "LA"), alpha=img.mode in ("LA", "RGBA")
        )

    writer = png.Writer(
        img.width, img.height, bitdepth=8, interlace=True, compression=9, **kwargs
    )
    data = img.tobytes()
    stride = len(data) // img.height
    rows = (data[y * stride : (y + 1) * stride] for y in range(img.height))
    writer.write(fp, rows)


def interlace_file(filepath: Path) -> None:
    with Image.open(filepath) as img:
        if is_interlaced(img):
            return

        print(f"Interlacing '{filepath}'...")
        tmp = filepath.with_name(filepath.name + ".tmp")
        with open(tmp, "wb") as fp:
            if img.format == "JPEG":
                img.save(
                    fp,
                    "JPEG",
                    quality="keep",
                    progressive=True,
                    optimize=True,
                    exif=img.info.get("exif", b""),
                    icc_profile=img.info.get("icc_profile"),
                )
            elif img.format == "PNG":
                save_interlaced_png(img, fp)

    tmp.replace(filepath)


@app.command()
def interlace(files: list[Path]):
    """Converts images to interlaced / progressive if they aren't already."""
    # Processes, not threads: pypng is pure Python and holds the GIL.
    with ProcessPoolExecutor(max_workers=6) as executor:
        list(executor.map(interlace_file, files))


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
