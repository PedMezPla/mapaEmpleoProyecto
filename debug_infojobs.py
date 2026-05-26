import re
import json
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}
resp = requests.get('https://www.infojobs.net/jobsearch/search-results/list.xhtml', headers=headers, timeout=20)
html = resp.text
pattern = r'window\.__INITIAL_PROPS__\s*=\s*JSON\.parse\("(?P<json>.*?)"\)'
match = re.search(pattern, html, flags=re.S)
print('match', bool(match))
if not match:
    raise SystemExit('no match')
json_text = match.group('json')
# unescape JSON string
json_text = json_text.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
obj = json.loads(json_text)
print('root keys:', list(obj.keys()))

found = []

def search(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            lower = k.lower()
            if any(token in lower for token in ('offer', 'job', 'result', 'hit', 'item', 'list', 'jobs', 'offers')):
                found.append((path + '.' + k, type(v).__name__))
            search(v, path + '.' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o[:5]):
            search(v, f'{path}[{i}]')

search(obj, 'root')
for item in found[:100]:
    print(item)
print('total found', len(found))
