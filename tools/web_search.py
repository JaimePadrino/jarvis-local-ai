import requests
from bs4 import BeautifulSoup


def search_web(query):
    url = f"https://www.google.com/search?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for g in soup.find_all("div"):
        text = g.get_text()
        if len(text) > 80:
            results.append(text)

    return "\n".join(results[:5])