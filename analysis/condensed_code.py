"""Standalone Ames Housing workflow: clean, analyze, summarize, and plot.

Run from any directory with Python 3:
    python /path/to/analysis/condensed_code.py

Uses only Python's standard library. The source CSV is read but never changed.
Outputs are written to analysis/data and analysis/artifacts.
"""

import csv
import html
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


ANALYSIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANALYSIS_DIR.parent
DATA_DIR = ANALYSIS_DIR / "data"
ARTIFACTS_DIR = ANALYSIS_DIR / "artifacts"
SOURCE_PATH = ROOT_DIR / "AmesHousing-1.csv"
FULL_DATA_PATH = DATA_DIR / "Amos_Housing_data_cleaned.csv"
LIMITED_DATA_PATH = DATA_DIR / "Amos_Housing_data_cleaned_limited.csv"
ANALYSIS_FIELDS = ["Neighborhood", "SalePrice", "Year Built", "Lot Area", "Overall Qual"]

NUMERIC_COLUMNS = {
    "Order", "MS SubClass", "Lot Frontage", "Lot Area", "Overall Qual",
    "Overall Cond", "Year Built", "Year Remod/Add", "Mas Vnr Area",
    "BsmtFin SF 1", "BsmtFin SF 2", "Bsmt Unf SF", "Total Bsmt SF",
    "1st Flr SF", "2nd Flr SF", "Low Qual Fin SF", "Gr Liv Area",
    "Bsmt Full Bath", "Bsmt Half Bath", "Full Bath", "Half Bath",
    "Bedroom AbvGr", "Kitchen AbvGr", "TotRms AbvGrd", "Fireplaces",
    "Garage Yr Blt", "Garage Cars", "Garage Area", "Wood Deck SF",
    "Open Porch SF", "Enclosed Porch", "3Ssn Porch", "Screen Porch",
    "Pool Area", "Misc Val", "Mo Sold", "Yr Sold", "SalePrice",
}
ABSENCE_CATEGORIES = {
    "Alley", "Bsmt Qual", "Bsmt Cond", "Bsmt Exposure", "BsmtFin Type 1",
    "BsmtFin Type 2", "Fireplace Qu", "Garage Type", "Garage Finish",
    "Garage Qual", "Garage Cond", "Pool QC", "Fence", "Misc Feature",
}
BASEMENT_NUMERIC = {
    "BsmtFin SF 1", "BsmtFin SF 2", "Bsmt Unf SF", "Total Bsmt SF",
    "Bsmt Full Bath", "Bsmt Half Bath",
}


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def clean_data():
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Source dataset not found: {SOURCE_PATH}")
    with SOURCE_PATH.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames
        if not columns:
            raise ValueError("The source CSV has no header row.")
        rows = [
            {column: (row.get(column) or "").strip() for column in columns}
            for row in reader
        ]

    missing_columns = set(ANALYSIS_FIELDS) - set(columns)
    if missing_columns:
        raise ValueError(f"Required analysis columns are missing: {sorted(missing_columns)}")
    if len({tuple(row[column] for column in columns) for row in rows}) != len(rows):
        raise ValueError("Duplicate full rows found; review before removing records.")
    if "PID" in columns:
        pids = [row["PID"] for row in rows]
        if any(not value for value in pids) or len(set(pids)) != len(pids):
            raise ValueError("PID values are blank or duplicated; review before cleaning.")

    for row in rows:
        for column in ABSENCE_CATEGORIES:
            if row.get(column, "").upper() == "NA":
                row[column] = "None"

        no_basement = row.get("Bsmt Qual") == "None" or (
            not row.get("Bsmt Qual")
            and all(not row.get(column) for column in BASEMENT_NUMERIC)
        )
        if no_basement:
            for column in BASEMENT_NUMERIC:
                if not row.get(column):
                    row[column] = "0"
            for column in ("Bsmt Qual", "Bsmt Cond", "Bsmt Exposure", "BsmtFin Type 1", "BsmtFin Type 2"):
                if not row.get(column):
                    row[column] = "None"

        if row.get("Garage Type") == "None":
            for column in ("Garage Cars", "Garage Area"):
                if not row.get(column):
                    row[column] = "0"

    for row_number, row in enumerate(rows, start=2):
        for column in NUMERIC_COLUMNS.intersection(columns):
            if not row[column]:
                continue
            try:
                value = float(row[column])
            except ValueError as error:
                raise ValueError(f"Non-numeric {column} on source row {row_number}: {row[column]!r}") from error
            if not value.is_integer():
                raise ValueError(f"Unexpected non-integer {column} on source row {row_number}: {row[column]!r}")
            row[column] = str(int(value))

        if not row["Neighborhood"]:
            raise ValueError(f"Neighborhood is blank on source row {row_number}.")
        for column in ANALYSIS_FIELDS[1:]:
            if not row[column]:
                raise ValueError(f"{column} is blank on source row {row_number}.")
        if int(row["SalePrice"]) <= 0 or int(row["Lot Area"]) <= 0:
            raise ValueError(f"Nonpositive sale price or lot area on source row {row_number}.")
        if not 1 <= int(row["Overall Qual"]) <= 10:
            raise ValueError(f"Overall quality outside 1–10 on source row {row_number}.")
        if not 1800 <= int(row["Year Built"]) <= 2026:
            raise ValueError(f"Year built outside the expected range on source row {row_number}.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(FULL_DATA_PATH, columns, rows)
    write_csv(LIMITED_DATA_PATH, ANALYSIS_FIELDS,
              [{column: row[column] for column in ANALYSIS_FIELDS} for row in rows])
    print(f"Cleaned data: {len(rows):,} rows, {len(columns)} columns -> {FULL_DATA_PATH}")
    print(f"Limited data: {len(rows):,} rows, {len(ANALYSIS_FIELDS)} columns -> {LIMITED_DATA_PATH}")


def get_neighborhood_summary():
    groups = defaultdict(list)
    with FULL_DATA_PATH.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            groups[row["Neighborhood"]].append(row)
    summary = []
    for neighborhood, homes in groups.items():
        summary.append({
            "Neighborhood": neighborhood,
            "Count": len(homes),
            "Median Price": median(int(home["SalePrice"]) for home in homes),
            "Average Year": mean(int(home["Year Built"]) for home in homes),
            "Average Lot": mean(int(home["Lot Area"]) for home in homes),
            "Average Quality": mean(int(home["Overall Qual"]) for home in homes),
        })
    return sorted(summary, key=lambda row: row["Median Price"], reverse=True)


def average_ranks(values, descending=False):
    ordered = sorted(enumerate(values), key=lambda item: item[1], reverse=descending)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        stop = start + 1
        while stop < len(ordered) and ordered[stop][1] == ordered[start][1]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for position in range(start, stop):
            ranks[ordered[position][0]] = rank
        start = stop
    return ranks


def spearman(left, right):
    x, y = average_ranks(left), average_ranks(right)
    mx, my = mean(x), mean(y)
    numerator = sum((a-mx)*(b-my) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a-mx)**2 for a in x) * sum((b-my)**2 for b in y))
    return numerator / denominator if denominator else float("nan")


def print_analysis(summary):
    print(f"\nAnalysis: {sum(row['Count'] for row in summary):,} homes across {len(summary)} neighborhoods")
    print(f"{'Neighborhood':<12} {'N':>5} {'Median price':>14} {'Mean year':>11} {'Mean lot area':>15} {'Mean quality':>14}")
    for row in summary:
        print(f"{row['Neighborhood']:<12} {row['Count']:>5} ${row['Median Price']:>13,.0f} "
              f"{row['Average Year']:>11.1f} {row['Average Lot']:>15,.0f} {row['Average Quality']:>14.2f}")
    prices = [row["Median Price"] for row in summary]
    print("\nSpearman rank correlations across neighborhoods:")
    for key, label in (("Average Year", "Average year built"),
                       ("Average Lot", "Average lot area"),
                       ("Average Quality", "Average overall quality")):
        print(f"Median sale price vs. {label}: rho = {spearman(prices, [row[key] for row in summary]):.3f}")


def make_summary_table(summary):
    path = ARTIFACTS_DIR / "Amos_Housing_summary_table.svg"
    headers = ["Neighborhood", "Number of sales", "Median sale price", "Average year built",
               "Average lot area (sq. ft.)", "Average overall quality"]
    widths = [150, 170, 190, 180, 220, 220]
    row_height, title_height, header_height = 34, 72, 42
    width = sum(widths)
    height = title_height + header_height + row_height*len(summary) + 20
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="24" y="34" font-family="Arial" font-size="23" font-weight="700" fill="#17324d">Ames Housing by Neighborhood</text>',
           '<text x="24" y="57" font-family="Arial" font-size="13" fill="#506477">Ranked by median sale price · summary across 2,930 sales</text>']
    y = title_height
    svg.append(f'<rect x="0" y="{y}" width="{width}" height="{header_height}" fill="#244a68"/>')
    x = 0
    for header, cell_width in zip(headers, widths):
        svg.append(f'<text x="{x+12}" y="{y+26}" font-family="Arial" font-size="13" font-weight="700" fill="#ffffff">{html.escape(header)}</text>')
        x += cell_width
    y += header_height
    for index, row in enumerate(summary):
        bg = "#eef4f7" if index % 2 == 0 else "#ffffff"
        svg.append(f'<rect x="0" y="{y}" width="{width}" height="{row_height}" fill="{bg}"/>')
        cells = [row["Neighborhood"], f'{row["Count"]:,}', f'${row["Median Price"]:,.0f}',
                 f'{row["Average Year"]:.1f}', f'{row["Average Lot"]:,.0f}', f'{row["Average Quality"]:.1f}']
        x = 0
        for cell, cell_width in zip(cells, widths):
            svg.append(f'<text x="{x+12}" y="{y+22}" font-family="Arial" font-size="13" fill="#182b3a">{html.escape(cell)}</text>')
            x += cell_width
        svg.append(f'<line x1="0" y1="{y+row_height}" x2="{width}" y2="{y+row_height}" stroke="#d7e0e6"/>')
        y += row_height
    svg.append("</svg>")
    path.write_text("\n".join(svg), encoding="utf-8")
    print(f"\nSummary table image -> {path}")


def svg_start(width, height, title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<text x="60" y="42" font-family="Arial" font-size="24" font-weight="700" fill="#17324d">{html.escape(title)}</text>',
            f'<text x="60" y="68" font-family="Arial" font-size="14" fill="#526779">{html.escape(subtitle)}</text>']


def save_plot(filename, elements):
    path = ARTIFACTS_DIR / filename
    path.write_text("\n".join(elements + ["</svg>"]), encoding="utf-8")
    print(f"Visualization -> {path}")


def dot_plot(rows):
    width, height, left, right, top, bottom = 1080, 1050, 210, 45, 110, 80
    plot_width, plot_height = width-left-right, height-top-bottom
    x = lambda value: left + value/350000*plot_width
    gap = plot_height/len(rows)
    svg = svg_start(width, height, "Typical sale price by neighborhood", "Median sale price; sales count shown beside each neighborhood")
    for tick in range(0, 350001, 50000):
        tx = x(tick)
        svg.extend([f'<line x1="{tx:.1f}" y1="{top}" x2="{tx:.1f}" y2="{height-bottom}" stroke="#dce5eb"/>',
                    f'<text x="{tx:.1f}" y="{height-bottom+27}" text-anchor="middle" font-family="Arial" font-size="12" fill="#526779">${tick//1000}k</text>'])
    for index, row in enumerate(rows):
        cy = top+(index+0.5)*gap
        svg.append(f'<text x="{left-14}" y="{cy+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#223b4c">{html.escape(row["Neighborhood"])} (n={row["Count"]})</text>')
        svg.append(f'<line x1="{left}" y1="{cy:.1f}" x2="{x(row["Median Price"]):.1f}" y2="{cy:.1f}" stroke="#bfd0da" stroke-width="2"/>')
        svg.append(f'<circle cx="{x(row["Median Price"]):.1f}" cy="{cy:.1f}" r="6" fill="#147d92"/>')
    svg.append(f'<text x="{left+plot_width/2}" y="{height-20}" text-anchor="middle" font-family="Arial" font-size="14" fill="#223b4c">Neighborhood median sale price (USD)</text>')
    save_plot("Amos_Housing_visualization_1_price_dot_plot.svg", svg)


def scatter(rows, key, label, filename, title, xmin, xmax, ticks, formatter):
    width, height, left, right, top, bottom = 1200, 820, 100, 230, 115, 95
    plot_width, plot_height = width-left-right, height-top-bottom
    ymin, ymax = 70000, 340000
    px = lambda value: left+(value-xmin)/(xmax-xmin)*plot_width
    py = lambda value: top+(ymax-value)/(ymax-ymin)*plot_height
    svg = svg_start(width, height, title, "Each point is a neighborhood; bubble size represents number of sales")
    for tick in range(75000, 340001, 25000):
        ty = py(tick)
        svg.extend([f'<line x1="{left}" y1="{ty:.1f}" x2="{width-right}" y2="{ty:.1f}" stroke="#e0e7ec"/>',
                    f'<text x="{left-12}" y="{ty+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#526779">${tick//1000}k</text>'])
    for tick in ticks:
        tx = px(tick)
        svg.extend([f'<line x1="{tx:.1f}" y1="{top}" x2="{tx:.1f}" y2="{height-bottom}" stroke="#eef2f5"/>',
                    f'<text x="{tx:.1f}" y="{height-bottom+24}" text-anchor="middle" font-family="Arial" font-size="12" fill="#526779">{html.escape(formatter(tick))}</text>'])
    svg.append(f'<text x="{left+plot_width/2}" y="{height-28}" text-anchor="middle" font-family="Arial" font-size="14" fill="#223b4c">{html.escape(label)}</text>')
    svg.append(f'<text transform="translate(25 {top+plot_height/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="14" fill="#223b4c">Neighborhood median sale price (USD)</text>')
    for index, row in enumerate(rows):
        cx, cy = px(row[key]), py(row["Median Price"])
        radius = 3+math.sqrt(row["Count"])*0.65
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="#17849a" fill-opacity="0.68" stroke="#ffffff" stroke-width="1.5"><title>{html.escape(row["Neighborhood"])}: median ${row["Median Price"]:,.0f}; n={row["Count"]}</title></circle>')
        dx = 9 if index % 2 == 0 else -9
        anchor = "start" if dx > 0 else "end"
        dy = -9 if index % 3 else 13
        text = f'{row["Neighborhood"]} (n={row["Count"]})'
        svg.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" text-anchor="{anchor}" font-family="Arial" font-size="10.5" fill="#294455" stroke="#ffffff" stroke-width="3" paint-order="stroke">{html.escape(text)}</text>')
    key_x, key_y = width-right+35, top+70
    svg.append(f'<text x="{key_x}" y="{key_y}" font-family="Arial" font-size="12" font-weight="700" fill="#294455">Sales count</text>')
    for index, count in enumerate((25, 100, 250)):
        radius = 3+math.sqrt(count)*0.65
        cy = key_y+35+index*55
        svg.extend([f'<circle cx="{key_x+15}" cy="{cy}" r="{radius:.1f}" fill="#17849a" fill-opacity="0.68"/>',
                    f'<text x="{key_x+42}" y="{cy+4}" font-family="Arial" font-size="11" fill="#526779">{count} sales</text>'])
    save_plot(filename, svg)


def rank_heatmap(rows):
    width, height, label_width, top, row_height, col_width = 1120, 1120, 190, 125, 32, 220
    keys = ["Median Price", "Average Year", "Average Lot", "Average Quality"]
    headers = ["Median price", "Year built", "Lot area", "Overall quality"]
    rank_values = {key: average_ranks([row[key] for row in rows], descending=True) for key in keys}
    original_position = {row["Neighborhood"]: idx for idx, row in enumerate(rows)}
    svg = svg_start(width, height, "Neighborhood rank profile", "Rank 1 is highest within each measure; cell text shows rank")
    colors = ["#246c58", "#83b99e", "#e5efe9", "#f2d8b7", "#c7775b"]
    for col, header in enumerate(headers):
        x = label_width+col*col_width
        svg.append(f'<text x="{x+col_width/2}" y="{top-16}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="#294455">{html.escape(header)}</text>')
    for row_index, row in enumerate(rows):
        y = top+row_index*row_height
        bg = "#f6f8f9" if row_index % 2 == 0 else "#ffffff"
        svg.append(f'<rect x="0" y="{y}" width="{width}" height="{row_height}" fill="{bg}"/>')
        svg.append(f'<text x="{label_width-15}" y="{y+21}" text-anchor="end" font-family="Arial" font-size="12" fill="#294455">{html.escape(row["Neighborhood"])} (n={row["Count"]})</text>')
        idx = original_position[row["Neighborhood"]]
        for col, key in enumerate(keys):
            rank = rank_values[key][idx]
            bin_index = min(4, int((rank-1)/max(1, len(rows)/5)))
            x = label_width+col*col_width
            svg.extend([f'<rect x="{x+4}" y="{y+3}" width="{col_width-8}" height="{row_height-6}" rx="4" fill="{colors[bin_index]}"/>',
                        f'<text x="{x+col_width/2}" y="{y+21}" text-anchor="middle" font-family="Arial" font-size="12" fill="#17324d">{rank:.0f}</text>'])
    legend_y = top+len(rows)*row_height+24
    svg.append(f'<text x="{label_width}" y="{legend_y}" font-family="Arial" font-size="11" fill="#526779">Higher rank</text>')
    for index, color in enumerate(colors):
        x = label_width+95+index*45
        svg.append(f'<rect x="{x}" y="{legend_y-12}" width="38" height="16" fill="{color}" rx="3"/>')
    svg.append(f'<text x="{label_width+340}" y="{legend_y}" font-family="Arial" font-size="11" fill="#526779">Lower rank</text>')
    save_plot("Amos_Housing_visualization_5_rank_heatmap.svg", svg)


def make_visualizations(summary):
    dot_plot(summary)
    scatter(summary, "Average Quality", "Neighborhood average overall quality (1–10)",
            "Amos_Housing_visualization_2_price_quality.svg", "Sale price and overall quality",
            4, 9, [4, 5, 6, 7, 8, 9], str)
    scatter(summary, "Average Year", "Neighborhood average year built",
            "Amos_Housing_visualization_3_price_year_built.svg", "Sale price and home vintage",
            1910, 2015, [1920, 1940, 1960, 1980, 2000], str)
    scatter(summary, "Average Lot", "Neighborhood average lot area (sq. ft.)",
            "Amos_Housing_visualization_4_price_lot_area.svg", "Sale price and lot area",
            0, 26000, [0, 5000, 10000, 15000, 20000, 25000], lambda value: f"{value//1000}k" if value else "0")
    rank_heatmap(summary)


def main():
    clean_data()
    summary = get_neighborhood_summary()
    print_analysis(summary)
    make_summary_table(summary)
    make_visualizations(summary)
    print("\nCondensed workflow completed successfully.")


if __name__ == "__main__":
    main()
