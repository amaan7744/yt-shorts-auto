#!/usr/bin/env python3
"""
Case Search – REAL CRIME SOURCES ONLY

FEATURES:
- Multiple dedicated crime news sources
- NEVER generates fake/placeholder data
- Strict duplicate prevention (content + case fingerprinting)
- Comprehensive RSS feeds from major crime news outlets
- Direct scraping from crime-specific news sites
- Retry logic for network resilience
- Always produces unique, real cases or fails cleanly
"""

import json
import os
import re
import hashlib
import random
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

# ==================================================
# FILES
# ==================================================

OUT_FILE = Path("case.json")
MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
USED_ARTICLES_FILE = MEMORY_DIR / "used_articles.json"
CASE_HISTORY_FILE = MEMORY_DIR / "case_history.json"
MEMORY_DIR.mkdir(exist_ok=True)

# ==================================================
# CONFIG
# ==================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ==================================================
# COMPREHENSIVE CRIME NEWS SOURCES
# ==================================================

CRIME_RSS_FEEDS = [
    # Major News - Crime Sections
    "https://feeds.npr.org/1001/rss.xml",  # NPR News
    "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World
    "https://www.abc.net.au/news/feed/51120/rss.xml",  # ABC News
    
    # Google News - Crime Specific
    "https://news.google.com/rss/search?q=murder+investigation+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=homicide+arrest+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=found+dead+investigation+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=suspicious+death+police+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=body+found+homicide+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=shooting+death+investigation+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=missing+person+found+dead+when:7d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=cold+case+solved+when:30d&hl=en-US&gl=US&ceid=US:en",
    
    # Regional News - Crime
    "https://news.google.com/rss/search?q=murder+site:nytimes.com+when:14d",
    "https://news.google.com/rss/search?q=homicide+site:washingtonpost.com+when:14d",
    "https://news.google.com/rss/search?q=crime+site:latimes.com+when:14d",
    "https://news.google.com/rss/search?q=murder+site:chicagotribune.com+when:14d",
]

# Direct crime news websites to scrape
CRIME_NEWS_SITES = [
    {
        "url": "https://apnews.com/hub/crime",
        "name": "AP News Crime",
        "article_selector": "div.PagePromo",
        "link_selector": "a.Link",
    },
    {
        "url": "https://www.crimeonline.com/",
        "name": "Crime Online",
        "article_selector": "article",
        "link_selector": "a",
    },
    {
        "url": "https://www.oxygen.com/crime-news",
        "name": "Oxygen Crime News",
        "article_selector": "div.m-ellipsis",
        "link_selector": "a",
    },
    {
        "url": "https://www.thedailybeast.com/category/crime",
        "name": "Daily Beast Crime",
        "article_selector": "article",
        "link_selector": "a.Card__link",
    },
    {
        "url": "https://www.reuters.com/world/us/",
        "name": "Reuters US News",
        "article_selector": "article",
        "link_selector": "a",
    },
    {
        "url": "https://www.foxnews.com/category/us/crime",
        "name": "Fox News Crime",
        "article_selector": "article",
        "link_selector": "a",
    },
    {
        "url": "https://www.nbcnews.com/crime",
        "name": "NBC Crime",
        "article_selector": "div.package-module",
        "link_selector": "a",
    },
    {
        "url": "https://abcnews.go.com/US",
        "name": "ABC US News",
        "article_selector": "div.ContentRoll__Item",
        "link_selector": "a",
    },
]

# True crime and investigation sites
TRUE_CRIME_SITES = [
    "https://www.insideedition.com/crime",
    "https://www.courttv.com/tag/crime/",
    "https://www.investigationdiscovery.com/crimefeed",
    "https://www.truecrimedaily.com/",
]

MAX_TEXT_LEN = 3000
MIN_TEXT_LEN = 500
MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================================================
# DUPLICATE PREVENTION
# ==================================================

def load_json_file(filepath, default=None):
    """Safely load JSON file with default fallback"""
    if not filepath.exists():
        if default is None:
            default = []
        filepath.write_text(json.dumps(default))
        return default
    try:
        return json.loads(filepath.read_text())
    except:
        return default if default else []

def save_json_file(filepath, data):
    """Safely save JSON file"""
    try:
        filepath.write_text(json.dumps(data, indent=2))
    except Exception as e:
        print(f"⚠️ Warning: Could not save {filepath.name}: {e}")

def load_used_cases():
    """Load set of used case fingerprints"""
    return set(load_json_file(USED_CASES_FILE, []))

def load_used_articles():
    """Load set of used article URLs/fingerprints"""
    return set(load_json_file(USED_ARTICLES_FILE, []))

def load_case_history():
    """Load full history of cases for deep duplicate checking"""
    return load_json_file(CASE_HISTORY_FILE, [])

def save_case_to_history(case):
    """Save case to history for future duplicate checking"""
    history = load_case_history()
    history.append({
        "case": case,
        "timestamp": datetime.now().isoformat(),
    })
    save_json_file(CASE_HISTORY_FILE, history)

def fingerprint(text):
    """Generate SHA256 fingerprint of text"""
    return hashlib.sha256(text.lower().encode()).hexdigest()

def generate_case_fingerprint(case):
    """Generate unique fingerprint for a case based on multiple fields"""
    # Combine multiple fields for robust duplicate detection
    components = [
        case.get("full_name", "").lower().strip(),
        case.get("location", "").lower().strip(),
        case.get("date", "").lower().strip(),
        # Use first 100 chars of summary for similarity
        case.get("summary", "")[:100].lower().strip(),
    ]
    combined = "|".join(components)
    return fingerprint(combined)

def is_duplicate_case(case, used_fingerprints, history):
    """Check if case is duplicate using multiple methods"""
    
    # Method 1: Exact fingerprint match
    case_fp = generate_case_fingerprint(case)
    if case_fp in used_fingerprints:
        print("  ⏭️  Duplicate: Exact fingerprint match")
        return True
    
    # Method 2: Name + location fuzzy match
    new_name = case.get("full_name", "").lower().strip()
    new_location = case.get("location", "").lower().strip()
    
    for hist_entry in history:
        hist_case = hist_entry["case"]
        hist_name = hist_case.get("full_name", "").lower().strip()
        hist_location = hist_case.get("location", "").lower().strip()
        
        # Skip generic placeholder names
        if "not publicly released" in new_name or "not publicly released" in hist_name:
            continue
        
        # Check name similarity (allowing for middle names, etc.)
        if new_name and hist_name:
            # Extract key parts (first and last name)
            new_parts = set(new_name.split())
            hist_parts = set(hist_name.split())
            
            # If 2+ name parts match and location matches
            if len(new_parts & hist_parts) >= 2 and new_location == hist_location:
                print(f"  ⏭️  Duplicate: Similar name + location ({new_name} ≈ {hist_name})")
                return True
    
    # Method 3: Summary text similarity (crude check)
    new_summary = case.get("summary", "").lower()
    for hist_entry in history[-50:]:  # Check last 50 cases
        hist_summary = hist_entry["case"].get("summary", "").lower()
        if len(new_summary) > 100 and len(hist_summary) > 100:
            # Check for significant overlap (>70% of words)
            new_words = set(new_summary.split())
            hist_words = set(hist_summary.split())
            overlap = len(new_words & hist_words) / max(len(new_words), len(hist_words))
            if overlap > 0.7:
                print(f"  ⏭️  Duplicate: High summary similarity ({overlap:.0%})")
                return True
    
    return False

def clean(t):
    """Clean and normalize text"""
    return re.sub(r"\s+", " ", t).strip()

# ==================================================
# NETWORK WITH RETRY
# ==================================================

def fetch_with_retry(url, timeout=20):
    """Fetch URL with exponential backoff retry"""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ Retry {attempt + 1}/{MAX_RETRIES} after {wait:.1f}s")
                time.sleep(wait)
            else:
                print(f"  ❌ Failed after {MAX_RETRIES} attempts: {str(e)[:100]}")
    return None

# ==================================================
# ARTICLE FETCHING
# ==================================================

def fetch_articles_from_rss():
    """Fetch article links from all RSS feeds"""
    links = []
    print("🔍 Fetching from RSS feeds...")
    
    for i, feed in enumerate(CRIME_RSS_FEEDS, 1):
        try:
            print(f"  [{i}/{len(CRIME_RSS_FEEDS)}] {feed[:60]}...")
            r = fetch_with_retry(feed, timeout=15)
            if not r:
                continue
            
            soup = BeautifulSoup(r.text, "xml")
            
            # Try different RSS formats
            items = soup.find_all("item") or soup.find_all("entry")
            
            for item in items:
                # Try multiple link formats
                link = None
                if item.find("link"):
                    link_tag = item.find("link")
                    link = link_tag.text.strip() if link_tag.text else link_tag.get("href")
                elif item.find("guid"):
                    guid = item.find("guid").text.strip()
                    if guid.startswith("http"):
                        link = guid
                
                if link:
                    links.append(link.strip())
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"  ⚠️ RSS error: {str(e)[:100]}")
    
    print(f"  ✓ Got {len(links)} links from RSS")
    return links

def fetch_articles_from_sites():
    """Fetch article links from direct news sites"""
    links = []
    print("🔍 Fetching from crime news sites...")
    
    for i, site in enumerate(CRIME_NEWS_SITES, 1):
        try:
            print(f"  [{i}/{len(CRIME_NEWS_SITES)}] {site['name']}...")
            r = fetch_with_retry(site["url"], timeout=15)
            if not r:
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Find all links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                
                # Convert relative to absolute URLs
                if not href.startswith("http"):
                    href = urljoin(site["url"], href)
                
                # Filter for article-like URLs
                parsed = urlparse(href)
                if parsed.netloc and len(parsed.path) > 10:
                    # Exclude common non-article paths
                    exclude = ["login", "signup", "subscribe", "category", "tag", "author", "search"]
                    if not any(ex in href.lower() for ex in exclude):
                        links.append(href)
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"  ⚠️ Site error: {str(e)[:100]}")
    
    print(f"  ✓ Got {len(links)} links from sites")
    return links

def fetch_articles_from_true_crime():
    """Fetch from true crime focused sites"""
    links = []
    print("🔍 Fetching from true crime sites...")
    
    for i, url in enumerate(TRUE_CRIME_SITES, 1):
        try:
            print(f"  [{i}/{len(TRUE_CRIME_SITES)}] {url}...")
            r = fetch_with_retry(url, timeout=15)
            if not r:
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if not href.startswith("http"):
                    href = urljoin(url, href)
                
                # Look for article patterns
                if re.search(r'/\d{4}/\d{2}/', href) or "article" in href or "story" in href:
                    links.append(href)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ⚠️ True crime site error: {str(e)[:100]}")
    
    print(f"  ✓ Got {len(links)} links from true crime sites")
    return links

def fetch_all_articles():
    """Fetch articles from all sources"""
    all_links = []
    
    # Fetch from all sources
    all_links.extend(fetch_articles_from_rss())
    all_links.extend(fetch_articles_from_sites())
    all_links.extend(fetch_articles_from_true_crime())
    
    # Remove duplicates and shuffle
    all_links = list(set(all_links))
    random.shuffle(all_links)
    
    print(f"📰 Total unique articles: {len(all_links)}")
    return all_links

# ==================================================
# ARTICLE TEXT EXTRACTION
# ==================================================

def extract_text_method_1(soup):
    """Standard paragraph extraction"""
    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text() for p in paragraphs)
    return clean(text)

def extract_text_method_2(soup):
    """Article tag extraction"""
    article = soup.find("article")
    if article:
        return clean(article.get_text())
    return ""

def extract_text_method_3(soup):
    """Main content extraction"""
    # Try common content containers
    for selector in ["main", "div[class*='content']", "div[class*='article']", "div[class*='story']"]:
        content = soup.select_one(selector)
        if content:
            return clean(content.get_text())
    return ""

def extract_text_method_4(soup):
    """Schema.org articleBody extraction"""
    article_body = soup.find(attrs={"itemprop": "articleBody"})
    if article_body:
        return clean(article_body.get_text())
    return ""

def fetch_article_text(url):
    """Fetch and extract article text using multiple methods"""
    try:
        r = fetch_with_retry(url, timeout=15)
        if not r:
            return None
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "form"]):
            tag.decompose()
        
        # Try all extraction methods
        texts = [
            extract_text_method_1(soup),
            extract_text_method_2(soup),
            extract_text_method_3(soup),
            extract_text_method_4(soup),
        ]
        
        # Pick longest valid text
        valid_texts = [t for t in texts if len(t) >= MIN_TEXT_LEN]
        if valid_texts:
            text = max(valid_texts, key=len)
            return text[:MAX_TEXT_LEN]
            
    except Exception as e:
        print(f"  ⚠️ Text extraction error: {str(e)[:100]}")
    
    return None

# ==================================================
# AI EXTRACTION
# ==================================================

def init_client():
    """Initialize Groq client"""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY environment variable not set")
    return Groq(api_key=key)

def validate_case_fields(case):
    """Validate that case has all required fields with real data"""
    required = [
        "full_name",
        "location",
        "date",
        "time",
        "summary",
        "key_detail",
        "official_story",
    ]
    
    # Check all fields exist
    for field in required:
        if field not in case or not case[field]:
            return False, f"Missing field: {field}"
    
    # Check for placeholder/generic values
    placeholder_phrases = [
        "not available",
        "not disclosed",
        "placeholder",
        "unknown",
        "not specified",
        "not released",
        "case data unavailable",
        "data unavailable",
    ]
    
    # At least name and location should have real data
    name = case["full_name"].lower()
    location = case["location"].lower()
    
    # Allow "not publicly released" for name (common in real cases)
    # But location should be specific
    if any(phrase in location for phrase in ["not disclosed", "unavailable", "unknown", "not specified"]):
        return False, "Location too vague"
    
    # Summary should be substantial
    if len(case["summary"]) < 50:
        return False, "Summary too short"
    
    return True, "Valid"

def extract_case(client, text):
    """Extract structured case data from article text"""
    
    prompt = f"""You are extracting crime case information from a news article.

CRITICAL INSTRUCTIONS:
1. Extract ONLY factual information explicitly stated in the article
2. NEVER invent, assume, or fabricate any details
3. Return ONLY valid JSON, nothing else
4. If critical information is missing, the extraction fails - return empty JSON: {{}}

REQUIRED FIELDS (all must have real data from the article):
- full_name: Victim's full name (or "Name not publicly released" if article states this)
- location: Specific city/town, state/region, country (MUST be specific, not "unknown")
- date: Specific date or time period mentioned (e.g., "January 15, 2026" or "early February 2026")
- time: Time of day if mentioned (e.g., "11:30 PM", "early morning", "late evening")
- summary: 2-3 sentences describing what happened based on the article
- key_detail: One specific investigative detail, evidence, or fact mentioned
- official_story: What police/authorities/officials stated (quote or paraphrase)

VALIDATION RULES:
- If the article doesn't mention a specific location (city/region), return {{}}
- If there's no death/crime case in the article, return {{}}
- Summary must be at least 50 characters and describe the incident
- All fields must contain real information from the article, not generic placeholders

ARTICLE TEXT:
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON or empty object:"""

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.15,
            max_completion_tokens=900,
        )
        
        content = res.choices[0].message.content.strip()
        
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        case = json.loads(content)
        
        # Empty object means extraction failed
        if not case or len(case) == 0:
            return None
        
        # Validate fields
        valid, msg = validate_case_fields(case)
        if not valid:
            print(f"  ⚠️ Validation failed: {msg}")
            return None
        
        # Clean all fields
        for field in case:
            if isinstance(case[field], str):
                case[field] = clean(case[field])
        
        return case
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️ LLM extraction error: {e}")
        return None

# ==================================================
# MAIN
# ==================================================

def main():
    print("=" * 60)
    print("🚀 CASE SEARCH - REAL CRIME SOURCES ONLY")
    print("=" * 60)
    
    # Initialize
    used_cases = load_used_cases()
    used_articles = load_used_articles()
    case_history = load_case_history()
    
    print(f"📊 History: {len(case_history)} total cases, {len(used_articles)} used articles")
    
    # Initialize Groq
    try:
        client = init_client()
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Groq client: {e}")
    
    # Fetch articles from all sources
    links = fetch_all_articles()
    
    if not links:
        raise RuntimeError("❌ No articles found from any source - check network connection")
    
    print(f"\n{'='*60}")
    print(f"🔎 Processing up to 100 articles to find unique case...")
    print(f"{'='*60}\n")
    
    # Try to extract a valid, unique case
    for i, link in enumerate(links[:100], 1):
        print(f"📄 [{i}/100] {link[:70]}...")
        
        # Check if article URL already used
        url_fp = fingerprint(link)
        if url_fp in used_articles:
            print("  ⏭️  Article URL already processed")
            continue
        
        # Fetch article text
        article_text = fetch_article_text(link)
        if not article_text:
            print("  ⏭️  Could not extract text")
            continue
        
        # Check if article content already used
        article_fp = fingerprint(article_text)
        if article_fp in used_articles:
            print("  ⏭️  Article content already processed")
            continue
        
        # Extract case
        print("  🤖 Extracting case data...")
        case = extract_case(client, article_text)
        
        if not case:
            print("  ⏭️  Extraction failed or invalid data")
            continue
        
        # Check for duplicates
        if is_duplicate_case(case, used_cases, case_history):
            continue
        
        # Success! We have a unique, valid case
        print(f"\n{'='*60}")
        print(f"✅ UNIQUE CASE FOUND!")
        print(f"{'='*60}")
        print(f"Name: {case['full_name']}")
        print(f"Location: {case['location']}")
        print(f"Date: {case['date']}")
        print(f"{'='*60}\n")
        
        # Save case
        OUT_FILE.write_text(json.dumps(case, indent=2), encoding="utf-8")
        
        # Update tracking
        case_fp = generate_case_fingerprint(case)
        used_cases.add(case_fp)
        used_articles.add(url_fp)
        used_articles.add(article_fp)
        
        save_json_file(USED_CASES_FILE, sorted(used_cases))
        save_json_file(USED_ARTICLES_FILE, sorted(used_articles))
        save_case_to_history(case)
        
        print("💾 Case saved to case.json")
        print("📝 Tracking data updated")
        return
    
    # If we get here, no unique case was found
    raise RuntimeError(
        f"❌ No unique cases found after processing {min(100, len(links))} articles.\n"
        f"All articles were either duplicates or could not be processed.\n"
        f"Try again later when new crime news is published."
    )

if __name__ == "__main__":
    main()
