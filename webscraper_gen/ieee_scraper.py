import requests
from datetime import datetime

def scrape_ieee(query, start_date, end_date, api_key='YOUR_API_KEY', max_papers=20):
    base_url = "https://api.ieee.org/search/v1/articles"
    
    params = {
        "apikey": api_key,
        "query_text": f'("{query}") AND (Publication Year: {start_date.year}-{end_date.year})',
        "start_record": 1,
        "max_records": max_papers,
        "format": "json"
    }

    response = requests.get(base_url, params=params)
    data = response.json()
    
    return [{
        'title': article['title'],
        'authors': [author['full_name'] for author in article['authors']],
        'date': datetime.strptime(article['publication_date'], '%Y-%m').date(),
        'pdf_url': next(link['value'] for link in article['links'] if link['type'] == 'pdf')
    } for article in data['articles']]
