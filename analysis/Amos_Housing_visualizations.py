"""Create five neighborhood visualizations as scalable SVG images.

All plots use the cleaned Ames dataset and neighborhood summaries. No third-
party packages are required. Run with: python Amos_Housing_visualizations.py
"""

import csv
import html
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


OUT_DIR = Path(__file__).resolve().parent
DATA_PATH = OUT_DIR / "Amos_Housing_data_cleaned.csv"


def read_summary():
    groups = defaultdict(list)
    with DATA_PATH.open(newline="", encoding="utf-8") as data_file:
        reader = csv.DictReader(data_file)
        required = {"Neighborhood", "SalePrice", "Year Built", "Lot Area", "Overall Qual"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Required fields not found: {sorted(missing)}")
        for row in reader:
            groups[row["Neighborhood"]].append({
                "SalePrice": int(row["SalePrice"]),
                "Year Built": int(row["Year Built"]),
                "Lot Area": int(row["Lot Area"]),
                "Overall Qual": int(row["Overall Qual"]),
            })

    result = []
    for neighborhood, homes in groups.items():
        result.append({
            "Neighborhood": neighborhood,
            "Count": len(homes),
            "Median Price": median(home["SalePrice"] for home in homes),
            "Average Year": mean(home["Year Built"] for home in homes),
            "Average Lot": mean(home["Lot Area"] for home in homes),
            "Average Quality": mean(home["Overall Qual"] for home in homes),
        })
    return sorted(result, key=lambda row: row["Median Price"], reverse=True)


def esc(value):
    return html.escape(str(value))


def svg_start(width, height, title, subtitle):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="60" y="42" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#17324d">{esc(title)}</text>',
        f'<text x="60" y="68" font-family="Arial, sans-serif" font-size="14" fill="#526779">{esc(subtitle)}</text>',
    ]


def save_svg(name, elements):
    path = OUT_DIR / name
    path.write_text("\n".join(elements + ["</svg>"]), encoding="utf-8")
    print(f"Saved {path}")


def horizontal_dot_plot(rows):
    width, height = 1080, 1050
    left, right, top, bottom = 210, 45, 110, 80
    plot_width = width - left - right
    plot_height = height - top - bottom
    low, high = 0, 350000
    x = lambda value: left + (value - low) / (high - low) * plot_width
    gap = plot_height / len(rows)
    svg = svg_start(width, height, "Typical sale price by neighborhood", "Median sale price; sales count shown beside each neighborhood")
    for tick in range(0, 350001, 50000):
        tx = x(tick)
        svg.append(f'<line x1="{tx:.1f}" y1="{top}" x2="{tx:.1f}" y2="{height-bottom}" stroke="#dce5eb"/>')
        svg.append(f'<text x="{tx:.1f}" y="{height-bottom+27}" text-anchor="middle" font-family="Arial" font-size="12" fill="#526779">${tick//1000}k</text>')
    for index, row in enumerate(rows):
        cy = top + (index + 0.5) * gap
        svg.append(f'<text x="{left-14}" y="{cy+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#223b4c">{esc(row["Neighborhood"])} (n={row["Count"]})</text>')
        svg.append(f'<line x1="{left}" y1="{cy:.1f}" x2="{x(row["Median Price"]):.1f}" y2="{cy:.1f}" stroke="#bfd0da" stroke-width="2"/>')
        svg.append(f'<circle cx="{x(row["Median Price"]):.1f}" cy="{cy:.1f}" r="6" fill="#147d92"/>')
    svg.append(f'<text x="{left+plot_width/2}" y="{height-20}" text-anchor="middle" font-family="Arial" font-size="14" fill="#223b4c">Neighborhood median sale price (USD)</text>')
    save_svg("Amos_Housing_visualization_1_price_dot_plot.svg", svg)


def scatter(rows, x_key, x_label, filename, title, x_min, x_max, x_ticks, formatter):
    width, height = 1200, 820
    left, right, top, bottom = 100, 230, 115, 95
    plot_width, plot_height = width-left-right, height-top-bottom
    y_min, y_max = 70000, 340000
    px = lambda value: left + (value-x_min)/(x_max-x_min)*plot_width
    py = lambda value: top + (y_max-value)/(y_max-y_min)*plot_height
    svg = svg_start(width, height, title, "Each point is a neighborhood; bubble size represents number of sales")
    for tick in range(75000, 340001, 25000):
        ty = py(tick)
        svg.append(f'<line x1="{left}" y1="{ty:.1f}" x2="{width-right}" y2="{ty:.1f}" stroke="#e0e7ec"/>')
        svg.append(f'<text x="{left-12}" y="{ty+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#526779">${tick//1000}k</text>')
    for tick in x_ticks:
        tx = px(tick)
        svg.append(f'<line x1="{tx:.1f}" y1="{top}" x2="{tx:.1f}" y2="{height-bottom}" stroke="#eef2f5"/>')
        svg.append(f'<text x="{tx:.1f}" y="{height-bottom+24}" text-anchor="middle" font-family="Arial" font-size="12" fill="#526779">{esc(formatter(tick))}</text>')
    svg.append(f'<text x="{left+plot_width/2}" y="{height-28}" text-anchor="middle" font-family="Arial" font-size="14" fill="#223b4c">{esc(x_label)}</text>')
    svg.append(f'<text transform="translate(25 {top+plot_height/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="14" fill="#223b4c">Neighborhood median sale price (USD)</text>')

    for index, row in enumerate(rows):
        cx, cy = px(row[x_key]), py(row["Median Price"])
        radius = 3 + math.sqrt(row["Count"]) * 0.65
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="#17849a" fill-opacity="0.68" stroke="#ffffff" stroke-width="1.5"><title>{esc(row["Neighborhood"])}: median ${row["Median Price"]:,.0f}; n={row["Count"]}</title></circle>')
        # Alternate label placement to reduce collisions around dense points.
        dx = 9 if index % 2 == 0 else -9
        anchor = "start" if dx > 0 else "end"
        dy = -9 if index % 3 else 13
        label = f'{row["Neighborhood"]} (n={row["Count"]})'
        svg.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anchor}" font-family="Arial" font-size="10.5" fill="#294455" stroke="#ffffff" stroke-width="3" paint-order="stroke">{esc(label)}</text>')

    # Bubble size key, placed in the right margin.
    key_x, key_y = width-right+35, top+70
    svg.append(f'<text x="{key_x}" y="{key_y}" font-family="Arial" font-size="12" font-weight="700" fill="#294455">Sales count</text>')
    for idx, count in enumerate((25, 100, 250)):
        radius = 3 + math.sqrt(count) * 0.65
        cy = key_y + 35 + idx * 55
        svg.append(f'<circle cx="{key_x+15}" cy="{cy}" r="{radius:.1f}" fill="#17849a" fill-opacity="0.68"/>')
        svg.append(f'<text x="{key_x+42}" y="{cy+4}" font-family="Arial" font-size="11" fill="#526779">{count} sales</text>')
    save_svg(filename, svg)


def average_ranks(values):
    ordered = sorted(enumerate(values), key=lambda pair: pair[1], reverse=True)
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        stop = start + 1
        while stop < len(ordered) and ordered[stop][1] == ordered[start][1]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for position in range(start, stop):
            result[ordered[position][0]] = rank
        start = stop
    return result


def rank_heatmap(rows):
    width, height = 1120, 1120
    label_width, top, row_height = 190, 125, 32
    col_width = 220
    columns = ["Median Price", "Average Year", "Average Lot", "Average Quality"]
    headers = ["Median price", "Year built", "Lot area", "Overall quality"]
    ranked_rows = sorted(rows, key=lambda item: item["Median Price"], reverse=True)
    ranks = {column: average_ranks([row[column] for row in rows]) for column in columns}
    row_pos = {row["Neighborhood"]: index for index, row in enumerate(rows)}
    svg = svg_start(width, height, "Neighborhood rank profile", "Rank 1 is highest within each measure; cell text shows rank")
    colors = ["#246c58", "#83b99e", "#e5efe9", "#f2d8b7", "#c7775b"]
    for column_index, header in enumerate(headers):
        x = label_width + column_index * col_width
        svg.append(f'<text x="{x+col_width/2}" y="{top-16}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="#294455">{esc(header)}</text>')
    for row_index, row in enumerate(ranked_rows):
        y = top + row_index * row_height
        bg = "#f6f8f9" if row_index % 2 == 0 else "#ffffff"
        svg.append(f'<rect x="0" y="{y}" width="{width}" height="{row_height}" fill="{bg}"/>')
        svg.append(f'<text x="{label_width-15}" y="{y+21}" text-anchor="end" font-family="Arial" font-size="12" fill="#294455">{esc(row["Neighborhood"])} (n={row["Count"]})</text>')
        original_index = row_pos[row["Neighborhood"]]
        for column_index, column in enumerate(columns):
            rank = ranks[column][original_index]
            bin_index = min(4, int((rank - 1) / max(1, len(rows) / 5)))
            x = label_width + column_index * col_width
            svg.append(f'<rect x="{x+4}" y="{y+3}" width="{col_width-8}" height="{row_height-6}" rx="4" fill="{colors[bin_index]}"/>')
            svg.append(f'<text x="{x+col_width/2}" y="{y+21}" text-anchor="middle" font-family="Arial" font-size="12" fill="#17324d">{rank:.0f}</text>')
    legend_y = top + len(ranked_rows)*row_height + 24
    svg.append(f'<text x="{label_width}" y="{legend_y}" font-family="Arial" font-size="11" fill="#526779">Higher rank</text>')
    for i, color in enumerate(colors):
        x = label_width + 95 + i * 45
        svg.append(f'<rect x="{x}" y="{legend_y-12}" width="38" height="16" fill="{color}" rx="3"/>')
    svg.append(f'<text x="{label_width+340}" y="{legend_y}" font-family="Arial" font-size="11" fill="#526779">Lower rank</text>')
    save_svg("Amos_Housing_visualization_5_rank_heatmap.svg", svg)


def main():
    rows = read_summary()
    horizontal_dot_plot(rows)
    scatter(
        rows, "Average Quality", "Neighborhood average overall quality (1–10)",
        "Amos_Housing_visualization_2_price_quality.svg",
        "Sale price and overall quality", 4, 9, [4, 5, 6, 7, 8, 9], lambda value: f"{value}",
    )
    scatter(
        rows, "Average Year", "Neighborhood average year built", 
        "Amos_Housing_visualization_3_price_year_built.svg",
        "Sale price and home vintage", 1910, 2015, [1920, 1940, 1960, 1980, 2000], lambda value: f"{value}",
    )
    scatter(
        rows, "Average Lot", "Neighborhood average lot area (sq. ft.)",
        "Amos_Housing_visualization_4_price_lot_area.svg",
        "Sale price and lot area", 0, 26000, [0, 5000, 10000, 15000, 20000, 25000], lambda value: f"{value//1000}k" if value else "0",
    )
    rank_heatmap(rows)
    print(f"Generated five visualizations from {sum(row['Count'] for row in rows):,} sales across {len(rows)} neighborhoods.")


if __name__ == "__main__":
    main()
