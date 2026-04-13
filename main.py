#
## Imports
import hashlib
import os
import shutil
import subprocess
import urllib.parse
from itertools import chain
from pathlib import Path

import markdown2
import typer
from PIL import Image

##

app = typer.Typer()


@app.command()
def build():
    style_css_file_name = "style-{}.css".format(
        hashlib.md5(Path("style.css").read_bytes()).hexdigest()[:8]
    )
    pygments_css_file_name = "pygments-{}.css".format(
        hashlib.md5(Path("pygments.css").read_bytes()).hexdigest()[:8]
    )

    template_data = (
        Path("index_template.html")
        .read_text()
        .replace("{{ STYLE_CSS }}", f"/{style_css_file_name}")
        .replace("{{ PYGMENTS_CSS }}", f"/{pygments_css_file_name}")
    )

    ## Making thumbnails
    for filepath in Path("docs/assets").iterdir():
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
        img.save(th_filepath)
    ##

    for x in chain(
        Path("docs").glob("style-*.css"),
        Path("docs").glob("pygments-*.css"),
    ):
        x.unlink()
    shutil.copyfile("style.css", Path("docs") / style_css_file_name)
    shutil.copyfile("pygments.css", Path("docs") / pygments_css_file_name)

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
        write_file(
            template_data=template_data,
            markdown_contents=markdown_contents,
            output_file_path=output_path,
        )

        print(f'Generated "{source_path}" - "{output_path}"!')


next_nanogallery_id = 0


def process_line(line: str) -> str:
    if line.startswith("SPOILER_START"):
        line = line.removeprefix("SPOILER_START")
        if line.strip() == "":
            line = "Подробнее"
        return f"<details><summary>{line}</summary>"
    elif line.startswith("SPOILER_END"):
        return "</details>"
    if line.startswith("FLEX_WRAP_START"):
        return """<div class="hulvdan_flex hulvdan_flex_wrap" ''>"""
    elif line.startswith("FLEX_START"):
        return (
            """<div class="hulvdan_flex" style='display: flex; align-items="center"'>"""
        )
    elif line.startswith("FLEX_END"):
        return "</div>"

    while "BADGE(" in line:
        line1, line2 = line.split("BADGE(", 1)
        badge_content, line3 = line2.split(")", 1)
        badge = '<img alt="Static Badge" src="https://img.shields.io/badge/{}-%235479b0">'.format(
            urllib.parse.quote_plus(badge_content)
        )
        line = line1 + badge + line3

    global next_nanogallery_id

    line = line.replace(" -> ", " ➜ ").replace(r" \-\> ", " -> ")

    if line.startswith("IMAGES "):
        images = [i.strip() for i in line.removeprefix("IMAGES ").split() if i]
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

    if line.startswith("YOUTUBE_"):
        video_id = line.split("_", 1)[-1].strip()

        loop = 0
        if video_id.startswith("LOOP_"):
            video_id = video_id.split("_", 1)[-1].strip()
            loop = 1

        return f"""<p><iframe
            allowfullscreen="true"
            frameborder="0"
            width="480"
            rel=0
            loop={loop}
            style="max-width: 100%; aspect-ratio: 16 / 9;"
            src="https://www.youtube.com/embed/{video_id}"
            ></iframe></p>"""

    if line.startswith("PAGE "):
        page_number = line.strip().split(" ", 1)[-1].strip()
        return f'<p class="page-number">{page_number}</p>'

    return line


def write_file(*, template_data: str, markdown_contents: str, output_file_path):
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
