import requests
import time
import re

queries = [
    "skills matrix employee",
    "competency management hr",
    "skill inventory employee",
    "learning path skills gap",
    "consultant skills"
]

all_repos = {}

for query in queries:
    print(f"Searching for: {query}")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=20"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for item in data.get('items', []):
                full_name = item['full_name']
                if full_name not in all_repos:
                    all_repos[full_name] = {
                        'full_name': item['full_name'],
                        'stars': item['stargazers_count'],
                        'url': item['html_url'],
                        'description': item['description'] or "",
                        'queries': [query]
                    }
                else:
                    all_repos[full_name]['queries'].append(query)
        else:
            print(f"Error {response.status_code} for query {query}")
        time.sleep(2) # Avoid rate limiting
    except Exception as e:
        print(f"Exception: {e}")

relevant_keywords = ["skill", "competency", "talent", "workforce", "matrix", "hr", "learning", "assessment", "capability"]
exclude_keywords = ["game", "recipe", "hotel", "restaurant", "hospital", "movie", "book"]

curated = []
for repo in all_repos.values():
    desc = repo['description'].lower()
    
    # Check if English/English-like (rough check)
    if not any(ord(c) > 127 for c in desc):
        # Keep if mentions relevant keywords
        if any(kw in desc for kw in relevant_keywords):
            # Exclude unrelated domains
            if not any(ex in desc for ex in exclude_keywords):
                curated.append(repo)

curated.sort(key=lambda x: x['stars'], reverse=True)

print("\n--- Top 15 Relevant Repositories ---\n")
for r in curated[:15]:
    print(f"Name: {r['full_name']}")
    print(f"Stars: {r['stars']}")
    print(f"URL: {r['url']}")
    print(f"Hits: {len(r['queries'])}")
    print(f"Description: {r['description']}")
    print("-" * 20)
