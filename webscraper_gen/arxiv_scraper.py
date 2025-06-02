import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote

def scrape_arxiv(query, start_date, end_date, max_papers=20):
    base_url = "https://arxiv.org/search/"
    date_fmt = "%Y%m%d%H%M%S"
    
    params = {
        "query": f"{query} AND submittedDate:[{start_date.strftime(date_fmt)} TO {end_date.strftime(date_fmt)}]",
        "searchtype": "all",
        "order": "-submitted_date",
        "size": max_papers
    }

    response = requests.get(base_url, params=params)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    papers = []
    for result in soup.select('li.arxiv-result'):
        papers.append({
            'title': result.select_one('p.title').text.strip(),
            'authors': [a.text for a in result.select('p.authors a')],
            'date': datetime.strptime(result.select_one('p.is-size-7').text.split(';')[0].strip(), 
                                    '%a, %d %b %Y %H:%M:%S %Z').date(),
            'pdf_url': result.select_one('a[title="Download PDF"]')['href']
        })
    
    return papers
