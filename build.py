import hashlib
import os
import re
import shutil
import urllib.parse
from datetime import datetime
from glob import glob
from pathlib import Path

import markdown2
from PIL import Image

HTML_TEMPLATE_FILE_PATH = Path("index_template.html")


def main():
    with open("style.css", "rb") as in_file:
        pretty_hash = hashlib.md5(in_file.read()).hexdigest()[:8]
        style_css_path = "/style-{}.css".format(pretty_hash)

    with open(HTML_TEMPLATE_FILE_PATH) as in_file:
        template_data = in_file.read().replace("{{ STYLE_CSS }}", style_css_path)

    for filepath in Path("docs/assets").iterdir():
        if "th__" in filepath.stem:
            continue

        th_filepath = filepath.parent / ("th__" + filepath.stem + ".jpg")
        if th_filepath.exists():
            continue

        img = Image.open(filepath)
        if filepath.name.endswith(".gif"):
            mypalette = img.getpalette()
            img.putpalette(mypalette)
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

    pairs = [
        (Path("pages") / i, Path("docs") / (i[:-2] + "html"))
        for i in glob("**/*.md", root_dir="pages", recursive=True)
    ]

    old_style_css = [i for i in glob("style-*.css", root_dir="docs", recursive=False)]
    for old_file in old_style_css:
        os.remove(Path("docs") / old_file)
    shutil.copyfile("style.css", Path("docs") / "style-{}.css".format(pretty_hash))

    for source_path, output_path in pairs:
        print(f'Generating from "{source_path}" - "{output_path}"...')

        with open(source_path, encoding="utf-8") as in_file:
            markdown_contents = in_file.read()

        markdown_contents = (
            markdown_contents.replace("/docs/index.html", "/")
            .replace("/docs/en.html", "/en")
            .replace("docs/assets/", "assets/")
            .replace("{% include today %}", datetime.now().strftime("%Y-%m-%d"))
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

    line = line.replace(" -> ", " ⇒ ")

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

    return line


def write_file(*, template_data: str, markdown_contents: str, output_file_path):
    markdown_contents = "\n".join(
        process_line(line) for line in markdown_contents.split("\n")
    )

    content = markdown2.markdown(
        markdown_contents.replace(" - ", " — "), extras=["markdown-in-html"]
    )
    rendered_html = template_data.format(content=content)

    with open(output_file_path, "w", encoding="utf-8") as out_file:
        out_file.write(rendered_html)


if __name__ == "__main__":
    main()
