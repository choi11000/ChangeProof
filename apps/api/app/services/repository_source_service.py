import logging
from dataclasses import dataclass, field

from app.analyzers.file_classifier import classify_file
from app.clients.github import GitHubClient, GitHubError, GitHubFileContentUnavailable
from app.schemas.dependency import RepositoryTree, SourceDocument, SourceScope
from app.schemas.github import (
    AnalysisWarning,
    AnalysisWarningCode,
    ChangedFile,
    ChangedFileStatus,
    ContentPolicy,
    FileCategory,
    GitHubRepositoryRef,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_SOURCE_FILES = 300
DEFAULT_MAX_SOURCE_FILE_BYTES = 256 * 1024  # 256 KiB
DEFAULT_MAX_TOTAL_SOURCE_BYTES = 5 * 1024 * 1024  # 5 MiB


@dataclass
class RepositorySourceSnapshot:
    documents: list[SourceDocument] = field(default_factory=list)
    warnings: list[AnalysisWarning] = field(default_factory=list)
    scan_complete: bool = True


class RepositorySourceService:
    def __init__(
        self,
        github_client: GitHubClient,
        *,
        max_source_files: int = DEFAULT_MAX_SOURCE_FILES,
        max_source_file_bytes: int = DEFAULT_MAX_SOURCE_FILE_BYTES,
        max_total_source_bytes: int = DEFAULT_MAX_TOTAL_SOURCE_BYTES,
    ) -> None:
        self._github = github_client
        self.max_source_files = max_source_files
        self.max_source_file_bytes = max_source_file_bytes
        self.max_total_source_bytes = max_total_source_bytes

    async def collect(
        self,
        repository: GitHubRepositoryRef,
        head_sha: str,
        changed_file_paths: set[str],
    ) -> tuple[RepositoryTree, RepositorySourceSnapshot]:
        tree = await self._github.fetch_repository_tree(repository, head_sha)
        warnings: list[AnalysisWarning] = []
        scan_complete = True

        if tree.truncated:
            warnings.append(
                AnalysisWarning(
                    code=AnalysisWarningCode.REPOSITORY_TREE_TRUNCATED,
                    message="Dependency scan incomplete because repository tree was truncated",
                )
            )
            scan_complete = False

        # Filter candidate blobs
        candidates: list[tuple[str, str | None, SourceScope]] = []
        for entry in tree.entries:
            if entry.type != "blob":
                continue

            dummy_file = ChangedFile(
                path=entry.path,
                status=ChangedFileStatus.MODIFIED,
                additions=0,
                deletions=0,
                changes=0,
            )
            classified = classify_file(dummy_file)

            if classified.content_policy is not ContentPolicy.ALLOW:
                continue

            if classified.category is FileCategory.APPLICATION:
                candidates.append((entry.path, entry.sha, SourceScope.APPLICATION))
            elif classified.category is FileCategory.TEST:
                candidates.append((entry.path, entry.sha, SourceScope.TEST))

        documents: list[SourceDocument] = []
        total_bytes = 0

        for path, sha, scope in candidates:
            if len(documents) >= self.max_source_files:
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.SOURCE_SCAN_LIMIT_REACHED,
                        message=(
                            f"Source scan reached file count limit of {self.max_source_files} files"
                        ),
                    )
                )
                scan_complete = False
                break

            try:
                content = await self._github.fetch_file_content(
                    repository,
                    path,
                    head_sha,
                    max_bytes=self.max_source_file_bytes,
                )
            except (GitHubFileContentUnavailable, GitHubError) as error:
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.SOURCE_CONTENT_UNAVAILABLE,
                        path=path,
                        message=str(error),
                    )
                )
                scan_complete = False
                continue

            if content.too_large:
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.SOURCE_FILE_TOO_LARGE,
                        path=path,
                        message=(
                            f"Source file exceeds maximum size limit of "
                            f"{self.max_source_file_bytes} bytes"
                        ),
                    )
                )
                continue

            text_content = content.content or ""
            content_bytes = len(text_content.encode("utf-8"))
            if total_bytes + content_bytes > self.max_total_source_bytes:
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.SOURCE_SCAN_LIMIT_REACHED,
                        message=(
                            f"Source scan reached total content limit of "
                            f"{self.max_total_source_bytes} bytes"
                        ),
                    )
                )
                scan_complete = False
                break

            total_bytes += content_bytes
            documents.append(
                SourceDocument(
                    path=path,
                    sha=content.sha or sha,
                    scope=scope,
                    content=text_content,
                    changed_in_pull_request=(path in changed_file_paths),
                )
            )

        if not scan_complete and not any(
            w.code is AnalysisWarningCode.DEPENDENCY_SCAN_INCOMPLETE for w in warnings
        ):
            warnings.append(
                AnalysisWarning(
                    code=AnalysisWarningCode.DEPENDENCY_SCAN_INCOMPLETE,
                    message="Dependency scan was incomplete due to scan limits or tree truncation",
                )
            )

        snapshot = RepositorySourceSnapshot(
            documents=documents,
            warnings=warnings,
            scan_complete=scan_complete,
        )
        return tree, snapshot
