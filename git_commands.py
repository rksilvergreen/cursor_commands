"""
Thin wrappers around the git CLI for cross-platform use.

Requires: Python 3.7+ and `git` on PATH (or set GIT_EXECUTABLE).

Usage:
    from git_commands import run_git, git_clone, git_commit
    run_git("status", "-sb")
    git_commit(message="fix: typo", cwd="/path/to/repo")
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

StrPath = Union[str, Path]
GitEnv = Optional[Mapping[str, str]]


def _exe() -> str:
    return os.environ.get("GIT_EXECUTABLE", "git")


def _str_paths(paths: Optional[Iterable[StrPath]]) -> List[str]:
    if not paths:
        return []
    return [str(p) for p in paths]


def run_git(
    *args: str,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
    text: bool = True,
    env: GitEnv = None,
    stdin: Optional[Union[str, bytes]] = None,
    input: Optional[Union[str, bytes]] = None,
) -> subprocess.CompletedProcess:
    """
    Run `git` with the given arguments. Extra kwargs are forwarded to subprocess.run.

    Returns subprocess.CompletedProcess. Raises CalledProcessError if check=True and git exits non-zero.
    """
    cmd: List[str] = [_exe(), *args]
    run_kw: Dict[str, Any] = {
        "cwd": str(cwd) if cwd is not None else None,
        "check": check,
        "capture_output": capture_output,
        "text": text,
    }
    if env is not None:
        run_kw["env"] = {**os.environ, **dict(env)}
    if input is not None:
        run_kw["input"] = input
    elif stdin is not None:
        run_kw["input"] = stdin
    return subprocess.run(cmd, **run_kw)


# --- clone / init ---


def git_clone(
    url: str,
    directory: Optional[StrPath] = None,
    *,
    depth: Optional[int] = None,
    branch: Optional[str] = None,
    single_branch: bool = False,
    recurse_submodules: bool = False,
    shallow_submodules: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["clone"]
    if depth is not None:
        args.extend(["--depth", str(depth)])
    if branch:
        args.extend(["--branch", branch])
    if single_branch:
        args.append("--single-branch")
    if recurse_submodules:
        args.append("--recurse-submodules")
    if shallow_submodules:
        args.append("--shallow-submodules")
    args.append(url)
    if directory is not None:
        args.append(str(directory))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_init(
    path: Optional[StrPath] = None,
    *,
    bare: bool = False,
    initial_branch: Optional[str] = None,
    quiet: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["init"]
    if quiet:
        args.append("--quiet")
    if bare:
        args.append("--bare")
    if initial_branch:
        args.extend(["--initial-branch", initial_branch])
    if path is not None:
        args.append(str(path))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- status / diff ---


def git_status(
    *,
    short: bool = False,
    branch: bool = False,
    untracked_files: Optional[str] = None,  # "no", "normal", "all"
    ignored: Optional[str] = None,  # "traditional", "matching", "no"
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["status"]
    if short:
        args.append("--short")
    if branch:
        args.append("--branch")
    if untracked_files:
        args.extend(["--untracked-files", untracked_files])
    if ignored:
        args.extend(["--ignored", ignored])
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_diff(
    *paths: StrPath,
    staged: bool = False,
    stat: bool = False,
    name_only: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = False,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["diff"]
    if staged:
        args.append("--cached")
    if stat:
        args.append("--stat")
    if name_only:
        args.append("--name-only")
    args.extend(_str_paths(paths))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- add / rm ---


def git_add(
    *paths: StrPath,
    all: bool = False,
    force: bool = False,
    update: bool = False,
    intent_to_add: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["add"]
    if all:
        args.append("--all")
    if force:
        args.append("--force")
    if update:
        args.append("--update")
    if intent_to_add:
        args.append("--intent-to-add")
    args.extend(_str_paths(paths) if paths else ([] if all or update else ["."]))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_rm(
    *paths: StrPath,
    cached: bool = False,
    force: bool = False,
    recursive: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["rm"]
    if cached:
        args.append("--cached")
    if force:
        args.append("--force")
    if recursive:
        args.append("-r")
    args.extend(_str_paths(paths))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- commit ---


def git_commit(
    *,
    message: Optional[str] = None,
    message_file: Optional[StrPath] = None,
    amend: bool = False,
    all: bool = False,
    signoff: bool = False,
    allow_empty: bool = False,
    no_verify: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["commit"]
    if message:
        args.extend(["-m", message])
    if message_file:
        args.extend(["-F", str(message_file)])
    if amend:
        args.append("--amend")
    if all:
        args.append("--all")
    if signoff:
        args.append("--signoff")
    if allow_empty:
        args.append("--allow-empty")
    if no_verify:
        args.append("--no-verify")
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- branch / checkout / switch ---


def git_branch(
    name: Optional[str] = None,
    *,
    list_: bool = False,
    all_remotes: bool = False,
    delete: Optional[str] = None,
    force_delete: Optional[str] = None,
    move: Optional[str] = None,
    show_current: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["branch"]
    if list_:
        args.append("--list")
    if all_remotes:
        args.append("-a")
    if show_current:
        args.append("--show-current")
    if delete:
        args.extend(["-d", delete])
    if force_delete:
        args.extend(["-D", force_delete])
    if move:
        args.extend(["-m", move])
    if name:
        args.append(name)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_checkout(
    target: Optional[str] = None,
    *paths: StrPath,
    new_branch: Optional[str] = None,
    track: Optional[str] = None,
    force: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["checkout"]
    if force:
        args.append("--force")
    if new_branch:
        args.extend(["-b", new_branch])
    if track:
        args.extend(["--track", track])
    if target:
        args.append(target)
    args.extend(_str_paths(paths))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_switch(
    branch: Optional[str] = None,
    *,
    create: Optional[str] = None,
    force_create: Optional[str] = None,
    detach: Optional[str] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["switch"]
    if create:
        args.extend(["-c", create])
    if force_create:
        args.extend(["-C", force_create])
    if detach:
        args.extend(["--detach", detach])
    if branch:
        args.append(branch)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- remote ---


def git_remote(
    action: str = "show",
    *,
    name: Optional[str] = None,
    new_name: Optional[str] = None,
    url: Optional[str] = None,
    add_track: Optional[str] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["remote", action]
    if action == "add" and name and url:
        args.extend([name, url])
        if add_track:
            args.extend(["-t", add_track])
    elif action == "rename" and name and new_name:
        args.extend([name, new_name])
    elif name and action in ("remove", "set-url", "get-url"):
        args.append(name)
        if url and action == "set-url":
            args.append(url)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- fetch / pull / push ---


def git_fetch(
    remote: Optional[str] = None,
    *refspecs: str,
    all_remotes: bool = False,
    prune: bool = False,
    tags: bool = False,
    depth: Optional[int] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["fetch"]
    if all_remotes:
        args.append("--all")
    if prune:
        args.append("--prune")
    if tags:
        args.append("--tags")
    if depth is not None:
        args.extend(["--depth", str(depth)])
    if remote:
        args.append(remote)
    args.extend(refspecs)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_pull(
    remote: Optional[str] = None,
    branch: Optional[str] = None,
    *,
    rebase: bool = False,
    ff_only: bool = False,
    no_ff: bool = False,
    autostash: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["pull"]
    if rebase:
        args.append("--rebase")
    if ff_only:
        args.append("--ff-only")
    if no_ff:
        args.append("--no-ff")
    if autostash:
        args.append("--autostash")
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_push(
    remote: Optional[str] = None,
    *refspecs: str,
    set_upstream: bool = False,
    force: bool = False,
    force_with_lease: bool = False,
    tags: bool = False,
    delete: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["push"]
    if set_upstream:
        args.append("-u")
    if force:
        args.append("--force")
    if force_with_lease:
        args.append("--force-with-lease")
    if tags:
        args.append("--tags")
    if delete:
        args.append("--delete")
    if remote:
        args.append(remote)
    args.extend(refspecs)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- merge / rebase ---


def git_merge(
    commit: Optional[str] = None,
    *,
    abort: bool = False,
    continue_merge: bool = False,
    ff_only: bool = False,
    no_ff: bool = False,
    squash: bool = False,
    message: Optional[str] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["merge"]
    if abort:
        args.append("--abort")
    if continue_merge:
        args.append("--continue")
    if ff_only:
        args.append("--ff-only")
    if no_ff:
        args.append("--no-ff")
    if squash:
        args.append("--squash")
    if message:
        args.extend(["-m", message])
    if commit:
        args.append(commit)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_rebase(
    upstream_or_branch: Optional[str] = None,
    *,
    onto: Optional[str] = None,
    interactive: bool = False,
    abort: bool = False,
    continue_rebase: bool = False,
    skip: bool = False,
    autostash: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["rebase"]
    if interactive:
        args.append("--interactive")
    if onto:
        args.extend(["--onto", onto])
    if autostash:
        args.append("--autostash")
    if abort:
        args.append("--abort")
    if continue_rebase:
        args.append("--continue")
    if skip:
        args.append("--skip")
    if upstream_or_branch:
        args.append(upstream_or_branch)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- log / show / blame ---


def git_log(
    *paths: StrPath,
    oneline: bool = False,
    graph: bool = False,
    max_count: Optional[int] = None,
    skip: Optional[int] = None,
    decorate: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    author: Optional[str] = None,
    grep: Optional[str] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["log"]
    if oneline:
        args.append("--oneline")
    if graph:
        args.append("--graph")
    if max_count is not None:
        args.extend(["-n", str(max_count)])
    if skip is not None:
        args.extend(["--skip", str(skip)])
    if decorate:
        args.extend(["--decorate", decorate])
    if since:
        args.extend(["--since", since])
    if until:
        args.extend(["--until", until])
    if author:
        args.extend(["--author", author])
    if grep:
        args.extend(["--grep", grep])
    args.extend(["--", *_str_paths(paths)] if paths else [])
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_show(
    ref: str = "HEAD",
    *,
    stat: bool = False,
    name_only: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["show", ref]
    if stat:
        args.append("--stat")
    if name_only:
        args.append("--name-only")
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_blame(
    file: StrPath,
    *,
    line_range: Optional[str] = None,  # e.g. "10,20" for -L 10,20
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["blame"]
    if line_range:
        args.extend(["-L", line_range])
    args.append(str(file))
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- stash ---


def git_stash(
    action: str = "list",
    *,
    message: Optional[str] = None,
    include_untracked: bool = False,
    branch: Optional[str] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["stash", action]
    if action == "push":
        if include_untracked:
            args.append("--include-untracked")
        if message:
            args.extend(["-m", message])
    elif action == "branch" and branch:
        args.append(branch)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- tag ---


def git_tag(
    name: Optional[str] = None,
    *,
    list_tags: bool = False,
    annotate: bool = False,
    message: Optional[str] = None,
    sign: bool = False,
    delete: Optional[str] = None,
    commit: Optional[str] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """List, create (lightweight or annotated with -a/-m/-s), or delete tags."""
    args: List[str] = ["tag"]
    if list_tags:
        args.append("--list")
    if delete:
        args.extend(["-d", delete])
        return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)
    if annotate or message or sign:
        args.append("-a")
    if message:
        args.extend(["-m", message])
    if sign:
        args.append("-s")
    if name:
        args.append(name)
        if commit:
            args.append(commit)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- reset / clean / cherry-pick ---


def git_reset(
    target: Optional[str] = None,
    *,
    mode: Optional[str] = None,
    paths: Optional[Sequence[StrPath]] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """
    Reset HEAD, index, or paths. If paths given: `git reset [<mode>] -- <paths>`.
    Otherwise: `git reset [<mode>] [<target>]`. mode is e.g. soft, mixed, hard, merge.
    """
    args: List[str] = ["reset"]
    if mode:
        args.append(mode)
    if paths:
        args.append("--")
        args.extend(_str_paths(paths))
    elif target:
        args.append(target)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_clean(
    *,
    force: bool = False,
    directories: bool = False,
    dry_run: bool = False,
    exclude: Optional[Sequence[str]] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["clean"]
    if force:
        args.append("-f")
    if directories:
        args.append("-d")
    if dry_run:
        args.append("-n")
    if exclude:
        for pattern in exclude:
            args.extend(["-e", pattern])
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_cherry_pick(
    *commits: str,
    abort: bool = False,
    continue_pick: bool = False,
    skip: bool = False,
    no_commit: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["cherry-pick"]
    if abort:
        args.append("--abort")
    if continue_pick:
        args.append("--continue")
    if skip:
        args.append("--skip")
    if no_commit:
        args.append("--no-commit")
    args.extend(commits)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


# --- submodule / config / plumbing ---


def git_submodule(
    action: str,
    *extra: str,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
    init: bool = False,
    recursive: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["submodule", action]
    if init and action == "update":
        args.append("--init")
    if recursive and action == "update":
        args.append("--recursive")
    args.extend(extra)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_config(
    key: Optional[str] = None,
    value: Optional[str] = None,
    *,
    global_: bool = False,
    use_local: bool = False,
    system: bool = False,
    list_all: bool = False,
    unset: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["config"]
    if global_:
        args.append("--global")
    if use_local:
        args.append("--local")
    if system:
        args.append("--system")
    if list_all:
        args.append("--list")
        return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)
    if key and unset:
        args.extend(["--unset", key])
        return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)
    if key and value is not None:
        args.extend([key, value])
    elif key:
        args.append(key)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_rev_parse(
    *rev: str,
    abbrev_ref: Optional[str] = None,
    show_toplevel: bool = False,
    git_dir: bool = False,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["rev-parse"]
    if show_toplevel:
        args.append("--show-toplevel")
    if git_dir:
        args.append("--git-dir")
    if abbrev_ref:
        args.extend(["--abbrev-ref", abbrev_ref])
    args.extend(rev)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_describe(
    *committish: str,
    tags: bool = False,
    always: bool = False,
    abbrev: Optional[int] = None,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    args: List[str] = ["describe"]
    if tags:
        args.append("--tags")
    if always:
        args.append("--always")
    if abbrev is not None:
        args.extend(["--abbrev", str(abbrev)])
    args.extend(committish)
    return run_git(*args, cwd=cwd, check=check, capture_output=capture_output)


def git_worktree(
    action: str,
    *extra: str,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """e.g. git_worktree("add", "../path", "branch"); git_worktree("list")."""
    return run_git("worktree", action, *extra, cwd=cwd, check=check, capture_output=capture_output)


def git_bisect(
    subcommand: str,
    *extra: str,
    cwd: Optional[StrPath] = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """e.g. git_bisect("start"); git_bisect("bad"); git_bisect("good", "abc123"); git_bisect("reset")."""
    return run_git("bisect", subcommand, *extra, cwd=cwd, check=check, capture_output=capture_output)


__all__ = [
    "run_git",
    "git_add",
    "git_blame",
    "git_branch",
    "git_checkout",
    "git_cherry_pick",
    "git_clean",
    "git_clone",
    "git_commit",
    "git_config",
    "git_describe",
    "git_diff",
    "git_fetch",
    "git_init",
    "git_log",
    "git_merge",
    "git_pull",
    "git_push",
    "git_rebase",
    "git_remote",
    "git_reset",
    "git_rev_parse",
    "git_rm",
    "git_show",
    "git_status",
    "git_stash",
    "git_submodule",
    "git_switch",
    "git_tag",
    "git_worktree",
    "git_bisect",
]
