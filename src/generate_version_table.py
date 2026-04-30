#!/usr/bin/env python3
"""
Generate a version history YAML file from git tags and commit logs.

Each git tag defines a version boundary. Commits between consecutive tags
are grouped under the newer tag. Commits after the latest tag are grouped
under an "Unreleased" section.

Usage:
    python generate_version_table.py [--output versions.yml]
    python generate_version_table.py --max-commits 10 --exclude-pattern "^Merge"
"""

import argparse
import os
import re
import subprocess
import sys

import yaml


def _run_git(*args: str) -> str:
    """Run a git command and return stripped stdout. Returns '' on failure."""
    try:
        result = subprocess.run(
            ['git'] + list(args),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return ''
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ''


def is_git_repo() -> bool:
    """Check whether the current directory is inside a git work tree."""
    return _run_git('rev-parse', '--is-inside-work-tree') == 'true'


def get_tags_sorted() -> list[dict]:
    """Return tags sorted by tagged commit date (newest first).

    Each entry: {name, sha, date, author, message}
    """
    # %(*objectname) resolves annotated-tag → commit SHA; empty for lightweight
    raw = _run_git(
        'tag', '-l',
        '--format=%(refname:short)\t%(objectname:short)\t%(*objectname:short)\t%(creatordate:short)\t%(taggername)\t%(contents:subject)',
    )
    if not raw:
        return []

    tags = []
    for line in raw.splitlines():
        parts = line.split('\t', 5)
        if len(parts) < 6:
            continue
        name, tag_sha, commit_sha, date, author, message = parts
        # For lightweight tags *objectname is empty; use tag SHA directly
        resolved_sha = commit_sha if commit_sha else tag_sha
        tags.append({
            'name': name,
            'sha': resolved_sha,
            'date': date.strip(),
            'author': author.strip() or _commit_author(resolved_sha),
            'message': message.strip(),
        })

    # Sort by the commit timestamp the tag points to (newest first)
    # This is critical when tags are created retroactively.
    for tag in tags:
        ts = _run_git('log', '-1', '--format=%ct', tag['sha'])
        tag['_commit_ts'] = int(ts) if ts.isdigit() else 0
        # Also use the commit date rather than the tag creation date
        commit_date = _run_git('log', '-1', '--format=%as', tag['sha'])
        if commit_date:
            tag['date'] = commit_date

    tags.sort(key=lambda t: t['_commit_ts'], reverse=True)
    return tags


def _commit_author(sha: str) -> str:
    """Get the author name for a commit SHA."""
    return _run_git('log', '-1', '--format=%an', sha)


def get_commits_between(older_ref: str, newer_ref: str,
                        exclude_pattern: str | None = None) -> list[str]:
    """Return list of commit subject lines between two refs (older exclusive)."""
    range_spec = f'{older_ref}..{newer_ref}' if older_ref else newer_ref
    raw = _run_git('log', range_spec, '--format=%s')
    if not raw:
        return []
    commits = raw.splitlines()
    if exclude_pattern:
        pat = re.compile(exclude_pattern)
        commits = [c for c in commits if not pat.search(c)]
    return commits


def get_all_commits(exclude_pattern: str | None = None) -> list[str]:
    """Return all commit subjects on current branch."""
    raw = _run_git('log', '--format=%s')
    if not raw:
        return []
    commits = raw.splitlines()
    if exclude_pattern:
        pat = re.compile(exclude_pattern)
        commits = [c for c in commits if not pat.search(c)]
    return commits


def get_head_sha() -> str:
    return _run_git('rev-parse', '--short', 'HEAD')


def get_head_date() -> str:
    return _run_git('log', '-1', '--format=%as')


def build_version_table(
    max_commits: int = 20,
    exclude_pattern: str | None = None,
    include_unreleased: bool = True,
) -> list[dict]:
    """Build version table entries from git tags + commit log.

    Returns a list of dicts:
        [{version, date, author, changes: [str, ...]}, ...]
    """
    tags = get_tags_sorted()
    entries = []

    if not tags:
        # No tags at all — single "Unreleased" block
        commits = get_all_commits(exclude_pattern)
        if commits:
            changes = commits[:max_commits]
            if len(commits) > max_commits:
                changes.append(f'… and {len(commits) - max_commits} more')
            entries.append({
                'version': 'Unreleased',
                'date': get_head_date(),
                'author': _commit_author(get_head_sha()),
                'changes': changes,
            })
        return entries

    # Unreleased: HEAD → latest tag
    if include_unreleased:
        unreleased = get_commits_between(tags[0]['sha'], 'HEAD', exclude_pattern)
        if unreleased:
            changes = unreleased[:max_commits]
            if len(unreleased) > max_commits:
                changes.append(f'… and {len(unreleased) - max_commits} more')
            entries.append({
                'version': 'Unreleased',
                'date': get_head_date(),
                'author': '—',
                'changes': changes,
            })

    # Tagged versions: each pair of consecutive tags
    for i, tag in enumerate(tags):
        older_ref = tags[i + 1]['sha'] if i + 1 < len(tags) else ''
        commits = get_commits_between(older_ref, tag['sha'], exclude_pattern)
        changes = commits[:max_commits]
        if len(commits) > max_commits:
            changes.append(f'… and {len(commits) - max_commits} more')

        # Use tag annotation as a summary line if available
        if tag['message'] and tag['message'] not in changes:
            changes.insert(0, tag['message'])

        entries.append({
            'version': tag['name'],
            'date': tag['date'],
            'author': tag['author'],
            'changes': changes if changes else ['No changes recorded'],
        })

    return entries


def write_version_table(entries: list[dict], output: str | None = None) -> str:
    """Write entries to a YAML file. Returns the YAML string."""
    data = {'versions': entries}
    yml = yaml.dump(data, default_flow_style=False, allow_unicode=True,
                    sort_keys=False, width=120)
    if output:
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w') as f:
            f.write(yml)
    return yml


def main():
    parser = argparse.ArgumentParser(
        description='Generate version history YAML from git tags and commits')
    parser.add_argument('--output', '-o', default=None,
                        help='Output YAML file path (default: stdout)')
    parser.add_argument('--max-commits', type=int, default=20,
                        help='Max commit entries per version (default: 20)')
    parser.add_argument('--exclude-pattern', default=None,
                        help='Regex pattern to exclude commits (e.g. "^Merge")')
    parser.add_argument('--no-unreleased', action='store_true',
                        help='Exclude unreleased commits section')
    args = parser.parse_args()

    if not is_git_repo():
        print('Error: not inside a git repository.', file=sys.stderr)
        sys.exit(1)

    entries = build_version_table(
        max_commits=args.max_commits,
        exclude_pattern=args.exclude_pattern,
        include_unreleased=not args.no_unreleased,
    )

    if not entries:
        print('Warning: no version entries found.', file=sys.stderr)
        sys.exit(0)

    yml = write_version_table(entries, args.output)

    if args.output:
        print(f'Wrote {len(entries)} version(s) to {args.output}')
    else:
        print(yml)


if __name__ == '__main__':
    main()
