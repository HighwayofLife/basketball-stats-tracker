import os

import httpx


class GithubIssueService:
    """Service to create GitHub issues via API."""

    def __init__(self, token: str | None = None, repo: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo = repo or os.getenv("GITHUB_REPOSITORY")
        if not self.token or not self.repo:
            raise ValueError("GitHub token and repository must be provided")

    async def create_issue(self, title: str, body: str, labels: list[str] | None = None) -> dict:
        """Create an issue on GitHub."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        data: dict[str, object] = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/repos/{self.repo}/issues",
                json=data,
                headers=headers,
                timeout=10,
            )
        resp.raise_for_status()
        return resp.json()
