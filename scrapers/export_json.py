#!/usr/bin/env python3
import argparse
import json
import hashlib
import unicodedata
from datetime import datetime
from pathlib import Path


COMMUNITY_ALIAS = {
    'Comunidad Valenciana': 'C. Valenciana'
}


def slugify(value):
    value = unicodedata.normalize('NFKD', value)
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = ''.join(ch if ch.isalnum() else '-' for ch in value)
    value = value.replace('--', '-')
    while '--' in value:
        value = value.replace('--', '-')
    return value.strip('-') or 'sin-region'


def normalize_job(raw):
    job_id = raw.get('id') or hashlib.sha256((raw.get('url', '') + raw.get('title', '')).encode('utf-8')).hexdigest()
    return {
        'id': job_id,
        'title': raw.get('title') or '',
        'company': raw.get('company') or '',
        'location': raw.get('location') or '',
        'province': raw.get('province') or '',
        'community': raw.get('community') or '',
        'category': raw.get('category') or '',
        'type': raw.get('type') or 'all',
        'portal': raw.get('portal') or 'unknown',
        'status': raw.get('status') or 'active',
        'lat': raw.get('lat'),
        'lng': raw.get('lng'),
        'url': raw.get('url') or '',
        'updated_at': raw.get('updated_at') or datetime.utcnow().isoformat()
    }


def merge_sources(source_paths):
    merged = {}
    for path in source_paths:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        for raw in data:
            job = normalize_job(raw)
            merged[job['id']] = job
    return list(merged.values())


def write_community_files(jobs, output_dir):
    communities = {}
    for job in jobs:
        community = job.get('community') or job.get('province') or 'Sin región'
        communities.setdefault(community, []).append(job)

    index = []
    seen_slugs = set()

    for community_name, community_jobs in sorted(communities.items(), key=lambda x: x[0]):
        slug = slugify(community_name)
        original_slug = slug
        suffix = 1
        while slug in seen_slugs:
            slug = f'{original_slug}-{suffix}'
            suffix += 1
        seen_slugs.add(slug)

        community_file = output_dir / 'jobs' / f'{slug}.json'
        community_file.parent.mkdir(parents=True, exist_ok=True)
        community_file.write_text(json.dumps(community_jobs, ensure_ascii=False, indent=2), encoding='utf-8')

        index.append({
            'name': COMMUNITY_ALIAS.get(community_name, community_name),
            'slug': slug,
            'path': f'jobs/{slug}.json'
        })

    return index


def main(output_path, source_paths):
    jobs = merge_sources(source_paths)
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')

    communities_index = write_community_files(jobs, output_dir)
    Path(output_dir / 'communities.json').write_text(
        json.dumps(communities_index, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    print(f'Exported {len(jobs)} normalized jobs to {output_path}')
    print(f"Generated {len(communities_index)} community files in {output_dir / 'jobs'}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge and normalize job JSON sources')
    parser.add_argument('--output', default='public/jobs.json')
    parser.add_argument('--sources', nargs='+', required=True)
    args = parser.parse_args()
    main(args.output, args.sources)
