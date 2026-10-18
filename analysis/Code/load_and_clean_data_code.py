"""Load and clean AmesHousing-1.csv, then save full and analysis datasets.

Run from any directory with Python 3:
    python load_and_clean_data_code.py

Only the Python standard library is required. Missing feature labels that mean
the feature is absent are standardized to "None". Truly unknown measurements
remain blank. The source file is never modified.
"""

import csv
from pathlib import Path


ANALYSIS_DIR = Path(__file__).resolve().parent.parent
ROOT = ANALYSIS_DIR.parent
SOURCE = ROOT / "AmesHousing-1.csv"
OUTPUT_DIR = ANALYSIS_DIR / "data"
FULL_OUTPUT = OUTPUT_DIR / "Amos_Housing_data_cleaned.csv"
LIMITED_OUTPUT = OUTPUT_DIR / "Amos_Housing_data_cleaned_limited.csv"

ANALYSIS_COLUMNS = [
    "Neighborhood",
    "SalePrice",
    "Year Built",
    "Lot Area",
    "Overall Qual",
]

# Numeric fields in the Ames Housing data. Values are written as integer text
# in the CSV; blank values are retained unless structural absence is known.
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

# These fields use the source value "NA" to mean the feature is absent.
ABSENCE_CATEGORIES = {
    "Alley", "Bsmt Qual", "Bsmt Cond", "Bsmt Exposure", "BsmtFin Type 1",
    "BsmtFin Type 2", "Fireplace Qu", "Garage Type", "Garage Finish",
    "Garage Qual", "Garage Cond", "Pool QC", "Fence", "Misc Feature",
}

BASEMENT_NUMERIC = {
    "BsmtFin SF 1", "BsmtFin SF 2", "Bsmt Unf SF", "Total Bsmt SF",
    "Bsmt Full Bath", "Bsmt Half Bath",
}
GARAGE_NUMERIC = {"Garage Cars", "Garage Area"}


def clean_value(value):
    """Trim whitespace and turn whitespace-only cells into empty values."""
    return (value or "").strip()


def write_csv(path, fieldnames, records):
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Could not find source dataset: {SOURCE}")

    with SOURCE.open(newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("The source CSV has no header row.")
        records = [
            {column: clean_value(row.get(column)) for column in fieldnames}
            for row in reader
        ]

    missing_columns = set(ANALYSIS_COLUMNS) - set(fieldnames)
    if missing_columns:
        raise ValueError(f"Required analysis columns are missing: {missing_columns}")

    # Reject duplicate records or IDs instead of silently deleting observations.
    if len({tuple(row[column] for column in fieldnames) for row in records}) != len(records):
        raise ValueError("Duplicate full rows found; review before removing any records.")
    if "PID" in fieldnames:
        ids = [row["PID"] for row in records]
        if any(not value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("PID values are blank or duplicated; review before cleaning.")

    # Standardize explicit source codes for structural absence. Do not turn
    # unknown blanks into absence labels.
    for row in records:
        for column in ABSENCE_CATEGORIES:
            if row.get(column, "").upper() == "NA":
                row[column] = "None"

        # A fully unrecorded basement profile with blank area measurements is
        # treated as no basement. An explicit "None" basement quality also
        # indicates no basement. Otherwise numeric blanks remain unknown.
        no_basement = (
            row.get("Bsmt Qual") == "None"
            or (
                not row.get("Bsmt Qual")
                and all(not row.get(column) for column in BASEMENT_NUMERIC)
            )
        )
        if no_basement:
            for column in BASEMENT_NUMERIC:
                if not row.get(column):
                    row[column] = "0"
            for column in ("Bsmt Qual", "Bsmt Cond", "Bsmt Exposure", "BsmtFin Type 1", "BsmtFin Type 2"):
                if not row.get(column):
                    row[column] = "None"

        # Missing garage size/count is zero only when garage type explicitly
        # indicates there is no garage. Unknown garage records stay blank.
        if row.get("Garage Type") == "None":
            for column in GARAGE_NUMERIC:
                if not row.get(column):
                    row[column] = "0"

    # Validate numeric fields and normalize integral numeric representations.
    # Leave genuine blanks (for example, unknown Lot Frontage) as blanks.
    for row_number, row in enumerate(records, start=2):
        for column in NUMERIC_COLUMNS & set(fieldnames):
            value = row[column]
            if not value:
                continue
            try:
                numeric_value = float(value)
            except ValueError as error:
                raise ValueError(
                    f"Non-numeric value in {column!r} on CSV row {row_number}: {value!r}"
                ) from error
            if not numeric_value.is_integer():
                raise ValueError(
                    f"Unexpected non-integer value in {column!r} on CSV row {row_number}: {value!r}"
                )
            row[column] = str(int(numeric_value))

    # The five fields used by the analysis must be present and plausible.
    for row_number, row in enumerate(records, start=2):
        if not row["Neighborhood"]:
            raise ValueError(f"Neighborhood is blank on CSV row {row_number}.")
        for column in ANALYSIS_COLUMNS[1:]:
            if not row[column]:
                raise ValueError(f"{column} is blank on CSV row {row_number}.")
        if int(row["SalePrice"]) <= 0 or int(row["Lot Area"]) <= 0:
            raise ValueError(f"Nonpositive SalePrice or Lot Area on CSV row {row_number}.")
        if not 1 <= int(row["Overall Qual"]) <= 10:
            raise ValueError(f"Overall Qual outside 1–10 on CSV row {row_number}.")
        if not 1800 <= int(row["Year Built"]) <= 2026:
            raise ValueError(f"Year Built outside the expected range on CSV row {row_number}.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(FULL_OUTPUT, fieldnames, records)
    write_csv(
        LIMITED_OUTPUT,
        ANALYSIS_COLUMNS,
        [{column: row[column] for column in ANALYSIS_COLUMNS} for row in records],
    )
    print(f"Saved {len(records)} rows and {len(fieldnames)} columns to {FULL_OUTPUT}")
    print(f"Saved {len(records)} rows and {len(ANALYSIS_COLUMNS)} columns to {LIMITED_OUTPUT}")


if __name__ == "__main__":
    main()
