"""Build the self-contained final Ames Housing report PDF (standard library only)."""

import html
import math
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


ANALYSIS_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ANALYSIS_DIR / "data"
ARTIFACTS = ANALYSIS_DIR / "artifacts"
OUTPUT = ANALYSIS_DIR / "Final_Report.pdf"
PAGE_W, PAGE_H = 612.0, 792.0


def pdf_string(value):
    raw = str(value).encode("cp1252", errors="replace")
    escaped = raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return b"(" + escaped + b")"


def color(value, fallback=(0, 0, 0)):
    if not value or value in ("none", "transparent"):
        return fallback
    if value.startswith("#") and len(value) == 7:
        return tuple(int(value[i:i+2], 16) / 255 for i in (1, 3, 5))
    return {"white": (1, 1, 1), "black": (0, 0, 0)}.get(value.lower(), fallback)


class PDFPage:
    def __init__(self, number):
        self.number = number
        self.ops = []
        self.rect(0, 0, PAGE_W, PAGE_H, fill="#ffffff")

    def rect(self, x, y_top, width, height, fill="#ffffff", stroke=None, line_width=0.6):
        y = PAGE_H - y_top - height
        ops = ["q"]
        if fill:
            r, g, b = color(fill)
            ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        if stroke:
            r, g, b = color(stroke)
            ops.extend([f"{r:.3f} {g:.3f} {b:.3f} RG", f"{line_width:.2f} w"])
        ops.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re")
        ops.append("B" if fill and stroke else "f" if fill else "S")
        ops.append("Q")
        self.ops.append("\n".join(ops))

    def line(self, x1, y1_top, x2, y2_top, stroke="#cccccc", width=0.6):
        r, g, b = color(stroke)
        self.ops.append(
            f"q {r:.3f} {g:.3f} {b:.3f} RG {width:.2f} w "
            f"{x1:.2f} {PAGE_H-y1_top:.2f} m {x2:.2f} {PAGE_H-y2_top:.2f} l S Q"
        )

    def circle(self, cx, cy_top, radius, fill="#000000", stroke=None, width=0.5):
        cy = PAGE_H - cy_top
        k = radius * 0.5522847498
        ops = ["q"]
        if fill:
            r, g, b = color(fill)
            ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        if stroke:
            r, g, b = color(stroke)
            ops.extend([f"{r:.3f} {g:.3f} {b:.3f} RG", f"{width:.2f} w"])
        ops.append(
            f"{cx+radius:.2f} {cy:.2f} m "
            f"{cx+radius:.2f} {cy+k:.2f} {cx+k:.2f} {cy+radius:.2f} {cx:.2f} {cy+radius:.2f} c "
            f"{cx-k:.2f} {cy+radius:.2f} {cx-radius:.2f} {cy+k:.2f} {cx-radius:.2f} {cy:.2f} c "
            f"{cx-radius:.2f} {cy-k:.2f} {cx-k:.2f} {cy-radius:.2f} {cx:.2f} {cy-radius:.2f} c "
            f"{cx+k:.2f} {cy-radius:.2f} {cx+radius:.2f} {cy-k:.2f} {cx+radius:.2f} {cy:.2f} c"
        )
        ops.append("B" if fill and stroke else "f" if fill else "S")
        ops.append("Q")
        self.ops.append("\n".join(ops))

    def text(self, value, x, y_top, size=10, font="F1", fill="#182b3a", align="left", rotate=0):
        if value is None:
            return
        value = str(value)
        estimate = len(value) * size * (0.60 if font in ("F2", "F4") else 0.52)
        if align == "middle":
            x -= estimate / 2
        elif align == "end":
            x -= estimate
        r, g, b = color(fill)
        if rotate == 90:
            matrix = f"0 1 -1 0 {x:.2f} {PAGE_H-y_top:.2f} Tm"
        elif rotate == -90:
            matrix = f"0 -1 1 0 {x:.2f} {PAGE_H-y_top:.2f} Tm"
        else:
            matrix = f"1 0 0 1 {x:.2f} {PAGE_H-y_top:.2f} Tm"
        self.ops.append(
            f"BT /{font} {size:.2f} Tf {r:.3f} {g:.3f} {b:.3f} rg {matrix} "
            f"{pdf_string(value).decode('latin-1')} Tj ET"
        )

    def footer(self):
        self.line(48, 756, PAGE_W-48, 756, "#d8e1e8", 0.5)
        self.text("Ames Housing neighborhood analysis", 48, 773, 8, fill="#687b88")
        self.text(f"{self.number}", PAGE_W-48, 773, 8, fill="#687b88", align="end")


class PDFDocument:
    def __init__(self):
        self.pages = []

    def new_page(self):
        page = PDFPage(len(self.pages) + 1)
        self.pages.append(page)
        return page

    def save(self, path):
        objects = [None]

        def add_object(payload):
            objects.append(payload if isinstance(payload, bytes) else payload.encode("latin-1"))
            return len(objects) - 1

        catalog_id = add_object(b"")
        pages_id = add_object(b"")
        fonts = {
            "F1": add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"),
            "F2": add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"),
            "F3": add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"),
            "F4": add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>"),
        }
        page_ids = []
        for page in self.pages:
            stream = "\n".join(page.ops).encode("latin-1", errors="replace")
            content_id = add_object(
                b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
            )
            font_dictionary = " ".join(f"/{name} {ref} 0 R" for name, ref in fonts.items())
            page_id = add_object(
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
                f"/Resources << /Font << {font_dictionary} >> >> /Contents {content_id} 0 R >>"
            )
            page_ids.append(page_id)
        objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
        kids = " ".join(f"{ref} 0 R" for ref in page_ids)
        objects[pages_id] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode()

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for index, obj in enumerate(objects[1:], start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode())
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_offset = len(output)
        output.extend(f"xref\n0 {len(objects)}\n".encode())
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(
            f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode()
        )
        path.write_bytes(output)


def wrap_text(text, max_chars):
    words = text.split()
    lines, current = [], ""
    for word in words:
        if current and len(current) + len(word) + 1 > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def paragraph(page, text, x, y, width_chars=86, size=10.2, leading=14, fill="#263e4e", font="F1"):
    for line in wrap_text(text, width_chars):
        page.text(line, x, y, size, font=font, fill=fill)
        y += leading
    return y


def heading(page, text, y, section=None):
    page.text(text, 52, y, 18, font="F2", fill="#17324d")
    page.line(52, y+8, 560, y+8, "#9cb2c1", 0.8)
    if section:
        page.text(section.upper(), 560, 36, 8, font="F2", fill="#147d92", align="end")


def code_block(page, lines, x, y, width=508, font_size=8.1, leading=12):
    height = 15 + len(lines)*leading
    page.rect(x, y-12, width, height, fill="#f1f5f7", stroke="#d8e1e8", line_width=0.6)
    for index, line in enumerate(lines):
        page.text(line, x+10, y+index*leading, font_size, font="F3", fill="#203748")
    return y + len(lines)*leading + 12


def draw_svg(page, path, box_x, box_y, max_width, max_height):
    root = ET.parse(path).getroot()
    width = float(re.sub(r"[^0-9.]", "", root.attrib.get("width", "1000")))
    height = float(re.sub(r"[^0-9.]", "", root.attrib.get("height", "700")))
    scale = min(max_width/width, max_height/height)
    render_w, render_h = width*scale, height*scale
    x0, y0 = box_x + (max_width-render_w)/2, box_y + (max_height-render_h)/2

    def px(value):
        try:
            return float(re.sub(r"[^0-9.+-]", "", value))
        except (TypeError, ValueError):
            return 0.0

    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        attrs = element.attrib
        if tag == "rect":
            x, y, w, h = (px(attrs.get(key, "0")) for key in ("x", "y", "width", "height"))
            fill = attrs.get("fill", "#000000")
            stroke = attrs.get("stroke")
            page.rect(x0+x*scale, y0+y*scale, w*scale, h*scale,
                      fill=None if fill == "none" else fill,
                      stroke=stroke if stroke and stroke != "none" else None,
                      line_width=px(attrs.get("stroke-width", "1"))*scale)
        elif tag == "line":
            page.line(x0+px(attrs.get("x1", "0"))*scale,
                      y0+px(attrs.get("y1", "0"))*scale,
                      x0+px(attrs.get("x2", "0"))*scale,
                      y0+px(attrs.get("y2", "0"))*scale,
                      attrs.get("stroke", "#000000"), px(attrs.get("stroke-width", "1"))*scale)
        elif tag == "circle":
            cx, cy, radius = (px(attrs.get(key, "0")) for key in ("cx", "cy", "r"))
            fill, stroke = attrs.get("fill", "#000000"), attrs.get("stroke")
            page.circle(x0+cx*scale, y0+cy*scale, radius*scale,
                        fill=None if fill == "none" else fill,
                        stroke=stroke if stroke and stroke != "none" else None,
                        width=px(attrs.get("stroke-width", "1"))*scale)
        elif tag == "text":
            value = "".join(element.itertext()).strip()
            if not value:
                continue
            x, y = px(attrs.get("x", "0")), px(attrs.get("y", "0"))
            size = px(attrs.get("font-size", "12"))*scale*1.12
            weight = attrs.get("font-weight", "400")
            font = "F2" if weight in ("bold", "700", "600") else "F1"
            anchor = attrs.get("text-anchor", "start")
            transform = attrs.get("transform", "")
            rotation = 90 if "rotate(-90)" in transform else 0
            translation = re.search(r"translate\(([-0-9.]+)[ ,]+([-0-9.]+)\)", transform)
            if translation:
                x, y = float(translation.group(1)), float(translation.group(2))
            pdf_anchor = {"start": "left", "middle": "middle", "end": "end"}.get(anchor, "left")
            page.text(value, x0+x*scale, y0+y*scale, size, font=font,
                      fill=attrs.get("fill", "#000000"), align=pdf_anchor, rotate=rotation)


def artifact_page(document, title, description, file_name, source_note=None):
    page = document.new_page()
    page.text("FINAL REPORT  /  AMES HOUSING", 52, 35, 8, font="F2", fill="#147d92")
    page.text(title, 52, 75, 20, font="F2", fill="#17324d")
    y = paragraph(page, description, 52, 101, width_chars=92, size=9.4, leading=13)
    svg_path = ARTIFACTS / file_name
    draw_svg(page, svg_path, 48, max(y+5, 125), 516, 595-(max(y+5, 125)-125))
    if source_note:
        page.text(source_note, 52, 736, 8, fill="#607482")
    page.footer()
    return page


def build_report():
    document = PDFDocument()

    # Page 1: purpose and key results.
    page = document.new_page()
    page.rect(0, 0, PAGE_W, 200, fill="#17324d")
    page.text("DATA ANALYSIS REPORT", 52, 52, 9, font="F2", fill="#73d0d0")
    page.text("Ames Housing", 52, 105, 31, font="F2", fill="#ffffff")
    page.text("Neighborhood sale prices and property characteristics", 52, 137, 14, fill="#e8f0f4")
    page.text(f"Prepared {date.today().isoformat()}  |  Ames, Iowa home sales", 52, 168, 9, fill="#b8cbd7")
    page.text("THE QUESTION", 52, 240, 9, font="F2", fill="#147d92")
    y = paragraph(page,
        "How do sale prices vary across Ames neighborhoods, and are higher-priced neighborhoods also characterized by newer homes, larger lots, or higher overall quality?",
        52, 265, width_chars=83, size=14, leading=21, fill="#17324d", font="F2")
    page.text("KEY FINDINGS", 52, y+28, 9, font="F2", fill="#147d92")
    cards = [
        ("$319,000", "Highest neighborhood median\nStoneBr; 51 sales"),
        ("$88,250", "Lowest neighborhood median\nMeadowV; 37 sales"),
        ("0.877", "Price and quality rank correlation\nStrongest observed association"),
    ]
    card_y, card_w, gap = y+48, 158, 17
    for i, (number, label) in enumerate(cards):
        x = 52+i*(card_w+gap)
        page.rect(x, card_y, card_w, 92, fill="#eef4f7", stroke="#d8e1e8")
        page.text(number, x+12, card_y+31, 19, font="F2", fill="#147d92")
        for line_no, line in enumerate(label.split("\n")):
            page.text(line, x+12, card_y+53+line_no*13, 8.4, fill="#40596a")
    page.text("OVERALL ANSWER", 52, card_y+129, 9, font="F2", fill="#147d92")
    paragraph(page,
        "Yes. Higher-priced neighborhoods generally had higher average quality, newer homes, and larger lots. The pattern was clearest for quality; age and lot area were less consistent. These are neighborhood-level associations, not proof that a feature caused a home's sale price.",
        52, card_y+153, width_chars=91, size=10.5, leading=15)
    page.footer()

    # Page 2: dataset, cleaning, methods, and code excerpts.
    page = document.new_page()
    heading(page, "Data and method", 58, "Context")
    y = 92
    y = paragraph(page,
        "The source file, AmesHousing-1.csv, contains 2,930 home sales and 82 fields. Each record describes a sold home in Ames, Iowa. The analysis groups homes into 28 neighborhoods and focuses on sale price, neighborhood, year built, lot area, and overall quality.",
        52, y, width_chars=91)
    y += 8
    page.text("Cleaning decisions", 52, y, 12, font="F2", fill="#17324d")
    y += 20
    for item in [
        "The original CSV was preserved; no duplicate rows or property IDs were found.",
        "Whitespace was trimmed and numeric fields were checked and normalized.",
        "Source codes for absent features were standardized; structurally absent basement or garage measurements were set to zero only when absence was clear.",
        "Unknown measurements stayed blank. All 2,930 records had values for the five analysis fields, so none were excluded.",
    ]:
        page.text("-", 56, y, 10, font="F2", fill="#147d92")
        y = paragraph(page, item, 70, y, width_chars=83, size=9.2, leading=12)+4
    page.text("Measures and interpretation", 52, y+3, 12, font="F2", fill="#17324d")
    y += 26
    y = paragraph(page,
        "Median sale price is the middle sale price in a neighborhood, less affected by unusually high or low transactions than the mean. Average year built, lot area, and quality describe neighborhood characteristics. Spearman's rank correlation (rho) measures whether neighborhoods ranking higher on one measure tend to rank higher on another; it does not measure causation.",
        52, y, width_chars=91, size=9.3, leading=13)
    y += 6
    page.text("Code excerpts from the reproducible workflow", 52, y, 12, font="F2", fill="#17324d")
    y += 22
    y = code_block(page, [
        "for neighborhood, homes in groups.items():",
        "    median_price = median(int(h['SalePrice']) for h in homes)",
        "    avg_year = mean(int(h['Year Built']) for h in homes)",
        "    avg_lot = mean(int(h['Lot Area']) for h in homes)",
        "    avg_quality = mean(int(h['Overall Qual']) for h in homes)",
    ], 52, y, font_size=7.6, leading=11)
    page.text("Rank association is calculated across the 28 neighborhood summaries:", 52, y, 9, fill="#40596a")
    code_block(page, [
        "rho_quality = spearman(median_prices, average_quality)",
        "rho_year = spearman(median_prices, average_year_built)",
        "rho_lot = spearman(median_prices, average_lot_area)",
    ], 52, y+19, font_size=7.8, leading=12)
    page.footer()

    # Page 3: compact source data excerpt and caveats.
    page = document.new_page()
    heading(page, "Neighborhood data at a glance", 58, "Results")
    paragraph(page,
        "Below are the three highest- and lowest-median-price neighborhoods. The complete 28-neighborhood comparison follows in the summary table artifact.",
        52, 94, width_chars=91)
    headers = ["Neighborhood", "Sales", "Median price", "Avg. year", "Avg. lot area", "Avg. quality"]
    rows = [
        ["StoneBr", "51", "$319,000", "1999.4", "11,383", "8.37"],
        ["NridgHt", "166", "$317,750", "2005.6", "11,217", "8.28"],
        ["NoRidge", "71", "$302,000", "1995.4", "12,976", "7.93"],
        ["IDOTRR", "93", "$106,500", "1927.7", "8,826", "4.73"],
        ["BrDale", "30", "$106,000", "1971.8", "1,841", "5.73"],
        ["MeadowV", "37", "$88,250", "1972.2", "2,109", "4.38"],
    ]
    x_positions = [52, 162, 220, 329, 410, 510]
    y = 158
    page.rect(52, y-18, 508, 27, fill="#244a68")
    for x, header in zip(x_positions, headers):
        page.text(header, x+4, y, 7.6, font="F2", fill="#ffffff")
    for index, row in enumerate(rows):
        y += 29
        page.rect(52, y-18, 508, 27, fill="#eef4f7" if index % 2 == 0 else "#ffffff")
        for x, value in zip(x_positions, row):
            page.text(value, x+4, y, 8.2, fill="#203748")
    page.text("Neighborhood-level Spearman rank correlations", 52, y+57, 13, font="F2", fill="#17324d")
    corr_rows = [
        ("Average overall quality", "0.877", "Strongest positive alignment"),
        ("Average year built", "0.681", "Positive alignment"),
        ("Average lot area", "0.570", "Positive, less consistent alignment"),
    ]
    y += 82
    for label, value, meaning in corr_rows:
        page.text(label, 60, y, 9.5, fill="#203748")
        page.text(value, 305, y, 10, font="F2", fill="#147d92")
        page.text(meaning, 365, y, 9, fill="#40596a")
        y += 25
    page.rect(52, y+10, 508, 98, fill="#fff6e8", stroke="#e7d5b1")
    page.text("Reading the results carefully", 66, y+34, 10, font="F2", fill="#694c1c")
    paragraph(page,
        "A positive rho means neighborhoods with higher ranks on one measure tended to have higher ranks on the other. Neighborhood means can hide differences between individual homes. Landmrk has only 1 sale and GrnHill 2, so their neighborhood estimates are especially uncertain. The associations do not establish cause and effect.",
        66, y+53, width_chars=83, size=8.8, leading=12, fill="#5b4a2b")
    page.footer()

    # Artifact order: summary table, then visualizations 1 through 5.
    artifact_page(document, "Summary table", 
        "Neighborhood summaries sorted from highest to lowest median sale price. The table includes sales count and average year built, lot area, and overall quality.",
        "Amos_Housing_summary_table.svg", "Source: cleaned Ames housing dataset; 2,930 sales in 28 neighborhoods.")
    artifact_page(document, "Visualization 1 - median sale price",
        "The dot plot ranks neighborhoods by median sale price. The count beside each label shows how many sales contribute to that neighborhood summary.",
        "Amos_Housing_visualization_1_price_dot_plot.svg", "Median is the neighborhood midpoint sale price.")
    artifact_page(document, "Visualization 2 - price and overall quality",
        "Each bubble represents a neighborhood. Higher points indicate higher median prices; bubble size represents sales count. Quality has the strongest rank association with price (rho = 0.877).",
        "Amos_Housing_visualization_2_price_quality.svg", "Overall quality is averaged within each neighborhood.")
    artifact_page(document, "Visualization 3 - price and year built",
        "This chart compares median sale price with average year built. A later average year means the neighborhood's homes tend to be newer. The rank association is positive (rho = 0.681).",
        "Amos_Housing_visualization_3_price_year_built.svg", "Average year built is a neighborhood summary, not an individual home age estimate.")
    artifact_page(document, "Visualization 4 - price and lot area",
        "This chart compares median sale price with average lot area. The positive rank association is more moderate (rho = 0.570), and large average lots do not always correspond to the highest median prices.",
        "Amos_Housing_visualization_4_price_lot_area.svg", "Lot area is measured in square feet.")
    artifact_page(document, "Visualization 5 - neighborhood rank heatmap",
        "Each cell shows a neighborhood's rank for that measure; rank 1 is highest. Green cells indicate higher ranks and warmer colors indicate lower ranks. Rows are ordered by median sale price.",
        "Amos_Housing_visualization_5_rank_heatmap.svg", "Rank colors support comparison; the printed rank in each cell is the precise value.")

    # Final report section: approved narrative summary.
    page = document.new_page()
    heading(page, "Narrative summary", 58, "Conclusion")
    y = 100
    narrative = [
        "Typical sale prices differed widely across Ames neighborhoods. The highest median sale price was in StoneBr at $319,000, based on 51 sales. NridgHt was close behind at $317,750 across 166 sales, followed by NoRidge at $302,000 across 71 sales. At the other end, MeadowV had the lowest median at $88,250 across 37 sales.",
        "A median is the midpoint sale price: half the sales in that neighborhood were higher and half were lower. It helps describe a typical sale without being pulled as strongly by a few unusually expensive homes.",
        "Across neighborhoods, sale price tended to rise along with average overall quality, average year built, and average lot area. To measure these patterns, I used Spearman rank correlation. It compares how neighborhoods rank on two measures: a positive value means neighborhoods ranked higher on one measure also tended to rank higher on the other. The relationship was strongest for overall quality (rho = 0.877), followed by year built (rho = 0.681) and lot area (rho = 0.570). In plain terms, neighborhood median prices aligned most closely with average quality, and somewhat less consistently with newer homes and larger lots.",
        "These are neighborhood-level patterns in this dataset; they do not show that home age, lot size, or quality caused sale prices to be higher. Neighborhoods with very few sales, such as Landmrk (1 sale) and GrnHill (2 sales), should also be interpreted cautiously because their median prices and averages are based on limited observations.",
        "Overall, the answer is yes: higher-priced neighborhoods generally had newer homes, larger lots, and higher overall quality. The connection was clearest for quality; the relationships with home age and lot area were more moderate and had exceptions. These patterns describe how neighborhoods compared in this dataset, rather than predicting the price of an individual home.",
    ]
    for text in narrative:
        y = paragraph(page, text, 52, y, width_chars=91, size=10.2, leading=15)+12
    page.footer()

    document.save(OUTPUT)
    print(f"Created {OUTPUT} ({len(document.pages)} pages)")


if __name__ == "__main__":
    build_report()
