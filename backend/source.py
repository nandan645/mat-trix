import json
import time
import random
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Output file path
JSON_PATH = Path("nature_articles.json")

# Load previously saved URLs
existing_urls = set()
if JSON_PATH.exists():
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            existing_articles = json.load(f)
            existing_urls = {article["URL"] for article in existing_articles}
    except Exception as e:
        print(f"[WARN] Failed to load existing JSON: {e}")
        existing_articles = []
else:
    existing_articles = []

def save_articles(new_articles):
    if not new_articles:
        return
    existing_articles.extend(new_articles)
    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_articles, f, ensure_ascii=False, indent=2)
        print(f"[SAVE] {len(new_articles)} articles saved to JSON.")
    except Exception as e:
        print(f"[ERROR] Failed to save articles: {e}")

def parse_articles_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("li", class_="app-article-list-row__item")
    new_data = []

    for item in items:
        title_tag = item.find("a", class_="c-card__link u-link-inherit")
        if not title_tag:
            continue

        title = title_tag.text.strip()
        relative_url = title_tag.get("href", "")
        full_url = f"https://www.nature.com{relative_url}"

        if full_url in existing_urls:
            print(f"[SKIP] Already saved: {full_url}")
            continue

        oa_tag = item.find("span", class_="u-color-open-access")
        open_access = "Yes" if oa_tag and "Open Access" in oa_tag.text else "No"

        date_tag = item.find("time", class_="c-meta__item")
        date_iso = date_tag.get("datetime") if date_tag else ""

        article_data = {
            "Title": title,
            "URL": full_url,
            "Open Access": open_access,
            "Date (ISO)": date_iso
        }

        existing_urls.add(full_url)
        new_data.append(article_data)

    return new_data

def scrape_pages(start_page=1, max_pages=5):
    print(f"[START] Scraping pages {start_page} to {start_page + max_pages - 1}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = context.new_page()

        for i in range(start_page, start_page + max_pages):
            print(f"[PAGE] Scraping page {i}")
            url = (
                f"https://www.nature.com/search"
                f"?order=date_desc&subject=materials-science"
                f"&article_type=research%2C+reviews%2C+protocols&page={i}"
            )
            try:
                page.goto(url, timeout=15000)
                page.wait_for_selector("li.app-article-list-row__item", timeout=10000)
                html = page.content()
                articles = parse_articles_from_html(html)

                if not articles:
                    print("[INFO] No new articles found on this page. Skipping.")
                    break

                save_articles(articles)

            except Exception as e:
                print(f"[ERROR] Failed to scrape page {i}: {e}")

            time.sleep(random.uniform(1.5, 3.5))  # Simulated human pause

        browser.close()
    print("[DONE] Scraping finished.")

# Start scraping
scrape_pages(start_page=1, max_pages=5)
