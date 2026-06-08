# Git history reinitialization (`@git-reinit`)

Use this command to collapse an existing repo's entire history into a single fresh commit, reproducing the **main** / **develop** layout that `@git-init` produces, but using the project's current content and keeping the existing remote.

## Confirm before running

This command is destructive, so do not run it immediately. When the user invokes it, first respond with a brief confirmation request that states the repercussions concisely:

- The entire commit history is rewritten into a single commit. The old history is **not** backed up — once the rewrite is pushed and garbage-collected, it is gone.
- The remote is overwritten with a force-push, and every other remote branch and all remote tags are deleted.
- Anyone else using the repo must re-clone.

Then ask whether they are sure they want to proceed. Only run **`git_reinit`** after the user explicitly confirms; if they decline or do not clearly confirm, do not run it.

## How to call `git_reinit`

Use the function **`git_reinit`** in **`commands/git/git_custom_commands.py`**.

It is not this command's job to edit files. If you spot an error, you may mention it, but continue running **`git_reinit`** without editing any files.

## Arguments

All parameters are defined on **`git_reinit`** in **`commands/git/git_custom_commands.py`**: **`path`**, **`main_branch`**, **`develop_branch`**, **`initial_commit_message`**, **`remote_name`**, **`push`**, **`prune_remote`**, **`use_force_with_lease`**, and **`strict_push`**.

Unless the user explicitly specifies an argument, leave it out and let **`git_reinit`** use the default defined in the function.

## What it does

Rewrites history in place using an orphan branch — it never moves or deletes `.git`. It creates an orphan branch, stages the current working tree (including submodule gitlinks), and commits it as a single commit. It then deletes every other local branch, renames the orphan to `main`, creates `develop` from it, and checks out `develop`. If a remote is configured, `main` and `develop` are force-pushed (with `--force-with-lease` by default); with `prune_remote` it then deletes every other remote branch and all remote tags so the remote mirrors the clean state. The old history is not preserved — there is no backup.

## Submodules

Because history is rewritten in place rather than by relocating `.git`, submodule registration and `.git/modules` are preserved, so submodules keep working. The command refuses to run if any submodule has uncommitted changes, since a rewrite would silently discard them; commit and push those inside the submodule first.

Note: this command's own code lives in the `commands/shared` submodule (a separate repository). Edits to it only persist if they are committed and pushed in that submodule — committing in the superproject does not save them. GitHub may also refuse to delete a remote branch that is still the repository's default branch; that is recorded as a warning rather than failing the run.
