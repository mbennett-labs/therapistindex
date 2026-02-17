"""
TherapistIndex — License Verification Pipeline
Phase 4: Cross-references therapist names against state licensing board databases.

Licensing board sources:
  - DC: doh.dc.gov/service/license-verification
  - MD: health.maryland.gov/bopc (Board of Professional Counselors)
  - VA: dhp.virginia.gov/counseling

Usage:
    python scripts/verify_licenses.py --input data/enriched/therapists_enriched.csv --output data/enriched/
    python scripts/verify_licenses.py --input data/enriched/therapists_enriched.csv --output data/enriched/ --state DC --limit 50
"""

import argparse
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import setup_logging

logger = setup_logging("verify_licenses")

# Rate limiting defaults
REQUEST_DELAY = 2.0  # seconds between requests to each board
REQUEST_TIMEOUT = 15.0  # seconds


class LicenseVerifier:
    """Base class for state license verification."""

    def __init__(self, state: str, delay: float = REQUEST_DELAY):
        self.state = state
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TherapistIndex Directory Verification Bot/1.0"
        })

    def verify(self, name: str, license_type: str = "") -> dict:
        """
        Attempt to verify a therapist's license.
        Returns dict with: verified (bool), license_number, license_type, status.
        """
        raise NotImplementedError

    def _extract_name_parts(self, name: str) -> tuple[str, str]:
        """Split a name into (first, last), handling common patterns."""
        if not name:
            return "", ""
        # Remove credentials/titles
        name = re.sub(
            r",?\s*(LCSW|LPC|LMFT|PsyD|PhD|MD|LCPC|LCMFT|MA|MS|MSW|MEd|EdD|NCC|ACS|LICSW)[-\w]*",
            "", name, flags=re.IGNORECASE
        ).strip()
        # Remove business suffixes
        name = re.sub(
            r"\b(LLC|Inc|PLLC|PC|Associates|& Associates|Group|Center|Practice)\b",
            "", name, flags=re.IGNORECASE
        ).strip()
        # Remove Dr. prefix
        name = re.sub(r"^Dr\.?\s+", "", name, flags=re.IGNORECASE)

        parts = name.split()
        if len(parts) >= 2:
            return parts[0], parts[-1]
        elif len(parts) == 1:
            return "", parts[0]
        return "", ""


class DCVerifier(LicenseVerifier):
    """
    DC Department of Health license verification.
    Uses the DC DOH online lookup.
    """

    BASE_URL = "https://doh.dc.gov/service/license-verification"

    def __init__(self, delay: float = REQUEST_DELAY):
        super().__init__("DC", delay)

    def verify(self, name: str, license_type: str = "") -> dict:
        result = {
            "verified": False,
            "license_number": "",
            "license_type": license_type,
            "license_status": "",
            "verification_source": "dc_doh",
            "verification_notes": "",
        }

        first_name, last_name = self._extract_name_parts(name)
        if not last_name:
            result["verification_notes"] = "Could not parse name"
            return result

        try:
            # DC DOH has a searchable database — attempt lookup
            # NOTE: The actual form submission may need adjustment based on
            # the current site structure. This is a template for the approach.
            params = {
                "last_name": last_name,
                "first_name": first_name,
            }
            resp = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            time.sleep(self.delay)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Look for results containing the therapist name
                text = soup.get_text().lower()
                if last_name.lower() in text:
                    # Found a potential match — flag for manual review
                    result["verification_notes"] = "Name found in DC DOH database — needs manual confirmation"
                    # Don't auto-verify; flag for human review
                else:
                    result["verification_notes"] = "Name not found in DC DOH search results"
            else:
                result["verification_notes"] = f"DC DOH returned status {resp.status_code}"

        except requests.RequestException as e:
            result["verification_notes"] = f"Request error: {e}"

        return result


class MDVerifier(LicenseVerifier):
    """
    Maryland Board of Professional Counselors verification.
    """

    BASE_URL = "https://health.maryland.gov/bopc"

    def __init__(self, delay: float = REQUEST_DELAY):
        super().__init__("MD", delay)

    def verify(self, name: str, license_type: str = "") -> dict:
        result = {
            "verified": False,
            "license_number": "",
            "license_type": license_type,
            "license_status": "",
            "verification_source": "md_bopc",
            "verification_notes": "",
        }

        first_name, last_name = self._extract_name_parts(name)
        if not last_name:
            result["verification_notes"] = "Could not parse name"
            return result

        try:
            # Maryland uses BPQP (Board of Professional Licensure) online lookup
            # The exact endpoint may need updates based on current site structure
            params = {
                "lastName": last_name,
                "firstName": first_name,
            }
            resp = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            time.sleep(self.delay)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text().lower()
                if last_name.lower() in text:
                    result["verification_notes"] = "Name found in MD BOPC database — needs manual confirmation"
                else:
                    result["verification_notes"] = "Name not found in MD BOPC search results"
            else:
                result["verification_notes"] = f"MD BOPC returned status {resp.status_code}"

        except requests.RequestException as e:
            result["verification_notes"] = f"Request error: {e}"

        return result


class VAVerifier(LicenseVerifier):
    """
    Virginia Department of Health Professions verification.
    Uses the DHP license lookup at dhp.virginia.gov.
    """

    BASE_URL = "https://dhp.virginia.gov/counseling"
    LOOKUP_URL = "https://dhp.virginia.gov/lookup/default"

    def __init__(self, delay: float = REQUEST_DELAY):
        super().__init__("VA", delay)

    def verify(self, name: str, license_type: str = "") -> dict:
        result = {
            "verified": False,
            "license_number": "",
            "license_type": license_type,
            "license_status": "",
            "verification_source": "va_dhp",
            "verification_notes": "",
        }

        first_name, last_name = self._extract_name_parts(name)
        if not last_name:
            result["verification_notes"] = "Could not parse name"
            return result

        try:
            params = {
                "lastName": last_name,
                "firstName": first_name,
                "profession": "counseling",
            }
            resp = self.session.get(
                self.LOOKUP_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            time.sleep(self.delay)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text().lower()
                if last_name.lower() in text:
                    result["verification_notes"] = "Name found in VA DHP database — needs manual confirmation"
                else:
                    result["verification_notes"] = "Name not found in VA DHP search results"
            else:
                result["verification_notes"] = f"VA DHP returned status {resp.status_code}"

        except requests.RequestException as e:
            result["verification_notes"] = f"Request error: {e}"

        return result


def get_verifier(state: str) -> LicenseVerifier | None:
    """Get the appropriate verifier for a state."""
    verifiers = {
        "DC": DCVerifier,
        "MD": MDVerifier,
        "VA": VAVerifier,
    }
    cls = verifiers.get(state.upper())
    return cls() if cls else None


def print_verification_summary(df: pd.DataFrame) -> None:
    """Print summary of verification results."""
    logger.info("=" * 60)
    logger.info("LICENSE VERIFICATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total records processed: {len(df)}")

    if "license_verified" in df.columns:
        verified = (df["license_verified"] == "True").sum()
        logger.info(f"Verified: {verified}")

    if "verification_notes" in df.columns:
        notes = df["verification_notes"].value_counts()
        logger.info("Results breakdown:")
        for note, count in notes.head(10).items():
            if note:
                logger.info(f"  {note}: {count}")

    logger.info("=" * 60)
    logger.info("NOTE: Auto-verification flags candidates for manual review.")
    logger.info("Always confirm license details manually before marking as verified.")


def main():
    parser = argparse.ArgumentParser(
        description="TherapistIndex License Verification (Phase 4)"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to enriched CSV",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for verified CSV",
    )
    parser.add_argument(
        "--state",
        choices=["DC", "MD", "VA", "ALL"],
        default="ALL",
        help="Which state(s) to verify (default: ALL)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of records to verify (0 = all)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY,
        help=f"Delay between requests in seconds (default: {REQUEST_DELAY})",
    )
    parser.add_argument(
        "--output-filename",
        default="therapists_verified.csv",
        help="Name of the output CSV file",
    )
    args = parser.parse_args()

    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    logger.info(f"Loading data from: {input_path}")
    df = pd.read_csv(input_path, dtype=str)
    logger.info(f"Loaded {len(df)} records")

    # Filter by state if specified
    if args.state != "ALL" and "state" in df.columns:
        df_to_verify = df[df["state"].str.upper() == args.state].copy()
        logger.info(f"Filtered to {len(df_to_verify)} records in {args.state}")
    else:
        df_to_verify = df.copy()

    # Apply limit
    if args.limit > 0:
        df_to_verify = df_to_verify.head(args.limit)
        logger.info(f"Limited to {args.limit} records")

    # Initialize verification columns
    for col in ["license_verified", "license_number", "verification_notes"]:
        if col not in df_to_verify.columns:
            df_to_verify[col] = ""

    # Process each record
    states_to_verify = ["DC", "MD", "VA"] if args.state == "ALL" else [args.state]
    verifiers = {}
    for state in states_to_verify:
        v = get_verifier(state)
        if v:
            verifiers[state] = v

    processed = 0
    for idx, row in df_to_verify.iterrows():
        state = str(row.get("state", "")).upper()
        if state not in verifiers:
            df_to_verify.at[idx, "verification_notes"] = f"No verifier available for state: {state}"
            continue

        name = row.get("therapist_name", "")
        license_type = row.get("license_type", "")

        if not name:
            continue

        processed += 1
        if processed % 10 == 0:
            logger.info(f"Progress: {processed}/{len(df_to_verify)}")

        result = verifiers[state].verify(name, license_type)

        df_to_verify.at[idx, "license_verified"] = str(result["verified"])
        if result["license_number"]:
            df_to_verify.at[idx, "license_number"] = result["license_number"]
        if result["license_type"]:
            df_to_verify.at[idx, "license_type"] = result["license_type"]
        df_to_verify.at[idx, "verification_notes"] = result.get("verification_notes", "")

    # Merge verification results back into full dataframe
    if args.state != "ALL":
        # Update only the verified rows in the original df
        for col in ["license_verified", "license_number", "verification_notes"]:
            if col not in df.columns:
                df[col] = ""
            df.loc[df_to_verify.index, col] = df_to_verify[col]
        output_df = df
    else:
        output_df = df_to_verify

    # Summary
    print_verification_summary(output_df)

    # Write output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.output_filename
    output_df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Verification results written to: {output_path}")


if __name__ == "__main__":
    main()
