"""
Flux RAG Pipeline — Article Downloader & Text Extractor
========================================================
Downloads all 30 curated articles (web pages + PDFs), extracts clean text,
and saves as .txt files ready for the ingest.py chunking pipeline.

Usage:
    python download_articles.py

Output:
    ./articles/01_nhlbi_aim_healthy_weight.txt
    ./articles/02_cdc_steps_losing_weight.txt
    ...etc

Each .txt file has metadata on line 1:
    Title: <title> | Source: <url>

Followed by the extracted body text.

Requirements:
    pip install requests beautifulsoup4 lxml pdfplumber
"""

import os
import re
import time
import logging
from pathlib import Path
from io import BytesIO

import requests
from bs4 import BeautifulSoup

# Optional: pdfplumber for PDF extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("WARNING: pdfplumber not installed. PDF extraction will be skipped.")
    print("Install with: pip install pdfplumber")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ARTICLES_DIR = Path(__file__).parent / "articles"
ARTICLES_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 30  # seconds
RETRY_DELAY = 3  # seconds between retries
MAX_RETRIES = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Article Registry — all 30 articles
# ---------------------------------------------------------------------------

ARTICLES = [
    # --- Category 1: Weight Loss & Healthy Weight (6) ---
    {
        "id": 1,
        "slug": "nhlbi_aim_healthy_weight",
        "title": "Aim for a Healthy Weight",
        "url": "https://www.nhlbi.nih.gov/health/heart-healthy-living/healthy-weight",
        "type": "web",
        "category": "weight_loss",
        "authority": "government",
    },
    {
        "id": 2,
        "slug": "cdc_steps_losing_weight",
        "title": "Steps for Losing Weight",
        "url": "https://www.cdc.gov/healthy-weight-growth/losing-weight/index.html",
        "type": "web",
        "category": "weight_loss",
        "authority": "government",
    },
    {
        "id": 3,
        "slug": "who_obesity_overweight",
        "title": "Obesity and Overweight Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
        "type": "web",
        "category": "weight_loss",
        "authority": "government",
    },
    {
        "id": 4,
        "slug": "mayo_weight_loss_6_strategies",
        "title": "Weight Loss: 6 Strategies for Success",
        "url": "https://www.mayoclinic.org/healthy-lifestyle/weight-loss/in-depth/weight-loss/art-20047752",
        "type": "web",
        "category": "weight_loss",
        "authority": "hospital",
    },
    {
        "id": 5,
        "slug": "pmc_prevention_obesity_evidence",
        "title": "Prevention of Obesity among Adults: Evidence",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12215444/",
        "type": "web",
        "category": "weight_loss",
        "authority": "peer_reviewed",
    },
    {
        "id": 6,
        "slug": "pmc_rate_weight_loss_prediction",
        "title": "Rate of Weight Loss Can Be Predicted by Patient Characteristics",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3447534/",
        "type": "web",
        "category": "weight_loss",
        "authority": "peer_reviewed",
    },
    # --- Category 2: Diet & Nutrition (6) ---
    {
        "id": 7,
        "slug": "who_healthy_diet",
        "title": "Healthy Diet Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "type": "web",
        "category": "nutrition",
        "authority": "government",
    },
    {
        "id": 8,
        "slug": "pmc_optimal_diet_strategies",
        "title": "Optimal Diet Strategies for Weight Loss and Maintenance",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8017325/",
        "type": "web",
        "category": "nutrition",
        "authority": "peer_reviewed",
    },
    {
        "id": 9,
        "slug": "ucdavis_weight_loss_guidelines",
        "title": "Helpful Guidelines for Successful Weight Loss",
        "url": "https://health.ucdavis.edu/transplant/PDFs/Helpful%20Guidelines%20for%20Successful%20Weight%20Loss.pdf",
        "type": "pdf",
        "category": "nutrition",
        "authority": "university",
    },
    {
        "id": 10,
        "slug": "harvard_healthy_eating_plate",
        "title": "Healthy Eating Plate",
        "url": "https://nutritionsource.hsph.harvard.edu/healthy-eating-plate/",
        "type": "web",
        "category": "nutrition",
        "authority": "university",
    },
    {
        "id": 11,
        "slug": "usda_dietary_guidelines_2020",
        "title": "Dietary Guidelines for Americans 2020-2025 Executive Summary",
        "url": "https://www.dietaryguidelines.gov/sites/default/files/2020-12/DGA_2020-2025_ExecutiveSummary_English.pdf",
        "type": "pdf",
        "category": "nutrition",
        "authority": "government",
    },
    {
        "id": 12,
        "slug": "harvard_water_intake",
        "title": "Water: How Much Do You Need?",
        "url": "https://nutritionsource.hsph.harvard.edu/water/",
        "type": "web",
        "category": "nutrition",
        "authority": "university",
    },
    # --- Category 3: Physical Activity & Strength Training (6) ---
    {
        "id": 13,
        "slug": "hhs_physical_activity_guidelines",
        "title": "Physical Activity Guidelines for Americans",
        "url": "https://odphp.health.gov/our-work/nutrition-physical-activity/physical-activity-guidelines/current-guidelines",
        "type": "web",
        "category": "strength",
        "authority": "government",
    },
    {
        "id": 14,
        "slug": "who_physical_activity",
        "title": "Physical Activity Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/physical-activity",
        "type": "web",
        "category": "strength",
        "authority": "government",
    },
    {
        "id": 15,
        "slug": "acsm_resistance_training",
        "title": "Resistance Training for Health and Fitness",
        "url": "https://www.prescriptiontogetactive.com/static/pdfs/resistance-training-ACSM.pdf",
        "type": "pdf",
        "category": "strength",
        "authority": "government",
    },
    {
        "id": 16,
        "slug": "healthdirect_strength_beginners",
        "title": "Strength Training for Beginners",
        "url": "https://www.healthdirect.gov.au/strength-training-for-beginners",
        "type": "web",
        "category": "strength",
        "authority": "government",
    },
    {
        "id": 17,
        "slug": "msu_acsm_recommendations",
        "title": "Evidence-Based Physical Activity Recommendations Part 2",
        "url": "https://www.canr.msu.edu/news/evidence_based_physical_activity_recommendations_part_2",
        "type": "web",
        "category": "strength",
        "authority": "university",
    },
    {
        "id": 18,
        "slug": "kaiser_strength_beginners",
        "title": "Beginners Guide: Simple Strength Training Exercises",
        "url": "https://healthy.kaiserpermanente.org/health-wellness/healtharticle.simple-ways-to-get-started-with-strength-training",
        "type": "web",
        "category": "strength",
        "authority": "hospital",
    },
    # --- Category 4: Running & Cardio (6) ---
    {
        "id": 19,
        "slug": "nhs_couch_to_5k",
        "title": "Couch to 5K Running Plan",
        "url": "https://www.nhs.uk/better-health/get-active/get-running-with-couch-to-5k/couch-to-5k-running-plan/",
        "type": "web",
        "category": "cardio",
        "authority": "government",
    },
    {
        "id": 20,
        "slug": "mayo_5k_training",
        "title": "5K Run: 7-Week Training Schedule for Beginners",
        "url": "https://www.mayoclinic.org/healthy-lifestyle/fitness/in-depth/5k-run/art-20050962",
        "type": "web",
        "category": "cardio",
        "authority": "hospital",
    },
    {
        "id": 21,
        "slug": "pmc_start_to_run_6week",
        "title": "Effectiveness of Start to Run: 6-Week Training Program",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3735486/",
        "type": "web",
        "category": "cardio",
        "authority": "peer_reviewed",
    },
    {
        "id": 22,
        "slug": "jama_aerobic_dose_response",
        "title": "Aerobic Exercise and Weight Loss Dose-Response Meta-Analysis",
        "url": "https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2828487",
        "type": "web",
        "category": "cardio",
        "authority": "peer_reviewed",
    },
    {
        "id": 23,
        "slug": "healthdirect_running_tips",
        "title": "Running Tips for Beginners",
        "url": "https://www.healthdirect.gov.au/running-tips",
        "type": "web",
        "category": "cardio",
        "authority": "government",
    },
    {
        "id": 24,
        "slug": "pmc_progressive_overload",
        "title": "Progressive Overload Without Progressing Load",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9528903/",
        "type": "web",
        "category": "cardio",
        "authority": "peer_reviewed",
    },
    # --- Category 5: Behavioral & Lifestyle (6) ---
    {
        "id": 25,
        "slug": "pmc_habit_formation_meta",
        "title": "Time to Form a Habit: Systematic Review and Meta-Analysis",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11641623/",
        "type": "web",
        "category": "behavioral",
        "authority": "peer_reviewed",
    },
    {
        "id": 26,
        "slug": "pmc_sleep_deprivation_weight",
        "title": "Sleep Deprivation: Effects on Weight Loss",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9031614/",
        "type": "web",
        "category": "behavioral",
        "authority": "peer_reviewed",
    },
    {
        "id": 27,
        "slug": "cdc_about_sleep",
        "title": "About Sleep",
        "url": "https://www.cdc.gov/sleep/about/index.html",
        "type": "web",
        "category": "behavioral",
        "authority": "government",
    },
    {
        "id": 28,
        "slug": "cleveland_stress_weight",
        "title": "Long-Term Stress Can Make You Gain Weight",
        "url": "https://health.clevelandclinic.org/stress-and-weight-gain",
        "type": "web",
        "category": "behavioral",
        "authority": "hospital",
    },
    {
        "id": 29,
        "slug": "pmc_self_monitoring_review",
        "title": "Self-Monitoring in Weight Loss: A Systematic Review",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3268700/",
        "type": "web",
        "category": "behavioral",
        "authority": "peer_reviewed",
    },
    {
        "id": 30,
        "slug": "pmc_behavioral_treatment_obesity",
        "title": "Behavioral Treatment of Obesity",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3233993/",
        "type": "web",
        "category": "behavioral",
        "authority": "peer_reviewed",
    },
]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def fetch_url(url: str) -> requests.Response | None:
    """Fetch a URL with retries and browser-like headers."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(f"  Fetching (attempt {attempt}): {url[:80]}...")
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            log.warning(f"  Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return None


def extract_text_from_html(html: str, url: str) -> str:
    """
    Extract main content text from HTML, stripping navigation,
    footers, scripts, styles, and sidebars.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                              "aside", "noscript", "iframe", "svg", "form"]):
        tag.decompose()

    # Remove common non-content classes/ids
    for selector in [
        "[class*='nav']", "[class*='sidebar']", "[class*='footer']",
        "[class*='menu']", "[class*='cookie']", "[class*='banner']",
        "[class*='advertisement']", "[class*='social']",
        "[id*='nav']", "[id*='sidebar']", "[id*='footer']",
        "[id*='menu']", "[id*='cookie']",
    ]:
        for tag in soup.select(selector):
            tag.decompose()

    # Try to find main content area (ordered by specificity)
    content = None

    # PMC articles
    if "pmc.ncbi.nlm.nih.gov" in url:
        content = soup.find("article") or soup.find("div", class_="article")
        # Remove references section from PMC articles (very long, not useful for RAG)
        if content:
            for ref_section in content.find_all("div", class_=re.compile(r"ref-list|references")):
                ref_section.decompose()
            for ref_section in content.find_all("section", id=re.compile(r"ref|reference|bibliography")):
                ref_section.decompose()

    # JAMA articles
    elif "jamanetwork.com" in url:
        content = soup.find("div", class_=re.compile(r"article-full-text|article-body"))

    # General: try common content containers
    if content is None:
        for selector in ["article", "main", "[role='main']",
                         ".article-body", ".content-body", ".entry-content",
                         "#main-content", "#content", ".main-content"]:
            content = soup.select_one(selector)
            if content:
                break

    # Fallback: use body
    if content is None:
        content = soup.find("body") or soup

    # Extract text
    text = content.get_text(separator="\n", strip=True)

    # Clean up: collapse multiple blank lines, strip excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    if not HAS_PDFPLUMBER:
        return "[PDF extraction skipped — pdfplumber not installed]"

    text_parts = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    text = "\n\n".join(text_parts)
    # Clean up
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Main download loop
# ---------------------------------------------------------------------------

def download_all():
    """Download and extract all 30 articles."""
    results = {"success": [], "failed": []}

    for article in ARTICLES:
        aid = article["id"]
        slug = article["slug"]
        title = article["title"]
        url = article["url"]
        atype = article["type"]
        category = article["category"]
        authority = article["authority"]

        filename = f"{aid:02d}_{slug}.txt"
        filepath = ARTICLES_DIR / filename

        log.info(f"[{aid:02d}/30] {title}")

        # Skip if already downloaded
        if filepath.exists() and filepath.stat().st_size > 500:
            log.info(f"  Already exists ({filepath.stat().st_size} bytes), skipping.")
            results["success"].append(filename)
            continue

        # Fetch
        resp = fetch_url(url)
        if resp is None:
            log.error(f"  FAILED to fetch: {url}")
            results["failed"].append({"id": aid, "title": title, "url": url})
            continue

        # Extract text
        if atype == "pdf":
            body = extract_text_from_pdf(resp.content)
        else:
            body = extract_text_from_html(resp.text, url)

        # Validate extraction
        if len(body) < 200:
            log.warning(f"  Extracted text suspiciously short ({len(body)} chars). Saving anyway.")

        # Build file content with metadata header
        file_content = (
            f"Title: {title} | Source: {url}\n"
            f"Category: {category} | Authority: {authority}\n"
            f"---\n"
            f"{body}\n"
        )

        # Write
        filepath.write_text(file_content, encoding="utf-8")
        char_count = len(body)
        log.info(f"  Saved: {filename} ({char_count:,} chars)")
        results["success"].append(filename)

        # Polite delay between requests
        time.sleep(1.5)

    # Summary
    print("\n" + "=" * 60)
    print(f"DOWNLOAD COMPLETE")
    print(f"  Success: {len(results['success'])}/30")
    print(f"  Failed:  {len(results['failed'])}/30")
    if results["failed"]:
        print("\nFailed articles (download manually):")
        for f in results["failed"]:
            print(f"  [{f['id']:02d}] {f['title']}")
            print(f"       {f['url']}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    download_all()
