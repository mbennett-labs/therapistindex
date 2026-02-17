"""
TherapistIndex — OutScraper Google Maps Data Pull
Phase 1: Pulls therapist listings from Google Maps via OutScraper API.

Usage:
    # Test pull — 100 results for therapists in DC
    python scripts/outscraper_pull.py --query "therapist" --location "Washington, DC" --limit 100

    # Full pull from config
    python scripts/outscraper_pull.py --from-config --limit 500

    # Single state
    python scripts/outscraper_pull.py --from-config --filter-location "Washington DC" --limit 500
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from outscraper import ApiClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import setup_logging, load_config, PROJECT_ROOT

logger = setup_logging("outscraper_pull")

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")


def get_client() -> ApiClient:
    """Initialize OutScraper API client from environment variable."""
    api_key = os.getenv("OUTSCRAPER_API_KEY")
    if not api_key:
        logger.error("OUTSCRAPER_API_KEY not found. Set it in .env or environment.")
        sys.exit(1)
    return ApiClient(api_key=api_key)


def slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def pull_google_maps(
    client: ApiClient,
    query: str,
    location: str,
    limit: int = 100,
    max_retries: int = 3,
) -> list[dict]:
    """
    Pull Google Maps results from OutScraper with retry logic.
    Returns list of result dicts.
    """
    search_query = f"{query}, {location}"
    logger.info(f"Querying OutScraper: \"{search_query}\" (limit={limit})")

    for attempt in range(1, max_retries + 1):
        try:
            results = client.google_maps_search(
                [search_query],
                limit=limit,
                language="en",
                region="US",
            )
            break
        except Exception as e:
            if attempt < max_retries:
                wait = 10 * attempt
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"All {max_retries} attempts failed for \"{search_query}\": {e}")
                return []

    # OutScraper returns a list of lists (one per query)
    if results and isinstance(results, list):
        if isinstance(results[0], list):
            records = results[0]
        else:
            records = results
    else:
        records = []

    logger.info(f"Received {len(records)} results for \"{search_query}\"")
    return records


def records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    """Convert OutScraper result dicts to a standardized DataFrame."""
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Rename API columns to our standardized names
    rename_map = {
        "address": "full_address",
        "postal_code": "zip_code",
        "website": "site",
        "business_status": "status",
        "subtypes": "subtypes",
        "photo": "photo_url",
        "description": "description",
        "state_code": "state_code",
    }
    rename = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Use subtypes (detailed) over category (single) when available
    if "subtypes" in df.columns:
        df["category"] = df["subtypes"]
        df = df.drop(columns=["subtypes"])
    # Use state_code (e.g. "DC") over state (e.g. "District Of Columbia")
    if "state_code" in df.columns:
        df["state"] = df["state_code"]
        df = df.drop(columns=["state_code"])

    # Select only the columns we want (that exist)
    keep_cols = [
        "name", "full_address", "street", "city", "state", "zip_code",
        "country_code", "phone", "site", "rating", "reviews", "category",
        "working_hours", "latitude", "longitude", "place_id", "google_id",
        "status", "photo_url", "description",
    ]
    existing = [c for c in keep_cols if c in df.columns]
    df = df[existing]

    return df


def pull_from_config(
    client: ApiClient,
    limit: int,
    filter_location: str | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Run all queries from outscraper_queries.json config.
    Returns dict of location_slug -> DataFrame.
    """
    config = load_config("outscraper_queries.json")
    queries = config["queries"]

    if filter_location:
        filter_lower = filter_location.lower()
        queries = [q for q in queries if filter_lower in q["location"].lower()]
        if not queries:
            logger.error(f"No queries match location filter: {filter_location}")
            sys.exit(1)

    # Sort by priority
    queries.sort(key=lambda q: q["priority"])

    # Group by location to combine results per state/region
    all_results: dict[str, list[dict]] = {}

    for q in queries:
        search_term = q["search_term"]
        location = q["location"]
        key = slugify(location)

        logger.info(f"[Priority {q['priority']}] \"{search_term}\" in {location}")
        records = pull_google_maps(client, search_term, location, limit=limit)

        if key not in all_results:
            all_results[key] = []
        all_results[key].extend(records)

        # Rate limit between queries — be generous to avoid API errors
        time.sleep(5)

    # Convert to DataFrames
    dataframes = {}
    for key, records in all_results.items():
        df = records_to_dataframe(records)
        if not df.empty:
            dataframes[key] = df
            logger.info(f"  {key}: {len(df)} total records")

    return dataframes


def main():
    parser = argparse.ArgumentParser(
        description="TherapistIndex OutScraper Data Pull (Phase 1)"
    )

    # Single query mode
    parser.add_argument("--query", "-q", help="Search query (e.g. 'therapist')")
    parser.add_argument("--location", "-l", help="Location (e.g. 'Washington, DC')")

    # Config mode
    parser.add_argument(
        "--from-config", action="store_true",
        help="Run all queries from config/outscraper_queries.json",
    )
    parser.add_argument(
        "--filter-location",
        help="Only run queries matching this location (used with --from-config)",
    )

    # Common options
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Max results per query (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "raw"),
        help="Output directory for CSVs",
    )

    args = parser.parse_args()

    # Validate args
    if not args.from_config and not (args.query and args.location):
        parser.error("Provide --query and --location, or use --from-config")

    client = get_client()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.from_config:
        dataframes = pull_from_config(client, args.limit, args.filter_location)
        for key, df in dataframes.items():
            output_path = output_dir / f"outscraper_{key}.csv"
            df.to_csv(output_path, index=False, encoding="utf-8")
            logger.info(f"Saved {len(df)} records to {output_path}")
    else:
        records = pull_google_maps(client, args.query, args.location, args.limit)
        df = records_to_dataframe(records)
        if df.empty:
            logger.error("No results returned. Check your query and API key.")
            sys.exit(1)

        slug = slugify(f"{args.query}_{args.location}")
        output_path = output_dir / f"outscraper_{slug}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} records to {output_path}")

    logger.info("Done! Run scripts/clean_data.py next to process the raw data.")


if __name__ == "__main__":
    main()
