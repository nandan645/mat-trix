import requests

def scrape_pmc(query, start_date, end_date, max_papers=20):
    base_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    
    params = {
        "from": start_date.strftime("%Y-%m-%d"),
        "until": end_date.strftime("%Y-%m-%d"),
        "term": query,
        "format": "json",
        "size": max_papers
    }

    response = requests.get(base_url, params=params)
    data = response.json()
    
    return [{
        'title': record['title'],
        'authors': record['authorList'].split('; '),
        'date': record['pubDate'],
        'pdf_url': record['pdf_url']
    } for record in data['records']]
