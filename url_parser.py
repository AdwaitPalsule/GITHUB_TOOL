import re


def url_parser(url: str) -> tuple[str, str]:
    """Parse a GitHub repo URL and return (owner, repo)."""
    parts = url
    parts=parts.rstrip("/")
    parts=parts.replace(".git","")
    parts=parts.split("/")
    owner=parts[-2]
    repo=parts[-1]

    return owner,repo
           