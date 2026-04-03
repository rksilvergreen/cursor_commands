# Git repository initialization (`@git-init`)

Use this command to initialize a local Git repo with a **main** / **develop** layout and, by default, a matching GitHub repo.

## How to call `git_init`

Use the function **`git_init`** in **`commands/git/git_custom_commands.py`**.

It is not this command's job to edit files. If you spot an error, you may mention it, but continue running **`git_init`** without editing any files.

## Arguments

All parameters are defined on **`git_init`** in **`commands/git/git_custom_commands.py`**: **`path`**, **`repository_name`**, **`main_branch`**, **`develop_branch`**, **`initial_commit_message`**, **`remote_name`**, **`create_github_repository`**, **`github_public`**, **`github_license`**, **`github_description`**, **`github_cli_executable`**, **`continue_without_github_if_cli_unavailable`**, **`strict_github`**, **`existing_repository`**, and **`reinitialize_backup_git_dir`**.

Unless the user explicitly specifies an argument, leave it out and let **`git_init`** use the default defined in the function.

## GitHub

`git_init` uses **`gh`** for the GitHub portion of the workflow. The function does not call MCP itself.

If anything in that GitHub flow fails (CLI missing, auth, `gh repo create`, or push), **complete the setup using the GitHub MCP server** plus normal Git from the repo root:

1. **Create the repository on GitHub** so it matches the intended setup and does not introduce a remote-only initial commit.
2. **Connect the local repository to that GitHub repository** if the remote was not created correctly.
3. **Publish the local branches and finish in the same final state** that a successful `git_init` run would have produced.

Use the **GitHub MCP server** for whichever of these steps require GitHub’s API (typically creating the repo, if `gh` did not); use **Git** for the remote and the pushes.

## What it does

Ensures a repository exists (or follows the existing-repository behavior), stages and commits as needed, creates the standard local branch layout, publishes to GitHub when that part of the flow runs successfully, and leaves the working tree in the expected final branch. Details and exact Git invocations are in the Python sources.

