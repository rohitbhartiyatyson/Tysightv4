import os
import sys
import json
import argparse
import requests
from urllib.parse import urlparse

TIMEOUT = 15

def repo_from_remote():
    # parse origin remote URL
    try:
        import subprocess
        out = subprocess.check_output(['git','remote','get-url','origin'], text=True).strip()
    except Exception:
        return None
    # handle formats https://github.com/owner/repo.git or https://token@github.com/owner/repo.git
    if out.startswith('http'):
        p = urlparse(out)
        path = p.path.lstrip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path
    # git@github.com:owner/repo.git
    if out.startswith('git@'):
        parts = out.split(':',1)
        if len(parts)==2:
            path = parts[1]
            if path.endswith('.git'):
                path = path[:-4]
            return path
    return None


def gh_request(method, endpoint, data=None, params=None):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print(json.dumps({'error':'no_token'}))
        sys.exit(1)
    repo = repo_from_remote()
    if not repo:
        print(json.dumps({'error':'no_repo'}))
        sys.exit(1)
    url = f"https://api.github.com/repos/{repo}{endpoint}"
    headers = {'Authorization': f'token {token}','Accept':'application/vnd.github+json'}
    resp = requests.request(method, url, json=data, params=params, headers=headers, timeout=TIMEOUT)
    out = {'status_code': resp.status_code, 'ok': resp.ok}
    try:
        out['json'] = resp.json()
    except Exception:
        out['text'] = resp.text
    return out


def cmd_create_pr(args):
    data = {
        'title': args.title,
        'head': args.source,
        'base': args.target,
        'body': args.body or ''
    }
    r = gh_request('POST', '/pulls', data=data)
    Path = 'runs/oh_gh_create_pr.json'
    os.makedirs('runs', exist_ok=True)
    with open(Path,'w') as f:
        json.dump(r, f, indent=2)
    print(json.dumps(r.get('json') or r, indent=2))


def cmd_get_prs(args):
    params = {'head': f"{args.owner}:{args.head}"} if args.owner else {'head': args.head}
    r = gh_request('GET', '/pulls', params=params)
    os.makedirs('runs', exist_ok=True)
    with open('runs/oh_gh_list_prs.json','w') as f:
        json.dump(r, f, indent=2)
    print(json.dumps(r.get('json') or r, indent=2))


def cmd_get_pr(args):
    r = gh_request('GET', f"/pulls/{args.number}")
    os.makedirs('runs', exist_ok=True)
    with open('runs/oh_gh_get_pr.json','w') as f:
        json.dump(r, f, indent=2)
    print(json.dumps(r.get('json') or r, indent=2))


def cmd_merge_pr(args):
    data = {'merge_method': args.method}
    r = gh_request('PUT', f"/pulls/{args.number}/merge", data=data)
    os.makedirs('runs', exist_ok=True)
    with open('runs/oh_gh_merge_pr.json','w') as f:
        json.dump(r, f, indent=2)
    print(json.dumps(r.get('json') or r, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p = sub.add_parser('create_pr')
    p.add_argument('--source', required=True)
    p.add_argument('--target', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--body', required=False)

    p2 = sub.add_parser('get_pr')
    p2.add_argument('--number', type=int, required=True)

    p3 = sub.add_parser('list_prs')
    p3.add_argument('--head', required=True)
    p3.add_argument('--owner', required=False)

    p4 = sub.add_parser('merge_pr')
    p4.add_argument('--number', type=int, required=True)
    p4.add_argument('--method', choices=['merge','squash','rebase'], default='squash')

    args = parser.parse_args()
    if args.cmd == 'create_pr':
        cmd_create_pr(args)
    elif args.cmd == 'get_pr':
        cmd_get_pr(args)
    elif args.cmd == 'list_prs':
        cmd_get_prs(args)
    elif args.cmd == 'merge_pr':
        cmd_merge_pr(args)
    else:
        parser.print_help()
