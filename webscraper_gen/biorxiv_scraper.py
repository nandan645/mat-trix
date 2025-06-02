import requests

def scrape_biorxiv(query, start_date, end_date, max_papers=20):
    base_url = f"https://api.biorxiv.org/details/biorxiv/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}/0"
    
    params = {
        "format": "json",
        "limit": max_papers
    }

    response = requests.get(base_url, params=params)
    data = response.json()
    
    return [{
        'title': paper['title'],
        'authors': paper['authors'].split('; '),
        'date': paper['date'],
        'pdf_url': paper['jatsxml'].replace('.xml', '.pdf')
    } for paper in data['collection']]
