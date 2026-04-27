import os
import base64
import requests

# User configuration
with open('token.txt', 'r') as f:
    TOKEN = f.read().strip()
REPO_NAME = "anime-bot-senior"
USERNAME = "aslbek-dev" # I'll try to fetch this or use a default if possible, but usually needed

def get_username():
    url = "https://api.github.com/user"
    headers = {"Authorization": f"token {TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['login']
    else:
        raise Exception(f"Failed to fetch username: {response.text}")

def create_repo(username):
    url = "https://api.github.com/user/repos"
    headers = {"Authorization": f"token {TOKEN}"}
    data = {
        "name": REPO_NAME,
        "description": "Anime Telegram Bot - Senior Refactored Version",
        "private": False
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f"Repository {REPO_NAME} created successfully.")
    elif response.status_code == 422:
        print(f"Repository {REPO_NAME} already exists.")
    else:
        raise Exception(f"Failed to create repo: {response.text}")

def upload_file(username, repo_name, file_path, content):
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = {"Authorization": f"token {TOKEN}"}
    
    # Base64 encode content
    encoded_content = base64.b64encode(content).decode('utf-8')
    
    data = {
        "message": f"Upload {file_path}",
        "content": encoded_content
    }
    
    # Check if file exists to get SHA (for updates)
    get_response = requests.get(url, headers=headers)
    if get_response.status_code == 200:
        data["sha"] = get_response.json()['sha']
        
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print(f"Uploaded: {file_path}")
    else:
        print(f"Failed to upload {file_path}: {response.text}")

def main():
    try:
        username = get_username()
        print(f"Authenticated as: {username}")
        
        create_repo(username)
        
        exclude_dirs = {'.venv', '__pycache__', '.git', 'temp_zip_dir', '.gemini'}
        exclude_files = {'db.sqlite3', 'anime_bot_full.zip', 'github_upload.py', 'git_installer.exe', 'send_zip.py'}
        
        for root, dirs, files in os.walk('.'):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files:
                    continue
                
                file_full_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_full_path, '.').replace('\\', '/')
                
                with open(file_full_path, 'rb') as f:
                    content = f.read()
                    upload_file(username, REPO_NAME, rel_path, content)
                    
        print(f"\nAll done! Your repo is at: https://github.com/{username}/{REPO_NAME}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
