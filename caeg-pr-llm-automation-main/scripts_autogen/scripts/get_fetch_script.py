import os
import sys
import logging
import requests


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def get_head_commit_from_pr(token, repo_url, pr_number):
    owner, repo = repo_url.split("/")
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    base_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'
    try:
        url = base_url
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()  # Raise an exception for non-200 status codes

        data = response.json()
        return data['head']['sha']  # Extract the head commit SHA
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pull request information: {e}")
        return None
    
def fetch_repo(token, repo_owner, pr_number, directory="/app/repo"):

    repo_url = f"https://{token}@github.com/{repo_owner}.git"

    logger.info(f"Getting the base_commit from {repo_owner} for PR number {pr_number}")
    base_commit = get_head_commit_from_pr(token, repo_owner, pr_number)

    logger.info(f"Base commit for PR {pr_number}: {base_commit}")

    logger.info(f"Setting up repository from {repo_url} into {directory}")

    # Change to the target directory
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    os.chdir(directory)

    # Initialize a new Git repository
    result = os.system("git init")
    if result != 0:
        logger.error("Failed to initialize a new Git repository")
        sys.exit(1)

    # Add the remote repository
    result = os.system(f"git remote add origin {repo_url}")
    if result != 0:
        logger.error("Failed to add remote repository")
        sys.exit(1)

    # Fetch the specified commit
    result = os.system(f"git fetch --depth 1 origin {base_commit}")
    if result != 0:
        logger.error("Failed to fetch the specified commit")
        sys.exit(1)

    # Check out the fetched commit
    result = os.system("git checkout FETCH_HEAD")
    if result != 0:
        logger.error("Failed to check out the fetched commit")
        sys.exit(1)

    logger.info("Repository setup completed successfully")
