import requests
import json
import os

class GitHubPR:
    def __init__(self, owner, repo, pr_number, token):
        self.owner = owner
        self.repo = repo
        self.pr_number = pr_number
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'
        
    def get_pr_files(self):
        url = f'{self.base_url}/files'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    def get_head_commit_from_pr(self):
        try:
            url = self.base_url
            response = requests.get(url=url, headers=self.headers)
            response.raise_for_status()  # Raise an exception for non-200 status codes

            data = response.json()
            return data['head']['sha']  # Extract the head commit SHA
        except requests.exceptions.RequestException as e:
            print(f"Error fetching pull request information: {e}")
            return None

def filter_files_include(files, extensions_to_include):
    return [file for file in files if any(file['filename'].endswith(ext) for ext in extensions_to_include)]

def main(repo_url_, pr_number_, token_):
    # repo_url = os.getenv('GITHUB_REPO')
    # pr_number = os.getenv('PR_NUMBER')
    # token = os.getenv('GITHUB_TOKEN')
    repo_url=repo_url_
    pr_number=pr_number_
    token=token_

    owner, repo = repo_url.split("/")
    
    github_pr = GitHubPR(owner, repo, pr_number, token)
    base_commit=github_pr.get_head_commit_from_pr()
    version = base_commit[:7]
    print(f"Repository URL: {repo_url}, Pull Request: #{pr_number} ({owner}/{repo}), Base Commit: {base_commit}, Version: {version}")
    pr_data = github_pr.get_pr_files()
    
    if pr_data:
        
        extensions_to_include = ['.cpp', '.hpp']
        pr_data_filtered = filter_files_include(pr_data, extensions_to_include)
        pr_details = []
        
        for file in pr_data_filtered:
            file_dict = {}
            file_dict['filename'] = file['filename']
            file_dict['status'] = file['status']
            file_dict['additions'] = file['additions']
            file_dict['deletions'] = file['deletions']
            if file['patch']:
                file_dict['patch'] = file['patch']
            else:
                file_dict['patch'] = None
            pr_details.append(file_dict)

        # print(pr_details)
        return pr_details
    
    else:
        print("Failed to fetch PR information.")
        return
        
        
