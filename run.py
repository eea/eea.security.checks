import json
import time
import logging
import requests
import subprocess

from settings import TOKEN
from constants import *


def get_repo_url(repo):
    repo = repo.strip()

    logging.info(f"Safety checking {repo}...")
    search_repo_url = (
        f"https://api.github.com/search/code?q=+repo:"
        f"eea/{repo}+filename:requirements.txt"
    )

    return search_repo_url


def make_request(url, params=None):
    headers = {'Authorization': f'token {TOKEN}'}
    return requests.get(url, params=params, headers=headers)


def api_limit_reached(response):
    if not response.ok:
        return True

    if response.headers and response.headers['X-RateLimit-Remaining']:
        # Remaining rate limit should be greater than 1, as a new request will be
        # made to the repo to extract the requirements.txt content
        return int(response.headers['X-RateLimit-Remaining']) < 1

    return False


def vulnerable_requirement(requirement):
    if "==" in requirement:
        task = subprocess.Popen(
            f"echo {requirement} | safety check --stdin --json", shell=True, stdout=subprocess.PIPE
        )

        req_vulnerability = json.loads((task.communicate()[0]).decode())
        return req_vulnerability[0] if req_vulnerability else None
    return False


def repo_vulnerable_packages(repo, repo_items):

    vulnerable_pkgs = []
    for item in repo_items:
        if item['name'] == requirements_file:
            requirements_url = item['html_url'].replace(
                'https://github.com/',
                'https://raw.githubusercontent.com/'
            )
            requirements_url = requirements_url.replace('/blob', '')
            requirements = (requests.get(requirements_url)).text

            for requirement in requirements.splitlines():
                vulnerability = vulnerable_requirement(requirement)
                if vulnerability:
                    vulnerable_pkgs.append(vulnerability)

            logging.info(
                f"Found {len(vulnerable_pkgs)} vulnerabilities in repo {repo}.")

            return vulnerable_pkgs


def check_repos(repos_file):
    python_repos_no_req = []
    python_repos_with_req = []
    python_repos_failed = []
    python_repos_with_issues = {}

    with open(repos_file) as f:
        for repo in f:

            # Github API limit: 30 requests/minute
            results = make_request(get_repo_url(repo), git_api_params)
            time.sleep(2)

            if api_limit_reached(results):

                logging.info("API limit reached. Waiting for an hour.")
                time.sleep(3601)
                results = make_request(get_repo_url(repo), git_api_params)

                if not results.ok:
                    # If second try did not work, stop
                    python_repos_failed.append(repo)
                    continue

            repo_items = results.json()['items']

            if not repo_items:
                logging.info(f"No requirements file in {repo}")
                python_repos_no_req.append(repo)
            else:
                python_repos_with_req.append(repo)

                vulnerable_pkgs = repo_vulnerable_packages(repo, repo_items)
                if vulnerable_pkgs:
                    python_repos_with_issues[repo] = vulnerable_pkgs

    return python_repos_no_req, python_repos_with_req, python_repos_failed, python_repos_with_issues


def save_report(report_file, no_req, with_req, failed, with_issues):
    logging.info("=== FINISHED PROCESSING ===")
    logging.info(
        f"Python repos with no requirement files: "
        f"{no_req}")
    logging.info(
        f"Python repos we couldn't analyze because of API errors: "
        f"{failed}"
    )
    logging.info(
        f"Python repos with requirements: "
        f"{with_req}"
    )

    print("=== FULL REPORT ===")
    report_content = json.dumps(with_issues, indent=4)
    logging.info(with_issues)
    with open(report_file, "w+") as f:
        f.write(report_content)


def main():
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    no_req, with_req, failed, with_issues = check_repos(python_repos_file)
    save_report(report_file, no_req, with_req, failed, with_issues)


if __name__ == '__main__':
    main()
