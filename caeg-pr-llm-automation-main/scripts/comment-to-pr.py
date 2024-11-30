import sys
import requests
import os
import json
from openai import AzureOpenAI

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

def get_comment_body(api_key, analysis_file, patch_file):
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint='https://coreengineautomation.openai.azure.com/',
        api_version='2024-02-01'
    )
    try:
        # Read the contents of the two input files
        with open(analysis_file, 'r') as file:
            incomplete_analysis = file.read()
        
        with open(patch_file, 'r') as file:
            patch = file.read()
            
        prompt = (
            f"""Analyze the code analyses in the JSON file 'File 1', and the corresponding patches in 'File 2'. Clean the patches in 'File 2' and add them to appropriate places in 'File 1' as key-value pairs, with the key being the string 'Patch' and the value being the corresponding patch. 
            Convert this JSON data into markdown format. Consider the value of the 'Patch' key to be in C++. Use appropriately indented bullet points for the key-value pairs. Provide only this markdown text as output. Do not provide any introduction or explanation. Do not add ```markdown``` to the output.\n\nFile 1:\n{incomplete_analysis}\nFile 2:\n{patch}.
            The patch should contain only the changes (added/deleted lines) that were made in the code and not the whole file as a patch. Do not add + or - in the beginning of lines in the patch.
            The final format for a single file should be in the below markdown format:\n'- **File:** \"as per incomplete_analysis\"\n  - **Proper Logging**: as per incomplete_analysis\n  - **Exception Handling**: as per incomplete_analysis\n  - **Code Suggestions**: \"as per incomplete_analysis\"\n  - <details><summary><b>Patch:</b></summary>patch</details>
            Patch is a part of the code, so, make sure that the patch is in proper markdown format for code.
            Also, make sure that the code suggestions are also in proper markdown format.
            You can also make relevant concise suggestions in the 'code suggesions', if required. Make sure that you mention where the code patches are made in the 'code suggestions'.
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
            final_analysis = f'**_This is an automated comment._**\n\n{final_analysis}'    
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

    pr_number = os.getenv('PR_NUMBER')
    repo_url = os.getenv('GITHUB_REPOSITORY')
    token = os.getenv('GITHUB_TOKEN')
    api_key = os.getenv('API_KEY')
    owner, repo = repo_url.split("/")

    if len(sys.argv) != 3:
        print("Error: Missing file argument!")
        sys.exit(1)

    analysis_file = sys.argv[1]
    patch_file = sys.argv[2]
    
    COMMENT_BODY = get_comment_body(api_key, analysis_file, patch_file)
        
    comment_on_pr(token, owner, repo_url, pr_number, COMMENT_BODY)
