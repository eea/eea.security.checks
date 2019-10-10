import json
import os
import sys
import time
import logging
import argparse
from redminelib import Redmine
from settings import API_KEY
from constants import *


def write_page(content):
    server = Redmine(redmineServer, key=API_KEY, requests={'verify': True})

    server.wiki_page.update(
        redminePageName, project_id=redmineProjectName, text=content)


def write_stdout(content):
    # pass
    print(content)


def write_content():
    header = create_page_header()
    body = create_page_body()

    content = header + body

    if args.dryrun:
        write_stdout("\n".join(content))
    else:
        write_page("\n".join(content))


def create_page_header():
    header = []
    header.append('h1. ' + redminePageTitle + '\n\n')
    header.append('Automatically discovered on ' + time.strftime('%d %B %Y'))
    header.append('\n{{>TOC}}\n')

    return header


def create_page_body():
    body = []

    with open(report_file) as json_report:
        report = json.load(json_report)

        for repo in report:
            repo_url = "https://github.com/eea/" + repo

            logging.info(f"Posting on repo {repo}")

            body.append('\nh2. "{}":{}\n'.format(repo, repo_url))
            body.append(
                '|_. Package |_. Current Version |_. Affected Versions |')

            for security_issue in report[repo]:
                package_name = security_issue[PACKAGE_NAME]
                affected_versions = security_issue[AFFECTED_VERSIONS]
                current_version = security_issue[CURRENT_VERSION]

                body.append('| {} | {} | {} |'.format(
                    package_name, current_version, affected_versions))

    return body


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-n', '--dryrun', action='store_true')

    args = parser.parse_args()

    loggingLevel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loggingLevel)

    write_content()
