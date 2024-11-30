import os
import logging
import subprocess

from git_fetch_script import fetch_repo

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

if __name__ == "__main__":
    
    logger.info("Starting run.py")

    token = os.getenv("token")
    pr_number = os.getenv("pr_number")
    api_key = os.getenv("api_key")
    repo_owner = os.getenv("repo_owner")
    dir_to_clone = "/app/repo"

    fetch_repo(token, repo_owner, pr_number, dir_to_clone)
    
    autogen_path = '/app/autogen_run.py'
    subprocess.run(['python', autogen_path])
