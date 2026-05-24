# Git merge to main (`@git-merge-to-main`)

Use this command to merge the current branch into main with a versioned merge commit, tag the release, and push.

## How to call `git_merge_to_main`

Use the function **`git_merge_to_main`** in **`commands/git/git_custom_commands.py`**.

It is not this command's job to edit files directly. If you spot an error, you may mention it, but continue running **`git_merge_to_main`** without editing any files. File modifications that are part of the release workflow (version bumps, changelog updates) should be handled through a **`prepare_release`** callback instead.

## Arguments

All parameters are defined on **`git_merge_to_main`** in **`commands/git/git_custom_commands.py`**: **`path`**, **`version`**, **`main_branch`**, **`remote_name`**, **`tag_prefix`**, **`commit_uncommitted`**, **`pre_merge_commit_message`**, **`prepare_release`**, **`release_commit_message`**, **`merge_commit_message`**, **`tag_message`**, **`push`**, and **`strict_push`**.

Unless the user explicitly specifies an argument, leave it out and let **`git_merge_to_main`** use the default defined in the function. The one required argument is **`version`**, which the user must provide when invoking the command — do not invent a version yourself.

## What it does

Commits any uncommitted changes on the current branch and pushes the source branch. If a **`prepare_release`** callback is provided, it is invoked next to perform release-preparation changes (such as version bumps or changelog updates); those changes are then committed and pushed automatically. Once the source branch is ready, checks out main, merges with `--no-ff`, creates an annotated tag, pushes main and tags, and returns to the source branch. The merge commit message, tag name, and tag annotation are derived from the `version` argument by default. Details and exact Git invocations are in the Python sources.
