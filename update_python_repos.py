import json
import requests
import subprocess

from settings import TOKEN
from constants import *


headers = {'Authorization': f'token {TOKEN}'}


def make_request(url, params, headers):
    return requests.get(url, params=params, headers=headers)


def get_python_repos():

    page = 1
    current_url = eea_repos
    python_repos = []

    while True:
        repos = make_request(
            current_url, {'page': page, 'per_page': PER_PAGE}, headers)

        if not repos.ok:
            break

        python_repos += [repo['name'] for repo in repos.json()
                         if repo['language'] == 'Python']

        if 'next' not in repos.links:
            break

        current_url = repos.links['next']['url']
        page += 1

    return python_repos


def write_repos(output_file, repo_names):
    with open(output_file, 'w') as f:
        f.write('\n'.join(repo_names))


def main():
    write_repos(python_repos_file, get_python_repos())


if __name__ == '__main__':
    main()
