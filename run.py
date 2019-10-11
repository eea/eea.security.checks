import json
import time
import logging
import argparse
import requests
import subprocess
from redminelib import Redmine

from settings import TOKEN, API_KEY
from constants import *

args = None


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

    if response.headers and response.headers.get('X-RateLimit-Remaining', None):
        # Remaining rate limit should be greater than 1, as a new request will be
        # made to the repo to extract the requirements.txt content
        return int(response.headers['X-RateLimit-Remaining']) < 2

    return False


def vulnerable_requirement(requirement):
    if "==" in requirement:
        task = subprocess.Popen(
            "safety check --stdin --json", stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )

        task.stdin.write(requirement.encode())

        req_vulnerability = json.loads((task.communicate()[0]).decode())
        task.stdin.close()

        return req_vulnerability[0] if req_vulnerability else None
    return None


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
    repos_summary = {
        'no_req': [],
        'with_req': [],
        'failed': []
    }

    repos_with_issues = {}

    with open(repos_file) as f:
        for repo in f:
            repo = repo.strip()

            # Github API limit: 30 requests/minute
            results = make_request(get_repo_url(repo), git_api_params)
            time.sleep(2)

            if api_limit_reached(results):

                logging.info("API limit reached. Waiting for an hour.")
                time.sleep(3601)
                results = make_request(get_repo_url(repo), git_api_params)

                if not results.ok:
                    # If second try did not work, stop
                    repos_summary['failed'].append(repo)
                    continue

            repo_items = results.json()['items']

            if not repo_items:
                logging.info(f"No requirements file in {repo}")
                repos_summary['no_req'].append(repo)
            else:
                repos_summary['with_req'].append(repo)

                vulnerable_pkgs = repo_vulnerable_packages(repo, repo_items)
                if vulnerable_pkgs:
                    repos_with_issues[repo] = vulnerable_pkgs

    return repos_summary, repos_with_issues


def create_redmine_content(report):
    content = []
    content.append('h1. ' + redminePageTitle + '\n\n')
    content.append('Automatically discovered on ' + time.strftime('%d %B %Y'))
    content.append('\n{{>TOC}}\n')

    report = json.loads(report)
    for repo in report:
        repo = repo.strip()
        repo_url = "https://github.com/eea/" + repo

        logging.info(f"Posting on repo {repo}")

        content.append('\nh2. "{}":{}\n'.format(repo, repo_url))
        content.append(
            '|_. Package |_. Current Version |_. Affected Versions |')

        for security_issue in report[repo]:
            package_name = security_issue[PACKAGE_NAME]
            affected_versions = security_issue[AFFECTED_VERSIONS]
            current_version = security_issue[CURRENT_VERSION]

            content.append('| {} | {} | {} |'.format(
                package_name, current_version, affected_versions))

    return content


def create_save_report(report_file, summary, with_issues):
    logging.info("=== FINISHED PROCESSING ===")
    logging.info(
        f"Python repos with no requirement files: "
        f"{summary['no_req']}")
    logging.info(
        f"Python repos we couldn't analyze because of API errors: "
        f"{summary['failed']}"
    )
    logging.info(
        f"Python repos with requirements: "
        f"{summary['with_req']}"
    )

    print("=== FULL REPORT ===")
    logging.info(
        f"Python repos with issues: "
        f"{with_issues}"
    )

    report_content = json.dumps(with_issues, indent=4)
    if args.save_report:
        with open(report_file, "w") as f:
            f.write(report_content)

    return report_content


def write_page(content):
    server = Redmine(redmineServer, key=API_KEY, requests={'verify': True})

    server.wiki_page.update(
        redminePageName, project_id=redmineProjectName, text=content)


def write_stdout(content):
    # pass
    print(content)


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-n', '--dryrun', action='store_true')
    parser.add_argument('-s', '--save_report', action='store_true')

    args = parser.parse_args()

    loggingLevel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loggingLevel)

    summary, with_issues = check_repos(python_repos_file)
    report = create_save_report(report_file, summary, with_issues)
    redmine_content = create_redmine_content(report)

    if args.dryrun:
        write_stdout("\n".join(redmine_content))
    else:
        write_page("\n".join(redmine_content))


if __name__ == '__main__':
    main()
