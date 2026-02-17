"""
TherapistIndex — Data Enrichment Pipeline
Phase 3: Scrapes therapist websites using Crawl4AI to extract:
  - Insurance panels accepted
  - Pricing / sliding scale
  - Specializations
  - Telehealth availability
  - Accepting new patients
  - Education / credentials
  - Profile photo URL

Usage:
    python scripts/enrich_data.py --input data/cleaned/therapists_cleaned.csv --output data/enriched/
    python scripts/enrich_data.py --input data/cleaned/therapists_cleaned.csv --output data/enriched/ --limit 50
"""

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    setup_logging,
    load_insurance_lookup,
    load_specialization_lookup,
    load_approach_lookup,
    match_insurance,
    match_specializations,
    detect_accepting_patients,
    detect_telehealth,
    detect_sliding_scale,
    detect_telehealth_platform,
    extract_price_range,
)

logger = setup_logging("enrich_data")

# Enrichment fields we'll add to each row
ENRICHMENT_FIELDS = [
    "insurance_accepted",
    "sliding_scale",
    "price_range_min",
    "price_range_max",
    "specializations",
    "therapy_approaches",
    "telehealth",
    "telehealth_platform",
    "accepting_new_patients",
    "education",
    "languages",
    "profile_image_url",
    "bio_summary",
]


async def crawl_website(url: str, crawler) -> str | None:
    """
    Crawl a single therapist website and return the extracted text content.
    Returns None on failure.
    """
    try:
        result = await crawler.arun(url=url)
        if result.success:
            return result.markdown or result.extracted_content or ""
        else:
            logger.debug(f"Crawl failed for {url}: {result.error_message}")
            return None
    except Exception as e:
        logger.debug(f"Crawl error for {url}: {e}")
        return None


def extract_profile_image(html_content: str, url: str) -> str:
    """Try to find a profile/headshot image from the crawled content."""
    if not html_content:
        return ""
    # Common patterns for therapist profile images
    img_patterns = [
        r'<img[^>]+(?:class|id)=["\'][^"\']*(?:profile|headshot|photo|avatar|therapist|portrait)[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+(?:class|id)=["\'][^"\']*(?:profile|headshot|photo|avatar|therapist|portrait)[^"\']*["\']',
        r'<img[^>]+alt=["\'][^"\']*(?:photo|headshot|profile)[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in img_patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            img_url = match.group(1)
            if img_url.startswith("/"):
                # Relative URL — make absolute
                from urllib.parse import urlparse
                parsed = urlparse(url)
                img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
            return img_url
    return ""


def extract_education(text: str) -> str:
    """Extract education/credentials from text."""
    if not text:
        return ""
    # Look for education sections
    edu_patterns = [
        r"(?:education|credentials|degree|training|qualifications)[:\s]*([^\n]{10,200})",
        r"(?:earned|received|graduated|completed)\s+(?:a\s+|an\s+)?([^\n]{10,150})",
        r"((?:M\.?A\.?|M\.?S\.?|Ph\.?D\.?|Psy\.?D\.?|M\.?D\.?|Ed\.?D\.?|M\.?S\.?W\.?|B\.?A\.?|B\.?S\.?)\s+(?:in\s+)?[^\n,]{5,100})",
    ]
    findings = []
    text_lower = text.lower()
    for pattern in edu_patterns:
        matches = re.findall(pattern, text_lower if pattern.startswith("(?:education") else text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip().rstrip(".,;")
            if len(cleaned) > 10 and cleaned not in findings:
                findings.append(cleaned)
    return "; ".join(findings[:3]) if findings else ""


def extract_languages(text: str) -> list[str]:
    """Extract languages spoken from text."""
    if not text:
        return []
    language_map = {
        "english": "English",
        "spanish": "Spanish",
        "espanol": "Spanish",
        "español": "Spanish",
        "mandarin": "Mandarin",
        "chinese": "Mandarin",
        "korean": "Korean",
        "vietnamese": "Vietnamese",
        "french": "French",
        "arabic": "Arabic",
        "amharic": "Amharic",
        "asl": "ASL",
        "american sign language": "ASL",
        "sign language": "ASL",
        "portuguese": "Portuguese",
        "hindi": "Hindi",
        "urdu": "Urdu",
        "tagalog": "Tagalog",
        "farsi": "Farsi",
        "persian": "Farsi",
        "russian": "Russian",
        "japanese": "Japanese",
        "german": "German",
        "italian": "Italian",
        "haitian creole": "Haitian Creole",
        "creole": "Haitian Creole",
    }
    text_lower = text.lower()
    found = set()
    for keyword, canonical in language_map.items():
        if keyword in text_lower:
            found.add(canonical)
    return sorted(found)


def enrich_from_text(
    text: str,
    html: str,
    url: str,
    insurance_lookup: dict,
    spec_lookup: dict,
    approach_lookup: dict,
) -> dict:
    """
    Extract all enrichment fields from scraped text content.
    Returns a dict of enrichment values.
    """
    result = {}

    # Insurance
    insurances = match_insurance(text, insurance_lookup)
    result["insurance_accepted"] = ", ".join(insurances) if insurances else ""

    # Sliding scale
    result["sliding_scale"] = detect_sliding_scale(text)

    # Price range
    price_min, price_max = extract_price_range(text)
    result["price_range_min"] = price_min
    result["price_range_max"] = price_max

    # Specializations
    specs = match_specializations(text, spec_lookup)
    result["specializations"] = ", ".join(specs) if specs else ""

    # Therapy approaches
    approaches = match_specializations(text, approach_lookup)
    result["therapy_approaches"] = ", ".join(approaches) if approaches else ""

    # Telehealth
    result["telehealth"] = detect_telehealth(text)
    result["telehealth_platform"] = detect_telehealth_platform(text)

    # Accepting new patients
    result["accepting_new_patients"] = detect_accepting_patients(text)

    # Education
    result["education"] = extract_education(text)

    # Languages
    langs = extract_languages(text)
    result["languages"] = ", ".join(langs) if langs else ""

    # Profile image
    result["profile_image_url"] = extract_profile_image(html, url)

    # Bio summary (first 500 chars of meaningful text)
    bio_text = text.strip()[:500] if text else ""
    result["bio_summary"] = bio_text

    return result


async def process_batch(
    df: pd.DataFrame,
    start_idx: int,
    batch_size: int,
    insurance_lookup: dict,
    spec_lookup: dict,
    approach_lookup: dict,
    delay: float,
) -> list[dict]:
    """Process a batch of therapist websites concurrently."""
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        logger.error(
            "crawl4ai not installed. Run: pip install crawl4ai"
        )
        sys.exit(1)

    end_idx = min(start_idx + batch_size, len(df))
    batch = df.iloc[start_idx:end_idx]
    results = []

    async with AsyncWebCrawler(verbose=False) as crawler:
        for idx, row in batch.iterrows():
            url = row.get("website", "")
            name = row.get("therapist_name", "unknown")

            if not url:
                results.append({field: "" for field in ENRICHMENT_FIELDS})
                continue

            logger.info(f"  [{idx + 1}/{len(df)}] Crawling: {name} — {url}")

            text = await crawl_website(url, crawler)
            if text is None:
                results.append({field: "" for field in ENRICHMENT_FIELDS})
                logger.debug(f"  No content extracted for {url}")
            else:
                enriched = enrich_from_text(
                    text, text, url,
                    insurance_lookup, spec_lookup, approach_lookup,
                )
                results.append(enriched)

            # Be polite — delay between requests
            if delay > 0:
                await asyncio.sleep(delay)

    return results


def print_enrichment_summary(df: pd.DataFrame) -> None:
    """Print summary of enrichment results."""
    total = len(df)
    logger.info("=" * 60)
    logger.info("ENRICHMENT SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total records: {total}")

    for field in ENRICHMENT_FIELDS:
        if field in df.columns:
            non_empty = df[field].fillna("").astype(str).replace("", pd.NA).notna().sum()
            pct = non_empty / total * 100 if total > 0 else 0
            logger.info(f"  {field}: {non_empty} ({pct:.1f}%)")

    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="TherapistIndex Enrichment Pipeline (Phase 3) — Crawl4AI website scraper"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to cleaned CSV from Phase 2",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for enriched CSV",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of records to process (0 = all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of websites to crawl per batch (default: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between requests (default: 1.0)",
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=0,
        help="Resume processing from this row index",
    )
    parser.add_argument(
        "--output-filename",
        default="therapists_enriched.csv",
        help="Name of the output CSV file",
    )
    args = parser.parse_args()

    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    logger.info(f"Loading cleaned data from: {input_path}")
    df = pd.read_csv(input_path, dtype=str)
    logger.info(f"Loaded {len(df)} records")

    # Apply limit
    if args.limit > 0:
        df = df.head(args.limit)
        logger.info(f"Limited to {len(df)} records")

    # Initialize enrichment columns
    for field in ENRICHMENT_FIELDS:
        if field not in df.columns:
            df[field] = ""

    # Load lookups
    logger.info("Loading config lookups...")
    insurance_lookup = load_insurance_lookup()
    spec_lookup = load_specialization_lookup()
    approach_lookup = load_approach_lookup()

    # Count records with websites to crawl
    has_website = df["website"].fillna("").astype(bool).sum()
    logger.info(f"Records with websites to crawl: {has_website}/{len(df)}")

    # Process in batches
    start_time = time.time()
    start_idx = args.resume_from
    all_results = []

    # Pre-fill results for rows before resume point
    for i in range(start_idx):
        all_results.append({field: df.iloc[i].get(field, "") for field in ENRICHMENT_FIELDS})

    while start_idx < len(df):
        batch_end = min(start_idx + args.batch_size, len(df))
        logger.info(f"Processing batch: rows {start_idx}-{batch_end - 1}")

        batch_results = asyncio.run(
            process_batch(
                df, start_idx, args.batch_size,
                insurance_lookup, spec_lookup, approach_lookup,
                args.delay,
            )
        )
        all_results.extend(batch_results)
        start_idx += args.batch_size

        # Save checkpoint every 5 batches
        if (start_idx // args.batch_size) % 5 == 0:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            checkpoint_path = output_dir / "enrichment_checkpoint.csv"
            temp_df = df.iloc[:len(all_results)].copy()
            for field in ENRICHMENT_FIELDS:
                temp_df[field] = [r.get(field, "") for r in all_results]
            temp_df.to_csv(checkpoint_path, index=False, encoding="utf-8")
            logger.info(f"Checkpoint saved: {checkpoint_path} ({len(all_results)} rows)")

    # Apply enrichment results to dataframe
    for field in ENRICHMENT_FIELDS:
        df[field] = [r.get(field, "") for r in all_results[:len(df)]]

    # Update enrichment status
    df["enrichment_status"] = df.apply(
        lambda row: "enriched_full" if row.get("insurance_accepted") else
                    "enriched_basic" if any(row.get(f) for f in ["specializations", "telehealth", "accepting_new_patients"]) else
                    "cleaned",
        axis=1,
    )

    # Summary
    elapsed = time.time() - start_time
    logger.info(f"Enrichment completed in {elapsed:.1f} seconds")
    print_enrichment_summary(df)

    # Write output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.output_filename
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Enriched data written to: {output_path}")
    logger.info(f"Ready for GeoDirectory import (scripts/prepare_import.py)")

    # Clean up checkpoint
    checkpoint = output_dir / "enrichment_checkpoint.csv"
    if checkpoint.exists():
        checkpoint.unlink()
        logger.info("Checkpoint file removed")


if __name__ == "__main__":
    main()
