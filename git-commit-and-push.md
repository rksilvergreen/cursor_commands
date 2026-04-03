# Git commit and push (`@git-commit-and-push`)

Use this command to stage, commit, and push changes to the remote repository with a detailed, conventional-commit-style message.

## How to call `git_commit_and_push`

Use the function **`git_commit_and_push`** in **`commands/git/git_custom_commands.py`**.

It is not this command's job to edit files. If you spot an error, you may mention it, but continue running **`git_commit_and_push`** without editing any files.

## Arguments

All parameters are defined on **`git_commit_and_push`** in **`commands/git/git_custom_commands.py`**: **`path`**, **`message`**, **`stage_all`**, **`push`**, **`remote_name`**, **`set_upstream_if_missing`**, and **`strict_push`**.

Unless the user explicitly specifies an argument, leave it out and let **`git_commit_and_push`** use the default defined in the function. The one required argument is **`message`**, which you must compose before calling the function.

## Composing the commit message

You are responsible for creating the `message` argument. Analyze the staged changes (or the full working tree if staging everything) to determine the appropriate type, scope, and details, then follow the conventions below.

### Type prefixes (conventional commit format):
- `feat:` — New feature
- `fix:` — Bug fix
- `refactor:` — Code refactoring
- `docs:` — Documentation changes
- `test:` — Test changes
- `chore:` — Maintenance tasks
- `style:` — Code style changes (formatting, missing semicolons, etc.)
- `perf:` — Performance improvements

### Message structure:

```
type: brief summary

- Detailed bullet points explaining changes
- Technical details about implementation
- Benefits and improvements
- Any breaking changes or important notes
```

The summary line should be concise (under 50 characters when possible). Include enough detail in the bullet points for meaningful code review and future reference.

Do not add a trailing tool or editor signature to the message (for example `Made-with: Cursor` or any similar line). The `message` passed to `git_commit_and_push` should end with substantive content only.

## What it does

Stages all changes (or works with what is already staged when `stage_all=False`), commits with the provided message, and pushes to the remote when the push succeeds. If there is nothing to commit, it returns immediately. Details and exact Git invocations are in the Python sources.
