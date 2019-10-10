import json
import os
import sys
import time
import getopt
import logging
from redminelib import Redmine
from settings import API_KEY

input_file = "report.json"

PACKAGE_NAME = 0
AFFECTED_VERSIONS = 1
CURRENT_VERSION = 2


def write_page(content):
    server = 'https://helpdesk.eaudeweb.ro'
    apikey = API_KEY
    projectName = 'interne'
    pageName = 'eea repos - security issues'
    server = Redmine(server, key=apikey, requests={'verify': True})

    server.wiki_page.update(pageName, project_id=projectName, text=content)


def write_stdout(content):
    # pass
    print(content)


if __name__ == '__main__':
    dryrun = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "vn")
    except getopt.GetoptError as err:
        sys.exit(2)

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    for o, a in opts:
        if o == "-v":
            logging.basicConfig(
                format='%(levelname)s:%(message)s', level=logging.DEBUG)
        if o == "-n":
            dryrun = True

    pageTitle = 'EEA REPOS SECURITY ISSUES'

    content = []
    content.append('h1. ' + pageTitle + '\n\n')
    content.append('Automatically discovered on ' +
                   time.strftime('%d %B %Y') + '. _Do not update this page manually._')
    content.append('\n{{>TOC}}\n')

    with open(input_file) as json_report:
        report = json.load(json_report)

        for repo in report:
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

    if dryrun:
        write_stdout("\n".join(content))
    else:
        write_page("\n".join(content))
