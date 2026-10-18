"""Create a neighborhood summary table and an SVG image of the table."""

import csv
import html
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


ANALYSIS_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ANALYSIS_DIR / "data" / "Amos_Housing_data_cleaned.csv"
IMAGE_PATH = ANALYSIS_DIR / "artifacts" / "Amos_Housing_summary_table.svg"


def load_summary():
    groups = defaultdict(list)
    with DATA_PATH.open(newline="", encoding="utf-8") as data_file:
        reader = csv.DictReader(data_file)
        required = {"Neighborhood", "SalePrice", "Year Built", "Lot Area", "Overall Qual"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Required fields not found: {sorted(missing)}")
        for row in reader:
            groups[row["Neighborhood"]].append(row)

    summary = []
    for neighborhood, homes in groups.items():
        summary.append(
            {
                "Neighborhood": neighborhood,
                "Number of sales": len(homes),
                "Median sale price": median(int(home["SalePrice"]) for home in homes),
                "Average year built": mean(int(home["Year Built"]) for home in homes),
                "Average lot area": mean(int(home["Lot Area"]) for home in homes),
                "Average overall quality": mean(int(home["Overall Qual"]) for home in homes),
            }
        )
    return sorted(summary, key=lambda item: item["Median sale price"], reverse=True)


def format_row(item):
    return [
        item["Neighborhood"],
        f'{item["Number of sales"]:,}',
        f'${item["Median sale price"]:,.0f}',
        f'{item["Average year built"]:.1f}',
        f'{item["Average lot area"]:,.0f}',
        f'{item["Average overall quality"]:.1f}',
    ]


def create_svg(summary):
    headers = [
        "Neighborhood",
        "Number of sales",
        "Median sale price",
        "Average year built",
        "Average lot area (sq. ft.)",
        "Average overall quality",
    ]
    rows = [format_row(item) for item in summary]
    widths = [150, 170, 190, 180, 220, 220]
    table_width = sum(widths)
    row_height = 34
    title_height = 72
    header_height = 42
    height = title_height + header_height + row_height * len(rows) + 20
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{table_width}" height="{height}" viewBox="0 0 {table_width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="34" font-family="Arial, sans-serif" font-size="23" font-weight="700" fill="#17324d">Ames Housing by Neighborhood</text>',
        '<text x="24" y="57" font-family="Arial, sans-serif" font-size="13" fill="#506477">Ranked by median sale price · summary across 2,930 sales</text>',
    ]
    y = title_height
    svg.append(f'<rect x="0" y="{y}" width="{table_width}" height="{header_height}" fill="#244a68"/>')
    x = 0
    for header, width in zip(headers, widths):
        svg.append(
            f'<text x="{x + 12}" y="{y + 26}" font-family="Arial, sans-serif" '
            f'font-size="13" font-weight="700" fill="#ffffff">{html.escape(header)}</text>'
        )
        x += width
    y += header_height
    for row_index, row in enumerate(rows):
        fill = "#eef4f7" if row_index % 2 == 0 else "#ffffff"
        svg.append(f'<rect x="0" y="{y}" width="{table_width}" height="{row_height}" fill="{fill}"/>')
        x = 0
        for cell, width in zip(row, widths):
            svg.append(
                f'<text x="{x + 12}" y="{y + 22}" font-family="Arial, sans-serif" '
                f'font-size="13" fill="#182b3a">{html.escape(cell)}</text>'
            )
            x += width
        svg.append(f'<line x1="0" y1="{y + row_height}" x2="{table_width}" y2="{y + row_height}" stroke="#d7e0e6"/>')
        y += row_height
    svg.append("</svg>")
    IMAGE_PATH.write_text("\n".join(svg), encoding="utf-8")


def main():
    summary = load_summary()
    IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    create_svg(summary)
    print(" | ".join([
        "Neighborhood", "Sales", "Median sale price", "Avg. year built",
        "Avg. lot area", "Avg. overall quality",
    ]))
    for item in summary:
        print(" | ".join(format_row(item)))
    print(f"\nSaved table image: {IMAGE_PATH}")


if __name__ == "__main__":
    main()
