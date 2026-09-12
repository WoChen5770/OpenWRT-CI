#!/usr/bin/env python3
"""Resolve official release metadata into a versioned, hash-checked OpenWrt recipe."""
import json
from pathlib import Path
import re
import sys
from datetime import datetime


def render(releases, template):
    if not isinstance(releases, list) or not releases:
        raise ValueError('GitHub returned no release list')
    published = [r for r in releases if not r.get('draft') and r.get('published_at')]
    if not published:
        raise ValueError('No published Xray release found')
    # Include prereleases; /releases/latest would exclude them.
    release = max(published, key=lambda r: datetime.fromisoformat(
        r['published_at'].replace('Z', '+00:00')))
    tag = release.get('tag_name', '')
    match = re.fullmatch(r'v([0-9]+\.[0-9]+\.[0-9]+)', tag)
    if not match:
        raise ValueError(f'Unsupported latest release tag: {tag!r}')
    assets = [a for a in release.get('assets', []) if a.get('name') == 'Xray-linux-64.zip']
    if len(assets) != 1 or assets[0].get('state') != 'uploaded':
        raise ValueError(f'{tag}: official x86-64 ZIP is missing or not ready')
    asset = assets[0]
    url = f'https://github.com/XTLS/Xray-core/releases/download/{tag}/Xray-linux-64.zip'
    if asset.get('browser_download_url') != url:
        raise ValueError(f'{tag}: unexpected download URL')
    digest = re.fullmatch(r'sha256:([0-9a-fA-F]{64})', asset.get('digest') or '')
    if not digest:
        raise ValueError(f'{tag}: official SHA256 missing; refusing unchecked download')
    for placeholder in ('@XRAY_VERSION@', '@XRAY_SHA256@'):
        if template.count(placeholder) != 1:
            raise ValueError(f'Missing or duplicate template placeholder: {placeholder}')
    result = template.replace('@XRAY_VERSION@', match[1]).replace('@XRAY_SHA256@', digest[1].lower())
    return result, release


def main():
    try:
        metadata, template, output = map(Path, sys.argv[1:])
        result, release = render(json.loads(metadata.read_text()), template.read_text())
        output.write_text(result)
        print(f"Xray selected: {release['tag_name']}, published={release['published_at']}, "
              f"prerelease={release.get('prerelease', False)}")
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        print(f'Xray release resolution failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
