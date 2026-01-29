from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

# Load websites
def load_websites():
    try:
        with open('websites.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

WEBSITES = load_websites()

def fetch_and_search(url, query):
    """Fetch a URL and search for the query"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=5, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Get title
        title = soup.title.string if soup.title else url
        
        # Search for query
        text_lower = text.lower()
        query_lower = query.lower()
        match_count = text_lower.count(query_lower)
        
        if match_count > 0:
            # Find snippet
            index = text_lower.find(query_lower)
            start = max(0, index - 75)
            end = min(len(text), index + 225)
            snippet = text[start:end]
            
            # Clean snippet
            snippet = ' '.join(snippet.split())
            if len(snippet) > 150:
                snippet = snippet[:150] + '...'
            
            return {
                'title': str(title)[:100],
                'url': url,
                'snippet': snippet,
                'relevance': match_count
            }
        
        return None
        
    except Exception as e:
        return None

@app.route('/')
def home():
    return jsonify({'message': 'Search Engine API is running', 'websites': len(WEBSITES)})

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({
            'error': 'Query too short',
            'results': []
        }), 400
    
    # Fetch all websites in parallel
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {
            executor.submit(fetch_and_search, url, query): url 
            for url in WEBSITES
        }
        
        for future in as_completed(future_to_url):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except:
                pass
    
    # Sort by relevance
    results.sort(key=lambda x: x['relevance'], reverse=True)
    
    return jsonify({
        'query': query,
        'results': results[:20],
        'count': len(results[:20])
    })

if __name__ == '__main__':
    print(f"Loaded {len(WEBSITES)} websites")
    app.run(host='0.0.0.0', port=5000)
