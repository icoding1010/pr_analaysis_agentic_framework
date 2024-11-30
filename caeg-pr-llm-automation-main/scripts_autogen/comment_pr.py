import sys
import requests
import os
import json
from openai import AzureOpenAI
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()


def comment_on_pr(token, owner, repo, pr_number, body):
    url = f'https://api.github.com/repos/{repo}/issues/{pr_number}/comments'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'body': body
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 201:
        print('Comment posted successfully.')
    else:
        print(f'Failed to post comment: {response.status_code}')
        print(response.json())

def get_comment_body(api_key, analysis_file):
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint='https://coreengineautomation.openai.azure.com/',
        api_version='2024-02-01'
    )
    try:
        # Read the contents of the two input files
        with open(analysis_file, 'r') as file:
            incomplete_analysis = file.read()

        prompt = (
            f"""Analyze the code analyses in the JSON file 'analysis.json'. The contents of the file are:
            Analysis content:\n{incomplete_analysis}\n.
            Consider the value of the 'Patch' key to be in C++. Do not provide any introduction or explanation during your analysis. Do not add ```markdown``` to the output.\
            The patch should contain only the changes (added/deleted lines) that were made in the code and not the whole file as a patch. 
            
            The final format for a single file should be in the below markdown format:\n'- **File:** \"as per analysis\"\n  - **Proper Logging**: as per analysis\n  - **Exception Handling**: as per analysis\n  - **Code Suggestions**: \"as per analysis\"\n  - <details><summary><b>Patch:</b></summary>patch</details>
            Patch is a part of the code, so, make sure that the patch is in proper markdown format for code.
            Ensure that the patch you generate is in unified format. Also, ensure that the correct file name is provided in the analysis.
            Also, ensure that the patch is relevant to the analysis, that is, do not add the whole file as Patch.
            If code suggetions have more than one suggestion, use numbering to mention each suggestion in a single line. Ensure each suggestion is on a single line with numbering.
            """
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
            {"role": "user", "content": prompt}
          ]
        )

        if response and response.choices:
            final_analysis = response.choices[0].message.content
            final_analysis = f'**_This is an automated comment._**</span>\n\n{final_analysis}'
            return final_analysis
            
        else:
            print("No response or choices found.")
            return None 
    
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


if __name__ == "__main__":

    pr_num = os.getenv('pr_number')
    repo_url = os.getenv('GITHUB_REPO')
    token = os.getenv('GITHUB_TOKEN')
    # api_key = os.getenv('API_KEY')
    api_key = ''
    owner, repo = repo_url.split("/")
    
    logger.info(f"Starting comment script on {repo_url}")

    if len(sys.argv) != 2:
        print("Error: Missing file argument!")
        sys.exit(1)

    analysis_file = sys.argv[1]
    
    COMMENT_BODY = get_comment_body(api_key, analysis_file)
        
    comment_on_pr(token, owner, repo_url, pr_num, COMMENT_BODY)
