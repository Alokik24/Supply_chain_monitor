# Git & GitHub Quick Reference

## 1. How Git Works

### Git Uses Snapshots

Git stores the state of the entire project at each commit rather than tracking individual line changes.

### The Three Areas of Git

#### Working Directory

Files you are currently editing.

#### Staging Area (Index)

Changes selected for the next commit.

```bash
git add <file>
```

#### Local Repository

Permanent history stored inside `.git/`.

```bash
git commit -m "<message>"
```

---

# 2. Basic Local Workflow

### Initialize a Repository

Use when starting Git tracking in an existing project.

```bash
git init
```

### Check Current State

Use before almost every Git operation.

```bash
git status
```

Shows:

* Modified files
* Staged files
* Untracked files
* Current branch

### Stage Changes

Use when you want specific changes included in the next commit.

```bash
git add <file>
```

Stage all changes:

```bash
git add .
```

### Create a Commit

Use when a logical unit of work is complete.

```bash
git commit -m "<message>"
```

Example:

```bash
git commit -m "Add user authentication"
```

### View Changes Before Committing

Use to inspect modifications.

```bash
git diff
```

Compare staged changes:

```bash
git diff --staged
```

### View Commit History

Use when reviewing project history.

```bash
git log
```

Compact version:

```bash
git log --oneline
```

---

# 3. Branching Workflow

## Why Branches?

Branches allow independent development without affecting stable code.

---

### Create a New Branch

Use before starting a feature, bug fix, or experiment.

```bash
git checkout -b <branch-name>
```

Example:

```bash
git checkout -b feature/login
```

---

### View Available Branches

```bash
git branch
```

Current branch is marked with `*`.

---

### Switch Branches

Use when moving between lines of development.

```bash
git checkout <branch-name>
```

Example:

```bash
git checkout main
```

---

### Merge a Branch

Use after feature development is complete.

```bash
git checkout main
git merge <branch-name>
```

Example:

```bash
git merge feature/login
```

---

### Delete a Branch

Use after successful merge.

```bash
git branch -d <branch-name>
```

Force delete:

```bash
git branch -D <branch-name>
```

---

# 4. Merge Conflicts

## Why Conflicts Happen

Two branches modify the same portion of a file differently.

Git cannot determine the correct version automatically.

Example:

```text
<<<<<<< HEAD
current_branch_code
=======
incoming_branch_code
>>>>>>> feature-branch
```

## Resolution Process

1. Open the conflicted file.
2. Choose the correct code.
3. Remove conflict markers.
4. Save the file.

Finalize:

```bash
git add <resolved-file>
git commit -m "Resolve merge conflict"
```

---

# 5. Connecting Git to GitHub

## Create a Remote Connection

Use after creating a repository on GitHub.

```bash
git remote add origin <repository-url>
```

Example:

```bash
git remote add origin https://github.com/user/project.git
```

Verify:

```bash
git remote -v
```

---

## Push Code to GitHub

### First Push

```bash
git push -u origin main
```

What it does:

* Uploads local commits
* Creates remote branch if needed
* Links local branch to remote branch

The 
```
`-u`
```
 flag establishes tracking.

After this:

```bash
git push
```

is enough.

---

## Pull Latest Changes

Use before starting work or when collaborating.

```bash
git pull
```

What it does:

1. Downloads remote changes
2. Merges them into your local branch

---

## Fetch Without Merging

Use when you want to inspect remote changes first.

```bash
git fetch
```

Difference:

```text
git fetch  -> Download only
git pull   -> Download + Merge
```

---

# 6. Typical Solo Developer Workflow

Start work:

```bash
git pull
```

Create feature branch:

```bash
git checkout -b feature/new-feature
```

Develop code.

Check changes:

```bash
git status
git diff
```

Commit work:

```bash
git add <files>
git commit -m "<message>"
```

Push branch:

```bash
git push -u origin feature/new-feature
```

Merge into main:

```bash
git checkout main
git merge feature/new-feature
```

Push updated main:

```bash
git push
```

Delete feature branch:

```bash
git branch -d feature/new-feature
```

---

# 7. Most Common Commands and When to Use Them

| Situation               | Command                     |
| ----------------------- | --------------------------- |
| Check repository state  | `git status`                |
| See modified code       | `git diff`                  |
| Stage changes           | `git add <file>`            |
| Save work permanently   | `git commit -m "<message>"` |
| View history            | `git log --oneline`         |
| Create a branch         | `git checkout -b <branch>`  |
| Switch branch           | `git checkout <branch>`     |
| Merge feature           | `git merge <branch>`        |
| Upload to GitHub        | `git push`                  |
| Download latest changes | `git pull`                  |
| Inspect remote changes  | `git fetch`                 |
| View branches           | `git branch`                |
| Delete merged branch    | `git branch -d <branch>`    |
| View remotes            | `git remote -v`             |

---

# 8. Git vs GitHub

### Git

A distributed version control system installed locally.

Responsibilities:

* Track file history
* Create commits
* Create branches
* Merge code

Examples:

```bash
git commit
git branch
git merge
```

### GitHub

A cloud platform that hosts Git repositories.

Responsibilities:

* Remote repository storage
* Collaboration
* Pull Requests
* Code Reviews
* CI/CD integrations

Examples:

```text
Git      → Version control engine
GitHub   → Hosting and collaboration platform
```

You can use Git without GitHub, but GitHub relies on Git underneath.
