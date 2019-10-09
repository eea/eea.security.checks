import json
import time
import requests
import subprocess

from settings import TOKEN

PER_PAGE = 100

headers = {'Authorization': f'token {TOKEN}'}

full_report = {}

python_repos_no_req = 0

python_repos_with_req = []

python_repos_failed = []

with open("python_repos.txt") as f:
    for repo in f:
        repo = repo.strip()
        
        print(f"Safety checking {repo}...")
        search_repo_url = (
            f"https://api.github.com/search/code?q=+repo:"
            f"eea/{repo}+filename:requirements.txt"
        )

        results = requests.get(
            search_repo_url, params={'page': 1, 'per_page': PER_PAGE},
            headers=headers
        )

        # Github API limit: 30 requests/minute
        time.sleep(2)

        if results.status_code != 200 or int(results.headers['X-RateLimit-Remaining']) < 1:
            # Remaining rate limit should be greater than 1, as a new request will be
            # made to the repo to extract the requirements.txt content

            print(results.status_code)
            continue

            print("API limit reached. Waiting for an hour.")
            time.sleep(3601)
            results = requests.get(
                search_repo_url, params={'page': 1, 'per_page': PER_PAGE},
                headers=headers
            )

            if results.status_code != 200:
                # If second try did not work, stop
                python_repos_failed.append(repo)
                continue

        items = results.json()['items']
        
        if not items:
            python_repos_no_req += 1
            print(f"Couldn't find a requirements file for repo {repo}.")
        else:
            python_repos_with_req.append(repo)

        vulnerable_pkgs = []
        for result in items:
            if result['name'] == 'requirements.txt':
                requirements_url = result['html_url'].replace(
                    'https://github.com/',
                    'https://raw.githubusercontent.com/'
                )
                requirements_url = requirements_url.replace('/blob', '')
                resp = requests.get(requirements_url, headers=headers)
                requirements = resp.text
                
                for requirement in requirements.splitlines():
                    if '==' in requirement:
                        task = subprocess.Popen(
                            f"echo {requirement} | safety check --stdin --json",
                            shell=True, stdout=subprocess.PIPE
                        )

                        req_vulnerability = json.loads((task.communicate()[0]).decode())
                        if (req_vulnerability):
                            vulnerable_pkgs.append(req_vulnerability[0])
                
                print(f"Found {len(vulnerable_pkgs)} vulnerabilities in repo {repo}.")
                if vulnerable_pkgs:
                    full_report[repo] = vulnerable_pkgs

print("=== FINISHED PROCESSING ===")
print(f"{python_repos_no_req} Python repos with no requirement files.")
print(
    f"Python repos we couldn't analyze because of API errors: "
    f"{python_repos_failed}"
)
print(f"Python repos with requirements: {python_repos_with_req}")

print("=== FULL REPORT ===")
report_content = json.dumps(full_report, indent=4)
print(report_content)
with open("report.json","w+") as f:
    f.write(report_content)
