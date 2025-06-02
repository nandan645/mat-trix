import requests

def scrape_core(query, start_date, end_date, max_papers=20):
    base_url = "https://api.core.ac.uk/v3/search/works"
    
    params = {
        "q": f"{query} AND createdDate:[{start_date.year} TO {end_date.year}]",
        "limit": max_papers,
        "sort": "createdDate:desc"
    }

    response = requests.get(base_url, params=params)
    data = response.json()
    
    return [{
        'title': result['title'],
        'authors': [author['name'] for author in result['authors']],
        'date': result['createdDate'][:10],
        'pdf_url': result['downloadUrl']
    } for result in data['results']]
