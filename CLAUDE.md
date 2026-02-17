# CLAUDE.md — TherapistIndex Project

## Project Overview

**TherapistIndex** (therapistindex.com) is a national therapist directory that helps people find mental health professionals based on real, verified data — not self-reported marketing copy. Built on WordPress + GeoDirectory, hosted on Hostinger.

**Owner:** Mike Bennett (Quantum Shield Labs LLC)
**Stack:** WordPress 6.9.1, GeoDirectory 2.8.151, Yoast SEO, PHP, Python (data pipeline)
**Hosting:** Hostinger web hosting (shared), domain: therapistindex.com
**Secondary domain:** therapistsearch.site (redirect to primary)

---

## Business Model

### Revenue Streams (in order of priority)
1. **Premium Listings** — therapists pay $29-$49/mo for enhanced profiles (photos, priority placement, verified badge)
2. **Lead Generation** — contact form submissions → charge per lead ($10-$30) or monthly retainer
3. **Display Ads** — AdSense immediately, Mediavine at 50K sessions/month ($15-$30 RPM)
4. **Affiliate** — BetterHelp, Talkspace, therapy tools affiliate links on blog content
5. **Data/Reports** — "State of Therapy Access" reports as lead magnets

### Competitive Advantage (The Moat)
Data that Psychology Today, GoodTherapy, and Zencare do NOT have:
- Verified insurance panels (not self-reported)
- Actual pricing ranges / sliding scale confirmed
- Currently accepting new patients (verified)
- Wait time estimates
- Telehealth platform used
- Languages spoken
- State licensing board verification

---

## Technical Architecture

### WordPress Setup
- **Theme:** Default (to be customized)
- **Core Plugin:** GeoDirectory (handles listings, maps, search, filtering, schema)
- **SEO:** Yoast SEO (sitemaps, meta, schema markup)
- **Forms:** Ninja Forms (contact/lead capture on listings)
- **Users:** UsersWP (therapist account management, listing claims)
- **Analytics:** Google Site Kit (Search Console + GA4)
- **Maps:** OpenStreetMap (free, no API key needed)
- **Cache:** LiteSpeed Cache (Hostinger built-in)

### GeoDirectory Custom Fields Needed
These are the data columns that make our directory unique:

```
- therapist_name (text)
- practice_name (text)
- address (address - GeoDirectory built-in)
- phone (phone - GeoDirectory built-in)
- email (email)
- website (url)
- license_type (select: LCSW, LPC, LMFT, PsyD, PhD, MD/Psychiatrist, LCPC, LCMFT)
- license_number (text)
- license_state (select: DC, MD, VA, PA, DE, WV, + all states)
- license_verified (checkbox)
- specializations (multiselect: Anxiety, Depression, PTSD/Trauma, Couples/Marriage, LGBTQ+, Grief, Addiction, ADHD, OCD, Eating Disorders, Child/Adolescent, Family, Anger Management, Life Transitions, Chronic Illness, Perinatal/Postpartum)
- insurance_accepted (multiselect: Aetna, BlueCross BlueShield, CareFirst, Cigna, Humana, Kaiser, Medicaid, Medicare, Tricare, UnitedHealthcare, Anthem, Magellan, Out-of-Network, Self-Pay Only)
- sliding_scale (select: Yes, No, Unknown)
- price_range_min (number)
- price_range_max (number)
- session_length (select: 30min, 45min, 50min, 60min, 90min)
- telehealth (select: Yes - Video, Yes - Phone, Yes - Both, No, Unknown)
- telehealth_platform (text: Doxy.me, Zoom, SimplePractice, etc.)
- accepting_new_patients (select: Yes, No, Waitlist, Unknown)
- wait_time (select: Immediate, 1-2 weeks, 2-4 weeks, 1+ month, Unknown)
- languages (multiselect: English, Spanish, Mandarin, Korean, Vietnamese, ASL, French, Arabic, Amharic, Other)
- therapy_approaches (multiselect: CBT, DBT, EMDR, Psychodynamic, Humanistic, Solution-Focused, ACT, Mindfulness-Based, Play Therapy, Art Therapy, Somatic)
- age_groups_served (multiselect: Children 0-12, Adolescents 13-17, Adults 18-64, Seniors 65+, Couples, Families, Groups)
- gender (select: Male, Female, Non-Binary, Prefer not to say)
- years_experience (number)
- education (text)
- profile_image_url (text/url)
- google_rating (number)
- google_review_count (number)
- last_verified_date (date)
- data_source (text: outscraper, crawl4ai, manual)
- enrichment_status (select: raw, cleaned, enriched_basic, enriched_full, verified)
```

---

## Data Pipeline

### Phase 1: Raw Data Collection (OutScraper)
**Tool:** OutScraper (outscraper.com) — Google Maps API scraper
**Queries to run:**
```
"therapist" — Washington DC
"therapist" — Maryland
"therapist" — Virginia
"psychologist" — Washington DC
"psychologist" — Maryland
"psychologist" — Virginia
"counselor mental health" — Washington DC
"counselor mental health" — Maryland
"counselor mental health" — Virginia
"psychiatrist" — Washington DC
"psychiatrist" — Maryland
"psychiatrist" — Virginia
"marriage counselor" — Washington DC / MD / VA
"family therapist" — Washington DC / MD / VA
```
**Expected output:** 5,000-10,000 raw records as CSV
**Fields from OutScraper:** name, address, phone, website, rating, reviews_count, category, hours, latitude, longitude

### Phase 2: Data Cleaning (Python / Claude Code)
```python
# Cleaning steps:
# 1. Remove duplicates (by name + address combo)
# 2. Remove non-therapist results (massage therapists, physical therapists, acupuncture)
# 3. Remove permanently closed businesses
# 4. Standardize phone numbers to (XXX) XXX-XXXX
# 5. Standardize addresses (proper capitalization, state abbreviations)
# 6. Validate website URLs (remove dead links)
# 7. Categorize by license type from business name/category
# 8. De-duplicate entries that appear in multiple search queries
# 9. Flag chains/group practices vs solo practitioners
```
**Target:** 5,000-10,000 raw → 2,000-4,000 cleaned records

### Phase 3: Data Enrichment (Crawl4AI + Claude API)
**Tool:** Crawl4AI (open source web crawler)
**For each therapist with a website, scrape:**
```
- Insurance panels accepted
- Pricing / fees / sliding scale
- Specializations listed
- Telehealth availability
- Currently accepting new patients
- Education / credentials
- Bio / about text (for summarization)
- Profile photo URL
```
**Enrichment priority order:**
1. Insurance accepted (highest value to users)
2. Accepting new patients (second highest)
3. Pricing/sliding scale
4. Specializations
5. Telehealth
6. Everything else

### Phase 4: License Verification
**Sources:**
- DC: doh.dc.gov/service/license-verification
- MD: health.maryland.gov/bopc (Board of Professional Counselors)
- VA: dhp.virginia.gov/counseling

Cross-reference scraped therapist names against state licensing databases.

### Phase 5: Import to WordPress/GeoDirectory
**Method:** GeoDirectory CSV Import or WordPress REST API
**Format:** CSV with columns matching GeoDirectory custom fields
**Batch size:** 500 records per import to avoid timeouts

---

## SEO Strategy

### Page Types (Programmatic)
1. **Individual listing pages:** `/therapist/jane-doe-bethesda-md/`
2. **City pages:** `/therapists-in-bethesda-md/`
3. **State pages:** `/therapists-in-maryland/`
4. **Insurance filter pages:** `/therapists-accepting-aetna-maryland/`
5. **Specialization filter pages:** `/ptsd-therapists-washington-dc/`
6. **Combined filter pages:** `/therapists-accepting-medicaid-silver-spring-md/`

### Target Keywords (Long-tail first)
```
"therapist accepting [insurance] in [city] [state]"
"sliding scale therapist [city]"
"[specialization] therapist near [city]"
"therapist accepting new patients [city]"
"telehealth therapist [state]"
"[language] speaking therapist [city]"
```

### Schema Markup
Every listing should have:
- LocalBusiness schema
- MedicalBusiness schema
- Physician schema (for psychiatrists)
- Review/Rating schema (from Google reviews)

Yoast handles basic schema; GeoDirectory adds listing-specific schema.

### Blog Content Plan
Blog posts target informational keywords that feed into directory pages:
- "How to Find a Therapist That Takes [Insurance] in [State]"
- "Sliding Scale Therapy Options in [City]: Complete Guide"
- "Online vs In-Person Therapy: What to Know in 2026"
- "Questions to Ask a New Therapist Before Your First Session"
- "Understanding Therapy Costs in [State]: Insurance, Sliding Scale, and Free Options"

Each blog post links to relevant directory filter pages.

---

## File Structure

```
therapistindex/
├── CLAUDE.md                          # This file
├── data/
│   ├── raw/                           # OutScraper CSV exports
│   │   ├── outscraper_dc_therapist.csv
│   │   ├── outscraper_md_therapist.csv
│   │   └── outscraper_va_therapist.csv
│   ├── cleaned/                       # Post-cleaning CSVs
│   │   └── therapists_cleaned.csv
│   ├── enriched/                      # Post-enrichment CSVs
│   │   └── therapists_enriched.csv
│   └── import_ready/                  # Final CSV for GeoDirectory import
│       └── therapists_geodirectory_import.csv
├── scripts/
│   ├── clean_data.py                  # Data cleaning pipeline
│   ├── enrich_data.py                 # Crawl4AI enrichment pipeline
│   ├── verify_licenses.py            # License verification scraper
│   ├── prepare_import.py             # Format data for GeoDirectory CSV import
│   └── utils.py                      # Shared utilities
├── config/
│   ├── outscraper_queries.json       # Search queries for OutScraper
│   ├── insurance_list.json           # Standardized insurance names
│   ├── specializations.json          # Standardized specialization categories
│   └── filter_keywords.json          # Words that identify non-therapist results
├── wordpress/
│   ├── custom_fields_setup.php       # GeoDirectory custom field configuration
│   ├── theme_customizations.css      # CSS overrides
│   └── functions_additions.php       # Custom PHP for WordPress
└── content/
    ├── blog_posts/                    # Pre-written blog content
    └── page_templates/                # City/state page templates
```

---

## WordPress Credentials & Access

- **WP Admin:** https://therapistindex.com/wp-admin/
- **Hosting:** Hostinger hPanel
- **Admin email:** michael@quantumshieldlabs.dev
- **GeoDirectory:** Installed and configured (OpenStreetMap, default location DC)

---

## Development Workflow

1. **Data work** → Python scripts in `/scripts/` directory
2. **WordPress customization** → PHP/CSS changes, test locally or via WP admin
3. **Content** → Blog posts written in markdown, imported to WordPress
4. **SEO** → Yoast handles most automatically; manual optimization for key pages

### Commands Cheat Sheet
```bash
# Install Python dependencies
pip install crawl4ai pandas requests beautifulsoup4 anthropic

# Run data cleaning
python scripts/clean_data.py --input data/raw/ --output data/cleaned/

# Run enrichment
python scripts/enrich_data.py --input data/cleaned/therapists_cleaned.csv --output data/enriched/

# Prepare GeoDirectory import
python scripts/prepare_import.py --input data/enriched/therapists_enriched.csv --output data/import_ready/
```

---

## Key Metrics to Track

- **Listings count** (target: 2,000+ by end of month 1)
- **Google indexed pages** (check Search Console weekly)
- **Organic traffic** (GA4 — goal: 1,000 visitors/month by month 3)
- **Premium listing conversions** (Stripe)
- **Lead form submissions** (Ninja Forms)
- **Revenue** (ads + premium + leads)

---

## Important Notes

- Start with DMV (DC/MD/VA) then expand state by state
- Data quality > data quantity — better to have 500 fully enriched listings than 5,000 bare-bones ones
- The MOAT is verified insurance + pricing data that no competitor has
- Every new city we add = hundreds of new SEO pages automatically via GeoDirectory
- therapistsearch.site should 301 redirect to therapistindex.com
- This project is separate from Quantum Shield Labs — different branding, different audience
- Mike also maintains CrawDaddy Security (Virtuals Protocol ACP agent) and QSL consulting — this directory is the fast-money income stream
