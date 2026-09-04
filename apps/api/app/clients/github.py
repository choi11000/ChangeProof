import base64
import binascii
from typing import Any
from urllib.parse import quote

import httpx

from app.schemas.dependency import RepositoryTree, RepositoryTreeEntry
from app.schemas.github import (
    ChangedFile,
    ChangedFileStatus,
    GitHubFileContent,
    GitHubRepositoryMetadata,
    GitHubRepositoryRef,
    PullRequestMetadata,
)

GITHUB_API_URL = "https://api.github.com"
MAX_SQL_CONTENT_BYTES = 1024 * 1024


class GitHubError(RuntimeError):
    """Base class for safe GitHub integration errors."""


class GitHubRepositoryNotFound(GitHubError):
    pass


class GitHubPullRequestNotFound(GitHubError):
    pass


class GitHubAuthenticationError(GitHubError):
    pass


class GitHubRateLimitError(GitHubError):
    def __init__(self, reset_at: int | None = None) -> None:
        super().__init__("GitHub API rate limit exceeded")
        self.reset_at = reset_at


class GitHubApiUnavailable(GitHubError):
    pass


class GitHubFileContentUnavailable(GitHubError):
    pass


class GitHubPrivateRepositoryRestricted(GitHubError):
    def __init__(self, _message: str | None = None) -> None:
        super().__init__(
            "Repository analysis is restricted to public repositories in this deployment."
        )


class GitHubClient:
    def __init__(
        self, http_client: httpx.AsyncClient, *, public_repositories_only: bool = True
    ) -> None:
        self._http = http_client
        self._public_repositories_only = public_repositories_only

    async def verify_repository(self, repository: GitHubRepositoryRef) -> GitHubRepositoryMetadata:
        data = await self._get(
            f"/repos/{repository.owner}/{repository.repo}",
            not_found=GitHubRepositoryNotFound("GitHub repository not found"),
        )
        try:
            if not isinstance(data, dict):
                raise TypeError
            metadata = GitHubRepositoryMetadata(
                full_name=data.get("full_name", repository.full_name),
                private=bool(data.get("private", False)),
                visibility=data.get("visibility"),
                archived=bool(data.get("archived", False)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubApiUnavailable("GitHub returned an invalid repository response") from error
        if metadata.private and self._public_repositories_only:
            raise GitHubPrivateRepositoryRestricted()
        return metadata

    async def fetch_pull_request(
        self, repository: GitHubRepositoryRef, number: int
    ) -> PullRequestMetadata:
        data = await self._get(
            f"/repos/{repository.owner}/{repository.repo}/pulls/{number}",
            not_found=GitHubPullRequestNotFound("GitHub pull request not found"),
        )
        try:
            return PullRequestMetadata(
                repository=repository.full_name,
                number=data["number"],
                title=data["title"],
                body=data.get("body"),
                state=data["state"],
                base_branch=data["base"]["ref"],
                head_branch=data["head"]["ref"],
                base_sha=data["base"]["sha"],
                head_sha=data["head"]["sha"],
                author=(data.get("user") or {}).get("login"),
                changed_files=data["changed_files"],
                html_url=data["html_url"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubApiUnavailable(
                "GitHub returned an invalid pull request response"
            ) from error

    async def fetch_changed_files(
        self, repository: GitHubRepositoryRef, number: int
    ) -> list[ChangedFile]:
        files: list[ChangedFile] = []
        for page in range(1, 31):
            data = await self._get(
                f"/repos/{repository.owner}/{repository.repo}/pulls/{number}/files",
                params={"per_page": 100, "page": page},
                not_found=GitHubPullRequestNotFound("GitHub pull request not found"),
            )
            if not isinstance(data, list):
                raise GitHubApiUnavailable("GitHub returned an invalid changed-files response")
            files.extend(self._changed_file(item) for item in data)
            if len(data) < 100:
                break
        return files

    async def fetch_repository_tree(
        self, repository: GitHubRepositoryRef, revision: str
    ) -> RepositoryTree:
        data = await self._get(
            f"/repos/{repository.owner}/{repository.repo}/git/trees/{revision}",
            params={"recursive": "1"},
            not_found=GitHubRepositoryNotFound("GitHub repository or tree revision not found"),
        )
        if not isinstance(data, dict) or not isinstance(data.get("tree"), list):
            raise GitHubApiUnavailable("GitHub returned an invalid tree response")

        entries: list[RepositoryTreeEntry] = []
        for item in data["tree"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            entries.append(
                RepositoryTreeEntry(
                    path=item["path"],
                    sha=item.get("sha"),
                    type=item.get("type", "blob"),
                    size=item.get("size"),
                )
            )
        return RepositoryTree(entries=entries, truncated=bool(data.get("truncated", False)))

    async def fetch_file_content(
        self,
        repository: GitHubRepositoryRef,
        path: str,
        revision: str,
        max_bytes: int = MAX_SQL_CONTENT_BYTES,
    ) -> GitHubFileContent:
        encoded_path = quote(path, safe="/")
        data = await self._get(
            f"/repos/{repository.owner}/{repository.repo}/contents/{encoded_path}",
            params={"ref": revision},
            not_found=GitHubFileContentUnavailable("GitHub file content is unavailable"),
        )
        if not isinstance(data, dict):
            raise GitHubFileContentUnavailable("GitHub file content is unavailable")
        size = data.get("size")
        if not isinstance(size, int) or size < 0:
            raise GitHubFileContentUnavailable("GitHub file size is unavailable")
        if size > max_bytes:
            return GitHubFileContent(
                path=path,
                sha=data.get("sha"),
                size=size,
                too_large=True,
            )
        if data.get("encoding") != "base64" or not isinstance(data.get("content"), str):
            raise GitHubFileContentUnavailable("GitHub file content encoding is unsupported")
        try:
            raw_b64 = "".join(data["content"].split())
            decoded = base64.b64decode(raw_b64, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as error:
            raise GitHubFileContentUnavailable("GitHub file content is not valid UTF-8") from error
        return GitHubFileContent(path=path, sha=data.get("sha"), size=size, content=decoded)

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        not_found: GitHubError,
    ) -> Any:
        try:
            response = await self._http.get(path, params=params)
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise GitHubApiUnavailable("GitHub API is unavailable") from error

        if response.status_code == 404:
            raise not_found
        if response.status_code == 401:
            raise GitHubAuthenticationError("GitHub authentication failed")
        if response.status_code in {403, 429}:
            if response.status_code == 429 or response.headers.get("X-RateLimit-Remaining") == "0":
                reset_at = self._safe_int(response.headers.get("X-RateLimit-Reset"))
                raise GitHubRateLimitError(reset_at)
            raise GitHubAuthenticationError("GitHub access was denied")
        if response.status_code >= 500:
            raise GitHubApiUnavailable("GitHub API is unavailable")
        if response.is_error:
            raise GitHubApiUnavailable("GitHub API request failed")
        try:
            return response.json()
        except ValueError as error:
            raise GitHubApiUnavailable("GitHub returned an invalid response") from error

    @staticmethod
    def _changed_file(data: dict[str, Any]) -> ChangedFile:
        status_map = {
            "added": ChangedFileStatus.ADDED,
            "modified": ChangedFileStatus.MODIFIED,
            "removed": ChangedFileStatus.REMOVED,
            "renamed": ChangedFileStatus.RENAMED,
        }
        try:
            return ChangedFile(
                path=data["filename"],
                previous_path=data.get("previous_filename"),
                status=status_map[data["status"]],
                additions=data["additions"],
                deletions=data["deletions"],
                changes=data["changes"],
                patch=data.get("patch"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubApiUnavailable("GitHub returned an invalid changed file") from error

    @staticmethod
    def _safe_int(value: str | None) -> int | None:
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None


def build_github_http_client(token: str | None) -> httpx.AsyncClient:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ChangeProof/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    timeout = httpx.Timeout(15.0, connect=5.0)
    return httpx.AsyncClient(
        base_url=GITHUB_API_URL,
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    )
