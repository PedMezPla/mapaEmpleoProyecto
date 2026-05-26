#!/usr/bin/env python3
import argparse
import json
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://www.infojobs.net'
SEARCH_PATH = '/jobsearch/search-results/list.xhtml'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Referer': 'https://www.infojobs.net',
    'Connection': 'keep-alive'
}

JOB_CARD_SELECTORS = [
    'article[data-offer-id]',
    'article[id^="offer-"]',
    '.offer-card',
    '.job-card',
    '.result-item'
]


def normalize_job(raw):
    return {
        'id': raw.get('id') or raw.get('url'),
        'title': raw.get('title') or '',
        'company': raw.get('company') or '',
        'location': raw.get('location') or '',
        'province': raw.get('province') or '',
        'community': raw.get('community') or '',
        'category': raw.get('category') or '',
        'type': raw.get('type') or 'all',
        'portal': 'InfoJobs',
        'status': raw.get('status', 'active'),
        'lat': raw.get('lat'),
        'lng': raw.get('lng'),
        'url': raw.get('url') or '',
        'updated_at': raw.get('updated_at') or datetime.utcnow().isoformat()
    }


def build_url(link):
    if not link:
        return ''
    if link.startswith('//'):
        return 'https:' + link
    if link.startswith('http'):
        return link
    if link.startswith('/'):
        return urljoin(BASE_URL, link)
    return urljoin(BASE_URL + '/', link)


def fetch_page(url, session=None):
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)
    response = session.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def extract_json_payload(script_text, variable_name='window.__INITIAL_PROPS__'):
    marker = f'{variable_name} = JSON.parse("'
    start = script_text.find(marker)
    if start == -1:
        return None
    start += len(marker)
    raw_chars = []
    escaped = False
    while start < len(script_text):
        c = script_text[start]
        if escaped:
            raw_chars.append(c)
            escaped = False
        elif c == '\\':
            raw_chars.append(c)
            escaped = True
        elif c == '"':
            break
        else:
            raw_chars.append(c)
        start += 1
    raw = ''.join(raw_chars)
    decoded = json.loads(f'"{raw}"')
    return json.loads(decoded)


def extract_initial_props(html):
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup.find_all('script'):
        content = script.string
        if not content:
            continue
        if 'window.__INITIAL_PROPS__' in content:
            try:
                return extract_json_payload(content)
            except Exception:
                continue
    return None


def detect_type(teleworking, workday):
    text = ' '.join(filter(None, [teleworking, workday])).lower()
    if 'remoto' in text or 'teletrabajo' in text:
        return 'remote'
    if 'híbrido' in text or 'hibrido' in text:
        return 'hybrid'
    return 'onsite'


def parse_offer(offer):
    url = build_url(offer.get('link') or offer.get('companyLink') or '')
    return {
        'id': offer.get('code') or url,
        'title': offer.get('title') or '',
        'company': offer.get('companyName') or '',
        'location': offer.get('city') or '',
        'province': '',
        'community': '',
        'category': offer.get('category', '') or '',
        'type': detect_type(offer.get('teleworking', ''), offer.get('workday', '')),
        'portal': 'InfoJobs',
        'status': 'active',
        'lat': None,
        'lng': None,
        'url': url,
        'updated_at': offer.get('publishedAt') or datetime.utcnow().isoformat()
    }


def parse_location(raw_location):
    if not raw_location:
        return '', '', ''
    text = raw_location.strip()
    pieces = [part.strip() for part in text.split(',') if part.strip()]
    if not pieces:
        return text, '', ''
    province = pieces[0]
    community = ''
    return text, province, community


def clean_text(element):
    return element.get_text(strip=True) if element else ''


def find_job_cards(soup):
    for selector in JOB_CARD_SELECTORS:
        cards = soup.select(selector)
        if cards:
            return cards
    return []


def parse_job_card(card):
    link = card.select_one('a[href]')
    if not link:
        return None
    title = clean_text(card.select_one('h2')) or clean_text(card.select_one('a'))
    company = clean_text(card.select_one('.company-name')) or clean_text(card.select_one('.offer-company'))
    location_text = clean_text(card.select_one('.location')) or clean_text(card.select_one('.location-text'))
    location, province, community = parse_location(location_text)
    job_type = detect_type(card)
    category = ''
    url = build_url(link['href'])
    return {
        'id': url,
        'title': title,
        'company': company,
        'location': location,
        'province': province,
        'community': community,
        'category': category,
        'type': job_type,
        'url': url
    }


def scrape_infojobs(max_pages=2):
    jobs = []
    session = requests.Session()
    session.headers.update(HEADERS)
    for page in range(1, max_pages + 1):
        url = f'{BASE_URL}{SEARCH_PATH}?page={page}'
        print(f'Scraping {url}')
        html = fetch_page(url, session=session)
        payload = extract_initial_props(html)
        page_jobs = []
        if payload and isinstance(payload, dict):
            offers = payload.get('offers') or []
            if offers:
                for offer in offers:
                    page_jobs.append(normalize_job(parse_offer(offer)))
            else:
                print('No offers found in __INITIAL_PROPS__, intentando parseo de HTML.')
        else:
            print('No se pudo extraer __INITIAL_PROPS__, intentando parseo de HTML.')
        if not page_jobs:
            soup = BeautifulSoup(html, 'html.parser')
            cards = find_job_cards(soup)
            if not cards:
                print('No se han encontrado tarjetas en la página, revisa los selectores de parseo.')
            for card in cards:
                item = parse_job_card(card)
                if item:
                    page_jobs.append(normalize_job(item))
        jobs.extend(page_jobs)
        time.sleep(1)
    return jobs


def main(output_path, max_pages):
    jobs = scrape_infojobs(max_pages=max_pages)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f'InfoJobs scraped {len(jobs)} offers into {output_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape InfoJobs job offers')
    parser.add_argument('--output', default='data/infojobs.json')
    parser.add_argument('--pages', type=int, default=2)
    args = parser.parse_args()
    main(args.output, args.pages)
