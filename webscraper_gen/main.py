import argparse
from datetime import datetime
from arxiv_scraper import scrape_arxiv
from ieee_scraper import scrape_ieee
from pmc_scraper import scrape_pmc
from core_scraper import scrape_core
from biorxiv_scraper import scrape_biorxiv

def valid_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: {date_str}. Use YYYY-MM-DD.")

def main():
    parser = argparse.ArgumentParser(description="Research Paper Scraper")
    parser.add_argument('--source', choices=['arxiv', 'ieee', 'pmc', 'core', 'biorxiv', 'all'], default='all')
    parser.add_argument('--query', type=str, required=True, help='Search query (title/topic)')
    parser.add_argument('--start', type=valid_date, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=valid_date, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--max', type=int, default=20, help='Max papers per source')
    args = parser.parse_args()

    scrapers = {
        'arxiv': scrape_arxiv,
        'ieee': scrape_ieee,
        'pmc': scrape_pmc,
        'core': scrape_core,
        'biorxiv': scrape_biorxiv,
    }

    results = []
    sources = [args.source] if args.source != 'all' else scrapers.keys()

    for src in sources:
        print(f"Scraping {src}...")
        try:
            papers = scrapers[src](args.query, args.start, args.end, args.max)
            for paper in papers:
                paper['source'] = src
            results.extend(papers)
            print(f"  Found {len(papers)} papers.")
        except Exception as e:
            print(f"  Error scraping {src}: {e}")

    # Print results (or save to file)
    for paper in results:
        print(f"\n[{paper['source'].upper()}] {paper['title']}\nAuthors: {', '.join(paper['authors'])}\nDate: {paper['date']}\nPDF: {paper['pdf_url']}\n")

    print(f"\nTotal papers found: {len(results)}")

if __name__ == "__main__":
    main()
