#!/usr/bin/env python3
"""Batched InfoJobs scraper using requests with retries and incremental saves.
Usage: python infojobs_batched.py --output data/infojobs_batched.json --pages 15
"""
import argparse
import json
import time
import os
import sys

# ensure scrapers package files are importable when running script from project root
sys.path.insert(0, os.path.dirname(__file__))
from infojobs_scraper import fetch_page, extract_initial_props, parse_offer, find_job_cards, parse_job_card, normalize_job, BASE_URL, SEARCH_PATH


def scrape_pages_incremental(output, pages=10, delay=1.0, retries=2):
    seen = set()
    results = []
    # load existing
    if os.path.exists(output):
        try:
            with open(output, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                for e in existing:
                    seen.add(e.get('id'))
                results.extend(existing)
        except Exception:
            pass

    for p in range(1, pages + 1):
        attempt = 0
        page_jobs = []
        while attempt <= retries:
            try:
                print(f'Fetching page {p} (attempt {attempt + 1})')
                url = f'{BASE_URL}{SEARCH_PATH}?page={p}'
                html = fetch_page(url)
                props = extract_initial_props(html)
                if props and isinstance(props, dict):
                    offers = props.get('offers') or []
                    for o in offers:
                        page_jobs.append(normalize_job(parse_offer(o)))
                if not page_jobs:
                    # fallback to HTML parsing
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    cards = find_job_cards(soup)
                    for card in cards:
                        item = parse_job_card(card)
                        if item:
                            page_jobs.append(normalize_job(item))
                break
            except Exception as e:
                print(f'Error fetching page {p}: {e}')
                attempt += 1
                time.sleep(1 + attempt)
        # normalize and dedupe
        added = 0
        for job in page_jobs:
            jid = job.get('id') or job.get('url')
            if jid and jid not in seen:
                seen.add(jid)
                results.append(job)
                added += 1
        # write incrementally
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f'Page {p} done, added {added} offers, total {len(results)}')
        time.sleep(delay)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/infojobs_batched.json')
    parser.add_argument('--pages', type=int, default=10)
    args = parser.parse_args()
    scrape_pages_incremental(args.output, pages=args.pages)
