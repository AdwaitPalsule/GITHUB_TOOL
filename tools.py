import re
from langchain_core.tools import tool
from dotenv import load_dotenv
import requests
import base64
import os

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


# -------------------------
# YOUR CUSTOM URL PARSER
# -------------------------
def url_parser(url: str) -> tuple[str, str]:
    """Parse a GitHub repo URL and return (owner, repo)."""
    url = url.rstrip("/")            # remove trailing slash
    url = url.replace(".git", "")    # remove .git suffix
    parts = url.split("/")           # split by /
    owner = parts[-2]
    repo = parts[-1]
    return owner, repo


# OPTIONAL: alias to keep compatibility
parse_github_url = url_parser


# -------------------------
# TOOLS
# -------------------------

@tool
def get_repo_info(url: str) -> dict:
    """Get basic info about a GitHub repository."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    return requests.get(api_url, headers=HEADERS).json()


@tool
def get_repo_languages(url: str) -> dict:
    """Check what programming languages are used in the repo."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    return requests.get(api_url, headers=HEADERS).json()


@tool
def get_repo_commits(url: str) -> list:
    """Get the 10 most recent commits from the repository."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=10"
    return requests.get(api_url, headers=HEADERS).json()


@tool
def get_repo_branches(url: str) -> list:
    """See all the branches in the repository."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
    return requests.get(api_url, headers=HEADERS).json()


@tool
def get_repo_contributors(url: str) -> list:
    """Find out who contributes to this repository."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
    return requests.get(api_url, headers=HEADERS).json()


@tool
def list_repo_files(url: str, path: str = "") -> dict:
    """Browse files and folders in the repository."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    return requests.get(api_url, headers=HEADERS).json()


@tool
def get_file_content(url: str, file_path: str) -> dict:
    """Read the actual content of a file in the repository."""
    owner, repo = url_parser(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    response = requests.get(api_url, headers=HEADERS).json()

    if "content" in response:
        decoded_content = base64.b64decode(response["content"]).decode("utf-8", errors="ignore")
        return {
            "file_path": file_path,
            "content": decoded_content
        }

    return response
