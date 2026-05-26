#!/usr/bin/env python3
import argparse
import json
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}


def normalize_job(raw, portal_name):
    return {
        'id': raw.get('id') or raw.get('url'),
        'title': raw.get('title'),
        'company': raw.get('company'),
        'location': raw.get('location'),
        'province': raw.get('province'),
        'community': raw.get('community'),
        'category': raw.get('category'),
        'type': raw.get('type'),
        'portal': portal_name,
        'status': raw.get('status', 'active'),
        'lat': raw.get('lat'),
        'lng': raw.get('lng'),
        'url': raw.get('url'),
        'updated_at': raw.get('updated_at') or datetime.utcnow().isoformat()
    }


def fetch_page(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')


def scrape_portal(url, portal_name):
    print(f'Scraping {portal_name}: {url}')
    soup = fetch_page(url)
    cards = soup.select('.job-card, .offer-card, .result-item')
    jobs = []
    for card in cards:
        link = card.select_one('a[href]')
        if not link:
            continue
        title = card.select_one('.job-title')
        company = card.select_one('.company-name')
        jobs.append(normalize_job({
            'id': link.get('href'),
            'title': title.get_text(strip=True) if title else None,
            'company': company.get_text(strip=True) if company else None,
            'location': None,
            'province': None,
            'community': None,
            'category': None,
            'type': None,
            'url': link.get('href') if link.get('href').startswith('http') else url + link.get('href')
        }, portal_name))
    return jobs


def main(output_path, portal='Generic', url='https://www.example.com/jobs'):
    jobs = scrape_portal(url, portal)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f'Scraped {len(jobs)} offers for {portal} into {output_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape a generic job portal')
    parser.add_argument('--output', default='data/generic.json')
    parser.add_argument('--portal', default='Generic')
    parser.add_argument('--url', default='https://www.example.com/jobs')
    args = parser.parse_args()
    main(args.output, args.portal, args.url)
