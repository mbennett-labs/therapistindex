"""
TherapistIndex — GeoDirectory Import Preparation
Phase 5: Formats enriched data into CSV ready for GeoDirectory CSV Import.

GeoDirectory expects specific column names and value formats.
This script maps our enriched data to their expected schema.

Usage:
    python scripts/prepare_import.py --input data/enriched/therapists_enriched.csv --output data/import_ready/
    python scripts/prepare_import.py --input data/enriched/therapists_enriched.csv --output data/import_ready/ --batch-size 500
"""

import argparse
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import setup_logging

logger = setup_logging("prepare_import")

# GeoDirectory CSV Import column mapping
# Left = our column name, Right = GeoDirectory expected column name
GEODIR_COLUMN_MAP = {
    "therapist_name": "post_title",
    "practice_name": "geodir_practice_name",
    "address": "post_address",
    "street": "street",
    "city": "city",
    "state": "region",
    "zip_code": "zip",
    "country_code": "country",
    "phone": "geodir_contact_phone",
    "email": "geodir_email",
    "website": "geodir_website",
    "latitude": "post_latitude",
    "longitude": "post_longitude",
    "license_type": "geodir_license_type",
    "license_number": "geodir_license_number",
    "license_state": "geodir_license_state",
    "license_verified": "geodir_license_verified",
    "specializations": "geodir_specializations",
    "insurance_accepted": "geodir_insurance_accepted",
    "sliding_scale": "geodir_sliding_scale",
    "price_range_min": "geodir_price_range_min",
    "price_range_max": "geodir_price_range_max",
    "session_length": "geodir_session_length",
    "telehealth": "geodir_telehealth",
    "telehealth_platform": "geodir_telehealth_platform",
    "accepting_new_patients": "geodir_accepting_new_patients",
    "wait_time": "geodir_wait_time",
    "languages": "geodir_languages",
    "therapy_approaches": "geodir_therapy_approaches",
    "age_groups_served": "geodir_age_groups_served",
    "gender": "geodir_gender",
    "years_experience": "geodir_years_experience",
    "education": "geodir_education",
    "profile_image_url": "geodir_profile_image_url",
    "google_rating": "geodir_google_rating",
    "google_review_count": "geodir_google_review_count",
    "last_verified_date": "geodir_last_verified_date",
    "data_source": "geodir_data_source",
    "enrichment_status": "geodir_enrichment_status",
}

# GeoDirectory required columns that need default values
GEODIR_DEFAULTS = {
    "post_status": "publish",
    "post_type": "gd_place",
    "post_category": "Therapist",
    "country": "US",
}


def generate_slug(name: str, city: str, state: str) -> str:
    """Generate a URL slug like jane-doe-bethesda-md."""
    import re
    parts = []
    for part in [name, city, state]:
        if part and isinstance(part, str):
            # Lowercase, remove special chars, replace spaces with hyphens
            cleaned = re.sub(r"[^a-z0-9\s-]", "", part.lower().strip())
            cleaned = re.sub(r"\s+", "-", cleaned)
            cleaned = re.sub(r"-+", "-", cleaned).strip("-")
            if cleaned:
                parts.append(cleaned)
    return "-".join(parts)


def generate_description(row: pd.Series) -> str:
    """Generate a post description/excerpt for the listing."""
    parts = []

    name = row.get("therapist_name", "")
    city = row.get("city", "")
    state = row.get("state", "")
    license_type = row.get("license_type", "")
    specializations = row.get("specializations", "")
    insurance = row.get("insurance_accepted", "")
    telehealth = row.get("telehealth", "")

    if name:
        intro = name
        if license_type:
            intro += f" ({license_type})"
        location = f"{city}, {state}" if city and state else city or state
        if location:
            intro += f" in {location}"
        parts.append(intro + ".")

    if specializations:
        specs = specializations.split(", ")[:5]
        parts.append(f"Specializes in {', '.join(specs)}.")

    if insurance:
        ins_list = insurance.split(", ")[:3]
        remaining = len(insurance.split(", ")) - 3
        ins_text = ", ".join(ins_list)
        if remaining > 0:
            ins_text += f" and {remaining} more"
        parts.append(f"Accepts {ins_text}.")

    if telehealth and telehealth not in ("No", "Unknown", ""):
        parts.append("Telehealth available.")

    accepting = row.get("accepting_new_patients", "")
    if accepting == "Yes":
        parts.append("Currently accepting new patients.")

    return " ".join(parts)


def format_multiselect(value: str) -> str:
    """
    Format comma-separated values for GeoDirectory multiselect fields.
    GeoDirectory expects comma-separated values.
    """
    if not value or not isinstance(value, str):
        return ""
    items = [item.strip() for item in value.split(",") if item.strip()]
    return ", ".join(items)


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Transform enriched data into GeoDirectory import format."""
    out = pd.DataFrame()

    # Map columns
    for our_col, gd_col in GEODIR_COLUMN_MAP.items():
        if our_col in df.columns:
            out[gd_col] = df[our_col].fillna("")
        else:
            out[gd_col] = ""

    # Add required defaults
    for col, default in GEODIR_DEFAULTS.items():
        out[col] = default

    # Generate slugs for URLs
    out["post_slug"] = df.apply(
        lambda row: generate_slug(
            row.get("therapist_name", ""),
            row.get("city", ""),
            row.get("state", ""),
        ),
        axis=1,
    )

    # Generate descriptions
    out["post_content"] = df.apply(generate_description, axis=1)

    # Set verification date to today for all imported records
    today = date.today().isoformat()
    out["geodir_last_verified_date"] = out["geodir_last_verified_date"].replace("", today)

    # Default license_state to state if not set
    if "geodir_license_state" in out.columns:
        state_col = df.get("state", pd.Series("", index=df.index)).fillna("")
        mask = out["geodir_license_state"] == ""
        out.loc[mask, "geodir_license_state"] = state_col[mask]

    # Format multiselect fields
    multiselect_fields = [
        "geodir_specializations",
        "geodir_insurance_accepted",
        "geodir_languages",
        "geodir_therapy_approaches",
        "geodir_age_groups_served",
    ]
    for field in multiselect_fields:
        if field in out.columns:
            out[field] = out[field].apply(format_multiselect)

    # Ensure numeric fields
    for field in ["geodir_price_range_min", "geodir_price_range_max",
                   "geodir_google_rating", "geodir_google_review_count",
                   "geodir_years_experience", "post_latitude", "post_longitude"]:
        if field in out.columns:
            out[field] = pd.to_numeric(out[field], errors="coerce").fillna("")

    # Reorder columns — put key GeoDirectory columns first
    priority_cols = [
        "post_title", "post_slug", "post_status", "post_type", "post_category",
        "post_content", "post_address", "city", "region", "zip", "country",
        "post_latitude", "post_longitude",
        "geodir_contact_phone", "geodir_email", "geodir_website",
    ]
    other_cols = [c for c in out.columns if c not in priority_cols]
    out = out[priority_cols + other_cols]

    return out


def print_import_summary(df: pd.DataFrame) -> None:
    """Print summary of import-ready data."""
    logger.info("=" * 60)
    logger.info("GEODIRECTORY IMPORT SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total listings: {len(df)}")
    logger.info(f"Columns: {len(df.columns)}")

    if "region" in df.columns:
        by_state = df["region"].value_counts()
        logger.info("By state:")
        for state, count in by_state.items():
            if state:
                logger.info(f"  {state}: {count}")

    has_phone = (df["geodir_contact_phone"].fillna("").astype(bool)).sum()
    has_website = (df["geodir_website"].fillna("").astype(bool)).sum()
    has_insurance = (df["geodir_insurance_accepted"].fillna("").astype(bool)).sum()
    has_specs = (df["geodir_specializations"].fillna("").astype(bool)).sum()

    logger.info(f"Has phone: {has_phone}")
    logger.info(f"Has website: {has_website}")
    logger.info(f"Has insurance data: {has_insurance}")
    logger.info(f"Has specializations: {has_specs}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="TherapistIndex GeoDirectory Import Preparation (Phase 5)"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to enriched CSV from Phase 3",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for import-ready CSV(s)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Split into batches of this size for import (default: 500)",
    )
    parser.add_argument(
        "--output-filename",
        default="therapists_geodirectory_import.csv",
        help="Base name for the output CSV file(s)",
    )
    args = parser.parse_args()

    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    logger.info(f"Loading enriched data from: {input_path}")
    df = pd.read_csv(input_path, dtype=str)
    logger.info(f"Loaded {len(df)} records")

    # Transform to GeoDirectory format
    gd_df = prepare_dataframe(df)

    # Summary
    print_import_summary(gd_df)

    # Write output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(gd_df) <= args.batch_size:
        # Single file
        output_path = output_dir / args.output_filename
        gd_df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Import file written to: {output_path}")
    else:
        # Split into batches
        num_batches = math.ceil(len(gd_df) / args.batch_size)
        base_name = Path(args.output_filename).stem
        ext = Path(args.output_filename).suffix

        for i in range(num_batches):
            start = i * args.batch_size
            end = min(start + args.batch_size, len(gd_df))
            batch_df = gd_df.iloc[start:end]

            batch_filename = f"{base_name}_batch{i + 1}{ext}"
            batch_path = output_dir / batch_filename
            batch_df.to_csv(batch_path, index=False, encoding="utf-8")
            logger.info(f"Batch {i + 1}/{num_batches}: {batch_path} ({len(batch_df)} records)")

    logger.info("Import files ready! Upload via GeoDirectory > Import/Export in WP Admin.")
    logger.info("Recommended: Import one batch at a time to avoid server timeouts.")


if __name__ == "__main__":
    main()
