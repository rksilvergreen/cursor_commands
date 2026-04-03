"""
Higher-level Git workflows that build on `git_commands.py`.

`git_init`
    Mirrors the behavior described in `git-init.md`: local repo with main +
    develop, initial commit, optional GitHub remote via `gh`, and both branches
    pushed when remote creation succeeds.

`git_commit_and_push`
    Mirrors the behavior described in `git-commit-and-push.md`: stage, commit
    with a caller-supplied message, and push to the remote.

`git_merge_to_main`
    Mirrors the behavior described in `git-merge-to-main.md`: merge the
    current branch into main with ``--no-ff``, tag the release, and push.

GitHub MCP (Cursor) cannot be invoked from plain Python; use `gh` or add the
remote yourself when the CLI is unavailable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Union

StrPath = Union[str, Path]

_GIT_CMD_DIR = str(Path(__file__).resolve().parent)
if _GIT_CMD_DIR not in sys.path:
    sys.path.insert(0, _GIT_CMD_DIR)

import git_commands as gc  # noqa: E402


ExistingRepoPolicy = Literal["raise", "return", "reinitialize"]


class GitRepositoryExistsError(RuntimeError):
    """Raised when `.git` already exists and `existing_repository=\"raise\"`."""


class GitWorkflowError(RuntimeError):
    """Base for hard failures in any custom Git workflow."""


class GitInitError(GitWorkflowError):
    """Raised for hard failures during initialization (Git or `gh`)."""


class GitCommitAndPushError(GitWorkflowError):
    """Raised for hard failures during commit-and-push."""


class GitMergeToMainError(GitWorkflowError):
    """Raised for hard failures during merge-to-main."""


@dataclass
class GitInitResult:
    """Outcome of `git_init`."""

    success: bool
    repository_root: Path
    repository_name: str
    current_branch: str
    main_branch: str
    develop_branch: str
    remote_url: Optional[str] = None
    github_remote_configured: bool = False
    skipped: bool = False
    skip_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class GitCommitAndPushResult:
    """Outcome of `git_commit_and_push`."""

    success: bool
    repository_root: Path
    branch: str
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    pushed: bool = False
    remote_url: Optional[str] = None
    nothing_to_commit: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass
class GitMergeToMainResult:
    """Outcome of `git_merge_to_main`."""

    success: bool
    repository_root: Path
    source_branch: str
    main_branch: str
    version: str
    tag: str
    merge_commit_hash: Optional[str] = None
    pre_merge_commit_hash: Optional[str] = None
    pushed: bool = False
    remote_url: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def _resolve_root(path: Optional[StrPath]) -> Path:
    base = Path(path) if path is not None else Path.cwd()
    return base.resolve()


def _repo_name(repo_root: Path, repository_name: Optional[str]) -> str:
    if repository_name is not None and repository_name.strip():
        return repository_name.strip()
    return repo_root.name


def _inside_git_work_tree(repo_root: Path) -> bool:
    r = gc.run_git(
        "rev-parse",
        "--is-inside-work-tree",
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode == 0 and r.stdout.strip().lower() == "true"


def _current_branch(repo_root: Path) -> str:
    r = gc.git_branch(show_current=True, cwd=repo_root, capture_output=True, check=True)
    return r.stdout.strip()


def _get_remote_url(repo_root: Path, remote_name: str) -> Optional[str]:
    r = gc.git_remote("get-url", name=remote_name, cwd=repo_root, capture_output=True, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _snapshot_repo_state(repo_root: Path, remote_name: str) -> tuple[str, Optional[str], str]:
    branch = _current_branch(repo_root)
    remote_url = _get_remote_url(repo_root, remote_name)
    st = gc.git_status(short=True, branch=True, cwd=repo_root, capture_output=True, check=True)
    status_line = st.stdout.strip()
    return branch, remote_url, status_line


def _backup_git_dir(repo_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = repo_root / f".git.init_backup_{stamp}"
    shutil.move(str(repo_root / ".git"), str(backup))
    return backup


def _gh_available(executable: str) -> bool:
    try:
        r = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


def _gh_authenticated(executable: str, repo_root: Path) -> bool:
    try:
        r = subprocess.run(
            [executable, "auth", "status"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


def _run_gh_repo_create(
    *,
    repo_root: Path,
    repository_name: str,
    remote_name: str,
    github_public: bool,
    github_description: Optional[str],
    github_license: Optional[str],
    gh_executable: str,
) -> None:
    cmd: List[str] = [
        gh_executable,
        "repo",
        "create",
        repository_name,
        "--source",
        str(repo_root),
        "--remote",
        remote_name,
    ]
    if github_public:
        cmd.append("--public")
    else:
        cmd.append("--private")
    if github_description:
        cmd.extend(["--description", github_description])
    if github_license:
        cmd.extend(["--license", github_license])
    try:
        proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    except OSError as exc:
        raise GitInitError(
            f"Failed to run `{gh_executable}`: {exc}"
        ) from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise GitInitError(
            f"`gh repo create` failed (exit {proc.returncode}): {err or 'no output'}"
        )


def git_init(
    path: Optional[StrPath] = None,
    *,
    repository_name: Optional[str] = None,
    main_branch: str = "main",
    develop_branch: str = "develop",
    initial_commit_message: str = "Initial commit",
    remote_name: str = "origin",
    create_github_repository: bool = True,
    github_public: bool = True,
    github_license: Optional[str] = None,
    github_description: Optional[str] = None,
    github_cli_executable: str = "gh",
    continue_without_github_if_cli_unavailable: bool = True,
    strict_github: bool = False,
    existing_repository: ExistingRepoPolicy = "raise",
    reinitialize_backup_git_dir: bool = True,
) -> GitInitResult:
    """
    Initialize a project directory the way `git-init.md` describes:

    - Ensure a new Git repo (or honor `existing_repository` policy).
    - Default branch `main_branch`, initial commit (empty if nothing to add).
    - Create `develop_branch` from `main_branch` and switch to it.
    - Optionally create a GitHub repo with `gh` and push both branches with upstreams.

    Parameters
    ----------
    path :
        Project root. Default: current working directory.
    repository_name :
        Used for `gh repo create` and defaults; default: directory name of `path`.
    main_branch / develop_branch :
        Branch names (must differ).
    initial_commit_message :
        First commit message; empty tree uses ``--allow-empty``.
    remote_name :
        Remote for GitHub (default ``origin``).
    create_github_repository :
        If True, try `gh repo create` then push both branches. If False, local only.
    github_public :
        If True (default), ``--public``; otherwise ``--private``.
    github_license :
        Optional `gh` license template (e.g. ``\"mit\"``). Default: none.
    github_description :
        Optional repo description for GitHub.
    github_cli_executable :
        `gh` binary name or path.
    continue_without_github_if_cli_unavailable :
        If ``gh`` is missing or not authenticated, finish local setup only and record a warning.
    strict_github :
        If True and GitHub creation was requested but failed, raise `GitInitError`
        instead of returning with warnings.
    existing_repository :
        ``\"raise\"`` — `GitRepositoryExistsError` with status summary.
        ``\"return\"`` — `GitInitResult` with ``skipped=True`` and current info.
        ``\"reinitialize\"`` — move `.git` aside (if `reinitialize_backup_git_dir`) then proceed.
    reinitialize_backup_git_dir :
        When ``existing_repository=\"reinitialize\"``, rename `.git` to a timestamped backup.
        If False, removes `.git` without backup (dangerous).
    """
    warnings: List[str] = []
    repo_root = _resolve_root(path)
    name = _repo_name(repo_root, repository_name)

    if main_branch == develop_branch:
        raise GitInitError("main_branch and develop_branch must differ")

    if _inside_git_work_tree(repo_root):
        if existing_repository == "raise":
            br, url, status = _snapshot_repo_state(repo_root, remote_name)
            msg = (
                f"Git repository already exists in {repo_root}\n"
                f"  Branch: {br}\n"
                f"  Remote {remote_name}: {url or '(none)'}\n"
                f"  Status:\n{status}"
            )
            raise GitRepositoryExistsError(msg)
        if existing_repository == "return":
            br, url, _ = _snapshot_repo_state(repo_root, remote_name)
            return GitInitResult(
                success=True,
                repository_root=repo_root,
                repository_name=name,
                current_branch=br,
                main_branch=main_branch,
                develop_branch=develop_branch,
                remote_url=url,
                github_remote_configured=bool(url and "github.com" in url),
                skipped=True,
                skip_reason="repository_already_exists",
                warnings=warnings,
            )
        if existing_repository == "reinitialize":
            if reinitialize_backup_git_dir:
                backup = _backup_git_dir(repo_root)
                warnings.append(f"Existing `.git` moved to {backup.name} (reinitialize).")
            else:
                shutil.rmtree(repo_root / ".git")
                warnings.append("Removed existing `.git` without backup (reinitialize).")

    gc.git_init(initial_branch=main_branch, cwd=str(repo_root), quiet=False)
    gc.git_add(all=True, cwd=str(repo_root))
    cr = gc.git_commit(
        message=initial_commit_message,
        cwd=str(repo_root),
        check=False,
        capture_output=True,
    )
    if cr.returncode != 0:
        gc.git_commit(
            message=initial_commit_message,
            allow_empty=True,
            cwd=str(repo_root),
            check=True,
            capture_output=True,
        )

    gc.git_branch(develop_branch, cwd=str(repo_root))
    gc.git_switch(develop_branch, cwd=str(repo_root))

    remote_url: Optional[str] = None
    github_ok = False

    if create_github_repository:
        if not _gh_available(github_cli_executable):
            w = (
                "GitHub CLI (`gh`) not found; local repository initialized without remote. "
                "Install https://cli.github.com or add `origin` manually."
            )
            warnings.append(w)
            if strict_github:
                raise GitInitError(w)
        elif not _gh_authenticated(github_cli_executable, repo_root):
            w = (
                "`gh` is not authenticated (`gh auth login`). "
                "Local repository initialized without GitHub remote."
            )
            warnings.append(w)
            if strict_github:
                raise GitInitError(w)
        else:
            try:
                _run_gh_repo_create(
                    repo_root=repo_root,
                    repository_name=name,
                    remote_name=remote_name,
                    github_public=github_public,
                    github_description=github_description,
                    github_license=github_license,
                    gh_executable=github_cli_executable,
                )
                gc.git_switch(main_branch, cwd=str(repo_root))
                gc.git_push(remote_name, main_branch, set_upstream=True, cwd=str(repo_root))
                gc.git_switch(develop_branch, cwd=str(repo_root))
                gc.git_push(remote_name, develop_branch, set_upstream=True, cwd=str(repo_root))
                github_ok = True
                remote_url = _get_remote_url(repo_root, remote_name)
            except GitInitError as e:
                if strict_github:
                    raise
                warnings.append(str(e))
            except Exception as e:  # pragma: no cover
                msg = f"Unexpected error during GitHub setup: {e}"
                if strict_github:
                    raise GitInitError(msg) from e
                warnings.append(msg)
    else:
        warnings.append(
            "Skipped GitHub repository creation (create_github_repository=False)."
        )

    if remote_url is None:
        remote_url = _get_remote_url(repo_root, remote_name)

    branch_now = _current_branch(repo_root)

    return GitInitResult(
        success=True,
        repository_root=repo_root,
        repository_name=name,
        current_branch=branch_now,
        main_branch=main_branch,
        develop_branch=develop_branch,
        remote_url=remote_url,
        github_remote_configured=github_ok,
        skipped=False,
        skip_reason=None,
        warnings=warnings,
    )


def _has_staged_changes(repo_root: Path) -> bool:
    r = gc.git_diff(staged=True, name_only=True, cwd=repo_root, capture_output=True, check=False)
    return bool(r.stdout.strip())


def _commit_hash(repo_root: Path) -> Optional[str]:
    r = gc.git_rev_parse("HEAD", cwd=repo_root, capture_output=True, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _has_tracking_branch(repo_root: Path, branch: str, remote_name: str) -> bool:
    r = gc.run_git(
        "config", "--get", f"branch.{branch}.remote",
        cwd=str(repo_root), capture_output=True, text=True, check=False,
    )
    return r.returncode == 0 and r.stdout.strip() == remote_name


def git_commit_and_push(
    path: Optional[StrPath] = None,
    *,
    message: str,
    stage_all: bool = True,
    push: bool = True,
    remote_name: str = "origin",
    set_upstream_if_missing: bool = True,
    strict_push: bool = False,
) -> GitCommitAndPushResult:
    """
    Stage, commit, and push in one call — the workflow described by
    `git-commit-and-push.md`.

    Parameters
    ----------
    path :
        Repository root. Default: current working directory.
    message :
        Commit message (the caller — typically the agent — is responsible for
        composing a conventional-commit-style message).
    stage_all :
        If True (default), run ``git add -A`` before committing.  Set to
        False when the user explicitly asks to commit only what is already
        staged.
    push :
        If True (default), push to the remote after committing.
    remote_name :
        Remote name used for the push (default ``origin``).
    set_upstream_if_missing :
        If the current branch has no tracking branch, push with ``-u``.
    strict_push :
        If True and the push fails, raise ``GitCommitAndPushError`` instead
        of returning with warnings.
    """
    warnings: List[str] = []
    repo_root = _resolve_root(path)

    if not _inside_git_work_tree(repo_root):
        raise GitCommitAndPushError(
            f"No Git repository found at {repo_root}. Initialize one first."
        )

    branch = _current_branch(repo_root)

    if stage_all:
        gc.git_add(all=True, cwd=str(repo_root))

    if not _has_staged_changes(repo_root):
        return GitCommitAndPushResult(
            success=True,
            repository_root=repo_root,
            branch=branch,
            nothing_to_commit=True,
            warnings=["Nothing to commit — working tree clean or nothing staged."],
        )

    try:
        gc.git_commit(message=message, cwd=str(repo_root), check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise GitCommitAndPushError(
            f"git commit failed (exit {exc.returncode}): "
            f"{(exc.stderr or exc.stdout or '').strip() or 'no output'}"
        ) from exc

    commit_hash = _commit_hash(repo_root)

    pushed = False
    remote_url: Optional[str] = None

    if push:
        remote_url = _get_remote_url(repo_root, remote_name)
        if remote_url is None:
            w = (
                f"Remote '{remote_name}' is not configured; commit created locally "
                "but not pushed. Add a remote or push manually."
            )
            warnings.append(w)
            if strict_push:
                raise GitCommitAndPushError(w)
        else:
            use_upstream = set_upstream_if_missing and not _has_tracking_branch(
                repo_root, branch, remote_name,
            )
            try:
                gc.git_push(
                    remote_name, branch,
                    set_upstream=use_upstream,
                    cwd=str(repo_root),
                    check=True,
                    capture_output=True,
                )
                pushed = True
            except subprocess.CalledProcessError as exc:
                err = (exc.stderr or exc.stdout or "").strip()
                w = f"Push failed (exit {exc.returncode}): {err or 'no output'}"
                warnings.append(w)
                if strict_push:
                    raise GitCommitAndPushError(w) from exc
    else:
        warnings.append("Push skipped (push=False).")

    if remote_url is None:
        remote_url = _get_remote_url(repo_root, remote_name)

    return GitCommitAndPushResult(
        success=True,
        repository_root=repo_root,
        branch=branch,
        commit_hash=commit_hash,
        commit_message=message,
        pushed=pushed,
        remote_url=remote_url,
        nothing_to_commit=False,
        warnings=warnings,
    )


def _has_uncommitted_changes(repo_root: Path) -> bool:
    r = gc.git_status(short=True, cwd=repo_root, capture_output=True, check=True)
    return bool(r.stdout.strip())


def _tag_exists(repo_root: Path, tag_name: str) -> bool:
    r = gc.run_git(
        "tag", "--list", tag_name,
        cwd=str(repo_root), capture_output=True, text=True, check=False,
    )
    return bool(r.stdout.strip())


def git_merge_to_main(
    path: Optional[StrPath] = None,
    *,
    version: str,
    main_branch: str = "main",
    remote_name: str = "origin",
    tag_prefix: str = "v",
    commit_uncommitted: bool = True,
    pre_merge_commit_message: Optional[str] = None,
    merge_commit_message: Optional[str] = None,
    tag_message: Optional[str] = None,
    push: bool = True,
    strict_push: bool = False,
) -> GitMergeToMainResult:
    """
    Merge the current branch into main, tag the release, and push — the
    workflow described by `git-merge-to-main.md`.

    Parameters
    ----------
    path :
        Repository root. Default: current working directory.
    version :
        Release version string (required).  Used in the default merge commit
        message, tag name, and tag annotation.
    main_branch :
        Target branch to merge into (default ``main``).
    remote_name :
        Remote name for pushes (default ``origin``).
    tag_prefix :
        Prefix for the tag name (default ``v``); the tag becomes
        ``{tag_prefix}{version}``.
    commit_uncommitted :
        If True (default) and there are uncommitted changes, stage and commit
        them on the source branch before merging.
    pre_merge_commit_message :
        Commit message for uncommitted changes.  Default:
        ``"chore: Prepare release {version}"``.
    merge_commit_message :
        Message for the ``--no-ff`` merge commit.  Default:
        ``"chore: Release version {version}"``.
    tag_message :
        Annotation for the release tag.  Default:
        ``"Release version {version}"``.
    push :
        If True (default), push the source branch, main, and tags.
    strict_push :
        If True and any push fails, raise ``GitMergeToMainError`` instead
        of returning with warnings.
    """
    warnings: List[str] = []
    repo_root = _resolve_root(path)

    if not version or not version.strip():
        raise GitMergeToMainError("A version string is required.")

    version = version.strip()
    tag_name = f"{tag_prefix}{version}"

    if not _inside_git_work_tree(repo_root):
        raise GitMergeToMainError(
            f"No Git repository found at {repo_root}. Initialize one first."
        )

    source_branch = _current_branch(repo_root)

    if source_branch == main_branch:
        raise GitMergeToMainError(
            f"Already on '{main_branch}'. Check out the branch you want to merge first."
        )

    if _tag_exists(repo_root, tag_name):
        raise GitMergeToMainError(
            f"Tag '{tag_name}' already exists. Use a different version "
            "or delete the existing tag."
        )

    # --- commit any uncommitted changes on the source branch ---
    pre_merge_hash: Optional[str] = None
    if commit_uncommitted and _has_uncommitted_changes(repo_root):
        msg = pre_merge_commit_message or f"chore: Prepare release {version}"
        gc.git_add(all=True, cwd=str(repo_root))
        try:
            gc.git_commit(
                message=msg, cwd=str(repo_root), check=True, capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            raise GitMergeToMainError(
                f"Pre-merge commit failed (exit {exc.returncode}): "
                f"{(exc.stderr or exc.stdout or '').strip() or 'no output'}"
            ) from exc
        pre_merge_hash = _commit_hash(repo_root)

    # --- push source branch ---
    if push:
        try:
            use_upstream = not _has_tracking_branch(
                repo_root, source_branch, remote_name,
            )
            gc.git_push(
                remote_name, source_branch,
                set_upstream=use_upstream,
                cwd=str(repo_root),
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or exc.stdout or "").strip()
            w = f"Source-branch push failed (exit {exc.returncode}): {err or 'no output'}"
            warnings.append(w)
            if strict_push:
                raise GitMergeToMainError(w) from exc

    # --- checkout main ---
    try:
        gc.git_checkout(
            main_branch, cwd=str(repo_root), check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise GitMergeToMainError(
            f"Failed to check out '{main_branch}' (exit {exc.returncode}): "
            f"{(exc.stderr or exc.stdout or '').strip() or 'no output'}"
        ) from exc

    # --- merge source into main (--no-ff) ---
    m_msg = merge_commit_message or f"chore: Release version {version}"
    try:
        gc.git_merge(
            source_branch, no_ff=True, message=m_msg,
            cwd=str(repo_root), check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        gc.git_checkout(
            source_branch, cwd=str(repo_root), check=False, capture_output=True,
        )
        raise GitMergeToMainError(
            f"Merge failed (exit {exc.returncode}): "
            f"{(exc.stderr or exc.stdout or '').strip() or 'no output'}. "
            "Resolve conflicts manually and retry."
        ) from exc

    merge_hash = _commit_hash(repo_root)

    # --- tag ---
    t_msg = tag_message or f"Release version {version}"
    try:
        gc.git_tag(
            tag_name, annotate=True, message=t_msg,
            cwd=str(repo_root), check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        gc.git_checkout(
            source_branch, cwd=str(repo_root), check=False, capture_output=True,
        )
        raise GitMergeToMainError(
            f"Tagging failed (exit {exc.returncode}): "
            f"{(exc.stderr or exc.stdout or '').strip() or 'no output'}"
        ) from exc

    # --- push main and tags ---
    pushed = False
    remote_url: Optional[str] = None
    if push:
        remote_url = _get_remote_url(repo_root, remote_name)
        if remote_url is None:
            w = (
                f"Remote '{remote_name}' is not configured; merge and tag "
                "created locally but not pushed."
            )
            warnings.append(w)
            if strict_push:
                gc.git_checkout(
                    source_branch, cwd=str(repo_root),
                    check=False, capture_output=True,
                )
                raise GitMergeToMainError(w)
        else:
            try:
                gc.git_push(
                    remote_name, main_branch,
                    cwd=str(repo_root), check=True, capture_output=True,
                )
                gc.git_push(
                    remote_name, tags=True,
                    cwd=str(repo_root), check=True, capture_output=True,
                )
                pushed = True
            except subprocess.CalledProcessError as exc:
                err = (exc.stderr or exc.stdout or "").strip()
                w = f"Push failed (exit {exc.returncode}): {err or 'no output'}"
                warnings.append(w)
                if strict_push:
                    gc.git_checkout(
                        source_branch, cwd=str(repo_root),
                        check=False, capture_output=True,
                    )
                    raise GitMergeToMainError(w) from exc
    else:
        warnings.append("Push skipped (push=False).")

    # --- return to source branch ---
    gc.git_checkout(
        source_branch, cwd=str(repo_root), check=False, capture_output=True,
    )

    if remote_url is None:
        remote_url = _get_remote_url(repo_root, remote_name)

    return GitMergeToMainResult(
        success=True,
        repository_root=repo_root,
        source_branch=source_branch,
        main_branch=main_branch,
        version=version,
        tag=tag_name,
        merge_commit_hash=merge_hash,
        pre_merge_commit_hash=pre_merge_hash,
        pushed=pushed,
        remote_url=remote_url,
        warnings=warnings,
    )


__all__ = [
    "ExistingRepoPolicy",
    "GitCommitAndPushError",
    "GitCommitAndPushResult",
    "GitInitError",
    "GitInitResult",
    "GitMergeToMainError",
    "GitMergeToMainResult",
    "GitRepositoryExistsError",
    "GitWorkflowError",
    "git_commit_and_push",
    "git_init",
    "git_merge_to_main",
]
