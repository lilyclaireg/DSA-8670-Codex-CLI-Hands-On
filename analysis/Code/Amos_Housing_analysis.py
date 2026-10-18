"""Neighborhood-level analysis of sale price and housing characteristics.

Uses the full cleaned dataset while selecting only the five fields in scope.
Requires only the Python standard library.
"""

import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


ANALYSIS_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ANALYSIS_DIR / "data" / "Amos_Housing_data_cleaned.csv"
FIELDS = ["Neighborhood", "SalePrice", "Year Built", "Lot Area", "Overall Qual"]


def average_ranks(values):
    """Return one-based average ranks, accounting for tied values."""
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(indexed):
        stop = start + 1
        while stop < len(indexed) and indexed[stop][1] == indexed[start][1]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for position in range(start, stop):
            ranks[indexed[position][0]] = rank
        start = stop
    return ranks


def spearman_correlation(left, right):
    """Calculate Spearman's rank correlation without third-party packages."""
    left_ranks = average_ranks(left)
    right_ranks = average_ranks(right)
    left_mean = mean(left_ranks)
    right_mean = mean(right_ranks)
    numerator = sum(
        (x - left_mean) * (y - right_mean)
        for x, y in zip(left_ranks, right_ranks)
    )
    left_ss = sum((x - left_mean) ** 2 for x in left_ranks)
    right_ss = sum((y - right_mean) ** 2 for y in right_ranks)
    denominator = math.sqrt(left_ss * right_ss)
    return numerator / denominator if denominator else float("nan")


def main():
    with DATA_PATH.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = set(FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Required fields not found: {sorted(missing)}")
        groups = defaultdict(list)
        for row in reader:
            groups[row["Neighborhood"]].append(
                {
                    "SalePrice": int(row["SalePrice"]),
                    "Year Built": int(row["Year Built"]),
                    "Lot Area": int(row["Lot Area"]),
                    "Overall Qual": int(row["Overall Qual"]),
                }
            )

    summary = []
    for neighborhood, homes in groups.items():
        summary.append(
            {
                "Neighborhood": neighborhood,
                "House Count": len(homes),
                "Median SalePrice": median(home["SalePrice"] for home in homes),
                "Average Year Built": mean(home["Year Built"] for home in homes),
                "Average Lot Area": mean(home["Lot Area"] for home in homes),
                "Average Overall Qual": mean(home["Overall Qual"] for home in homes),
            }
        )
    summary.sort(key=lambda row: row["Median SalePrice"], reverse=True)

    print(f"Homes analyzed: {sum(row['House Count'] for row in summary):,}")
    print(f"Neighborhoods analyzed: {len(summary)}")
    print("\nNeighborhood summary (ranked by median sale price):")
    print(
        f"{'Neighborhood':<12} {'N':>5} {'Median price':>14} "
        f"{'Mean year':>11} {'Mean lot area':>15} {'Mean quality':>14}"
    )
    for row in summary:
        print(
            f"{row['Neighborhood']:<12} {row['House Count']:>5} "
            f"${row['Median SalePrice']:>13,.0f} "
            f"{row['Average Year Built']:>11.1f} "
            f"{row['Average Lot Area']:>15,.0f} "
            f"{row['Average Overall Qual']:>14.2f}"
        )

    sale_prices = [row["Median SalePrice"] for row in summary]
    print("\nSpearman rank correlations across neighborhoods:")
    for field, label in (
        ("Average Year Built", "Average year built"),
        ("Average Lot Area", "Average lot area"),
        ("Average Overall Qual", "Average overall quality"),
    ):
        coefficient = spearman_correlation(
            sale_prices, [row[field] for row in summary]
        )
        print(f"Median sale price vs. {label}: rho = {coefficient:.3f}")


if __name__ == "__main__":
    main()
