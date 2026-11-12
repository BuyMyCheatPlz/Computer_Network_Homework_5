"""Check cover fidelity and prepare full-size two-page review sheets."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from PIL import Image, ImageChops, ImageDraw
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
render_folder = DOCS / "verification/final-pages-v2"
images = sorted(render_folder.glob("page-*.png"))
pdf = PdfReader(ROOT / "局域网聊天室课程设计报告.pdf")
assert len(images) == len(pdf.pages)
results = []
for index in (1, 2):
    before = Image.open(DOCS / f"verification/template-final-scale/page-{index}.png").convert("RGB")
    after = Image.open(render_folder / f"page-{index:02}.png").convert("RGB")
    assert before.size == after.size
    box = ImageChops.difference(before, after).getbbox()
    assert box is None, f"Template page {index} has pixel changes: {box}"
    results.append(dict(page=index, pixel_identical=True))
source_hash = hashlib.sha256((ROOT / "课程设计报告书-模版(1).doc").read_bytes()).hexdigest()
assert source_hash.upper() == "CC21C4F54B5604BC3194D51542C3D285AE6986B418DA5CBF6C47650836620198"
with ZipFile(DOCS / "参考模板.docx") as source, ZipFile(ROOT / "局域网聊天室课程设计报告.docx") as final:
    a, b = (etree.fromstring(z.read("word/styles.xml")) for z in (source, final))
    assert all(etree.tostring(x, method="c14n") == etree.tostring(y, method="c14n") for x,y in zip(a,b))
    assert len(b) == len(a) + 1
evidence = dict(original_doc_sha256=source_hash, original_doc_unchanged=True,
                pages=results, original_style_definitions_unchanged=True, added_style="Title",
                final_report_pages=len(pdf.pages), rendered_pages=len(images))
(DOCS / "封面像素验证.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
sheets = DOCS / "verification/review-sheets"
sheets.mkdir(exist_ok=True)
for start in range(0, len(images), 2):
    pages = [Image.open(p).convert("RGB") for p in images[start:start+2]]
    width = sum(p.width for p in pages)
    height = max(p.height for p in pages) + 32
    sheet = Image.new("RGB", (width, height), "#dddfe4")
    draw = ImageDraw.Draw(sheet)
    offset = 0
    for number, page in enumerate(pages, start+1):
        draw.text((offset + 10, 8), f"PAGE {number}", fill="black")
        sheet.paste(page, (offset, 32))
        offset += page.width
    sheet.save(sheets / f"sheet-{start//2+1:02}.png")
print(json.dumps(evidence, ensure_ascii=False))
