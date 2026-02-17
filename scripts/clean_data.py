"""
TherapistIndex — Data Cleaning Pipeline
Phase 2: Takes raw OutScraper CSV exports and produces cleaned, deduplicated data.

Usage:
    python scripts/clean_data.py --input data/raw/ --output data/cleaned/
    python scripts/clean_data.py --input data/raw/outscraper_dc_therapist.csv --output data/cleaned/
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import requests

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    setup_logging,
    load_filter_keywords,
    standardize_phone,
    standardize_state,
    standardize_address,
    is_valid_url,
    normalize_url,
    guess_license_type,
    is_group_practice,
)

logger = setup_logging("clean_data")


# --- OutScraper column mapping ---
# OutScraper exports have varying column names; map them to our standard names
COLUMN_MAP = {
    "name": "therapist_name",
    "full_address": "address",
    "street": "street",
    "city": "city",
    "state": "state",
    "zip_code": "zip_code",
    "country_code": "country_code",
    "phone": "phone",
    "site": "website",
    "rating": "google_rating",
    "reviews": "google_review_count",
    "category": "category",
    "working_hours": "working_hours",
    "latitude": "latitude",
    "longitude": "longitude",
    "place_id": "place_id",
    "google_id": "google_id",
    "status": "status",
    # Common alternate names from OutScraper
    "reviews_count": "google_review_count",
    "review_count": "google_review_count",
    "website": "website",
    "address": "address",
    "postal_code": "zip_code",
    "zipcode": "zip_code",
}


def load_raw_csvs(input_path: str) -> pd.DataFrame:
    """Load one or more raw CSV files from OutScraper."""
    path = Path(input_path)
    frames = []

    if path.is_file() and path.suffix == ".csv":
        logger.info(f"Loading single file: {path}")
        df = pd.read_csv(path, dtype=str)
        df["_source_file"] = path.name
        frames.append(df)
    elif path.is_dir():
        csv_files = sorted(path.glob("*.csv"))
        if not csv_files:
            logger.error(f"No CSV files found in {path}")
            sys.exit(1)
        for csv_file in csv_files:
            logger.info(f"Loading: {csv_file.name}")
            df = pd.read_csv(csv_file, dtype=str)
            df["_source_file"] = csv_file.name
            frames.append(df)
    else:
        logger.error(f"Input path not found: {input_path}")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(combined)} total raw records from {len(frames)} file(s)")
    return combined


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to standard names using the column map."""
    # Lowercase all columns first
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rename = {}
    for old_name, new_name in COLUMN_MAP.items():
        if old_name in df.columns:
            rename[old_name] = new_name
    df = df.rename(columns=rename)
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicates based on:
    1. Exact name + address match
    2. Exact name + phone match
    3. Same place_id (Google Maps ID)
    """
    before = len(df)

    # Normalize for comparison
    df["_name_key"] = df["therapist_name"].str.lower().str.strip()
    df["_addr_key"] = df.get("address", pd.Series(dtype=str)).fillna("").str.lower().str.strip()
    df["_phone_key"] = df.get("phone", pd.Series(dtype=str)).fillna("").str.replace(r"\D", "", regex=True)

    # Dedupe by place_id first (most reliable)
    if "place_id" in df.columns:
        df = df.drop_duplicates(subset=["place_id"], keep="first")

    # Then by name + address
    df = df.drop_duplicates(subset=["_name_key", "_addr_key"], keep="first")

    # Then by name + phone (if phone exists)
    mask = df["_phone_key"].str.len() >= 10
    dupes = df[mask].duplicated(subset=["_name_key", "_phone_key"], keep="first")
    df = df[~(mask & dupes)]

    # Clean up temp columns
    df = df.drop(columns=["_name_key", "_addr_key", "_phone_key"])

    after = len(df)
    logger.info(f"Deduplication: {before} -> {after} ({before - after} duplicates removed)")
    return df.reset_index(drop=True)


def filter_non_therapists(df: pd.DataFrame) -> pd.DataFrame:
    """Remove results that are not mental health therapists."""
    keywords = load_filter_keywords()
    before = len(df)

    name_col = df["therapist_name"].fillna("").str.lower()
    cat_col = df.get("category", pd.Series("", index=df.index)).fillna("").str.lower()

    # Build exclusion mask from name
    name_exclude = pd.Series(False, index=df.index)
    for keyword in keywords["exclude_name_contains"]:
        name_exclude |= name_col.str.contains(keyword.lower(), na=False)

    # Build exclusion mask from category
    cat_exclude = pd.Series(False, index=df.index)
    for keyword in keywords["exclude_category_contains"]:
        cat_exclude |= cat_col.str.contains(keyword.lower(), na=False)

    # Build inclusion mask — if category matches a therapy type, keep it
    # even if name triggered a partial match
    cat_include = pd.Series(False, index=df.index)
    for keyword in keywords["include_category_contains"]:
        cat_include |= cat_col.str.contains(keyword.lower(), na=False)

    # Remove if name excludes AND category doesn't explicitly include
    exclude_mask = (name_exclude | cat_exclude) & ~cat_include
    df = df[~exclude_mask]

    after = len(df)
    logger.info(f"Non-therapist filter: {before} -> {after} ({before - after} removed)")
    return df.reset_index(drop=True)


def remove_closed(df: pd.DataFrame) -> pd.DataFrame:
    """Remove permanently closed businesses."""
    keywords = load_filter_keywords()
    before = len(df)

    status_col = df.get("status", pd.Series("", index=df.index)).fillna("").str.lower()
    name_col = df["therapist_name"].fillna("").str.lower()

    closed_mask = pd.Series(False, index=df.index)
    for indicator in keywords["exclude_permanently_closed_indicators"]:
        closed_mask |= status_col.str.contains(indicator.lower(), na=False)
        closed_mask |= name_col.str.contains(indicator.lower(), na=False)

    df = df[~closed_mask]
    after = len(df)
    logger.info(f"Closed business filter: {before} -> {after} ({before - after} removed)")
    return df.reset_index(drop=True)


def standardize_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Apply formatting standards to all fields."""
    # Phone
    if "phone" in df.columns:
        df["phone"] = df["phone"].apply(standardize_phone)

    # State
    if "state" in df.columns:
        df["state"] = df["state"].apply(standardize_state)

    # Address
    if "address" in df.columns:
        df["address"] = df["address"].apply(standardize_address)

    # Website
    if "website" in df.columns:
        df["website"] = df["website"].apply(normalize_url)
        # Remove invalid URLs
        valid_mask = df["website"].apply(lambda x: is_valid_url(x) if x else True)
        invalid_count = (~valid_mask & df["website"].astype(bool)).sum()
        if invalid_count > 0:
            logger.info(f"Cleared {invalid_count} invalid URLs")
        df.loc[~valid_mask, "website"] = ""

    # Ratings — ensure numeric
    if "google_rating" in df.columns:
        df["google_rating"] = pd.to_numeric(df["google_rating"], errors="coerce")
    if "google_review_count" in df.columns:
        df["google_review_count"] = pd.to_numeric(df["google_review_count"], errors="coerce").fillna(0).astype(int)

    # Zip code — ensure 5 digits
    if "zip_code" in df.columns:
        df["zip_code"] = df["zip_code"].fillna("").astype(str).str.extract(r"(\d{5})", expand=False).fillna("")

    return df


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed fields: license_type guess, group practice flag, etc."""
    category_col = df.get("category", pd.Series("", index=df.index)).fillna("")

    # Guess license type from name/category
    df["license_type"] = df.apply(
        lambda row: guess_license_type(
            row.get("therapist_name", ""),
            category_col.get(row.name, ""),
        ),
        axis=1,
    )

    # Flag group practices
    df["is_group_practice"] = df["therapist_name"].apply(is_group_practice)

    # Set data pipeline fields
    df["data_source"] = "outscraper"
    df["enrichment_status"] = "cleaned"
    df["last_verified_date"] = ""

    return df


def validate_urls_live(df: pd.DataFrame, timeout: float = 5.0, sample_size: int = 0) -> pd.DataFrame:
    """
    Optionally check if websites are reachable.
    Set sample_size > 0 to only check a sample (for speed).
    Set sample_size = 0 to skip live validation.
    """
    if sample_size == 0:
        logger.info("Skipping live URL validation (use --validate-urls N to enable)")
        return df

    urls_to_check = df[df["website"].astype(bool)]
    if sample_size > 0 and len(urls_to_check) > sample_size:
        urls_to_check = urls_to_check.sample(n=sample_size, random_state=42)

    logger.info(f"Checking {len(urls_to_check)} URLs for reachability...")
    dead_indices = []
    for idx, row in urls_to_check.iterrows():
        try:
            resp = requests.head(row["website"], timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                dead_indices.append(idx)
        except (requests.RequestException, Exception):
            dead_indices.append(idx)

    if dead_indices:
        logger.info(f"Found {len(dead_indices)} unreachable URLs — clearing them")
        df.loc[dead_indices, "website"] = ""

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print a summary of the cleaned dataset."""
    logger.info("=" * 60)
    logger.info("CLEANING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total records: {len(df)}")

    if "state" in df.columns:
        state_counts = df["state"].value_counts()
        logger.info(f"Records by state:")
        for state, count in state_counts.items():
            if state:
                logger.info(f"  {state}: {count}")

    if "license_type" in df.columns:
        lt_counts = df["license_type"].value_counts()
        logger.info(f"License types detected:")
        for lt, count in lt_counts.items():
            label = lt if lt else "(unknown)"
            logger.info(f"  {label}: {count}")

    has_phone = (df.get("phone", pd.Series(dtype=str)).fillna("").astype(bool)).sum()
    has_website = (df.get("website", pd.Series(dtype=str)).fillna("").astype(bool)).sum()
    has_rating = (df.get("google_rating", pd.Series(dtype=float)).notna()).sum()
    group_count = df.get("is_group_practice", pd.Series(dtype=bool)).sum()

    logger.info(f"Has phone: {has_phone} ({has_phone/len(df)*100:.1f}%)")
    logger.info(f"Has website: {has_website} ({has_website/len(df)*100:.1f}%)")
    logger.info(f"Has rating: {has_rating} ({has_rating/len(df)*100:.1f}%)")
    logger.info(f"Group practices: {group_count}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="TherapistIndex Data Cleaning Pipeline (Phase 2)"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to raw CSV file or directory of CSVs from OutScraper",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for cleaned CSV",
    )
    parser.add_argument(
        "--validate-urls",
        type=int,
        default=0,
        metavar="N",
        help="Check N random URLs for reachability (0 = skip, slow for large N)",
    )
    parser.add_argument(
        "--output-filename",
        default="therapists_cleaned.csv",
        help="Name of the output CSV file (default: therapists_cleaned.csv)",
    )
    args = parser.parse_args()

    # Load raw data
    df = load_raw_csvs(args.input)

    # Normalize column names
    df = normalize_columns(df)

    # Ensure required column exists
    if "therapist_name" not in df.columns:
        logger.error("No 'name' or 'therapist_name' column found in CSV. Check your OutScraper export format.")
        sys.exit(1)

    # Step 1: Remove closed businesses
    df = remove_closed(df)

    # Step 2: Filter non-therapists
    df = filter_non_therapists(df)

    # Step 3: Remove duplicates
    df = remove_duplicates(df)

    # Step 4: Standardize fields
    df = standardize_fields(df)

    # Step 5: Live URL validation (optional)
    df = validate_urls_live(df, sample_size=args.validate_urls)

    # Step 6: Add derived fields
    df = add_derived_fields(df)

    # Print summary
    print_summary(df)

    # Write output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.output_filename
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Cleaned data written to: {output_path}")
    logger.info(f"Ready for enrichment pipeline (scripts/enrich_data.py)")


if __name__ == "__main__":
    main()
