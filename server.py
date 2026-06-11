"""
GitHub MCP Server
Exposes GitHub API operations as MCP tools.
Configuration via .env file.
"""

import os
import base64
from typing import Optional

from dotenv import load_dotenv
from github import Github, GithubException, InputGitAuthor
from mcp.server.fastmcp import FastMCP

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
DEFAULT_OWNER = os.getenv("GITHUB_DEFAULT_OWNER", "")

if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_personal_access_token_here":
    raise EnvironmentError(
        "GITHUB_TOKEN is not set. "
        "Add your Personal Access Token to the .env file."
    )

gh = Github(login_or_token=GITHUB_TOKEN, base_url=GITHUB_API_URL)
mcp = FastMCP("GitHub MCP Server")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(owner: str, repo: str):
    """Return a PyGithub Repository object."""
    return gh.get_repo(f"{owner}/{repo}")


def _fmt_repo(r) -> dict:
    return {
        "id": r.id,
        "full_name": r.full_name,
        "description": r.description,
        "private": r.private,
        "url": r.html_url,
        "default_branch": r.default_branch,
        "stars": r.stargazers_count,
        "forks": r.forks_count,
        "open_issues": r.open_issues_count,
        "language": r.language,
        "created_at": str(r.created_at),
        "updated_at": str(r.updated_at),
    }


def _fmt_issue(i) -> dict:
    return {
        "number": i.number,
        "title": i.title,
        "state": i.state,
        "body": i.body,
        "url": i.html_url,
        "user": i.user.login,
        "labels": [lb.name for lb in i.labels],
        "assignees": [a.login for a in i.assignees],
        "created_at": str(i.created_at),
        "updated_at": str(i.updated_at),
        "closed_at": str(i.closed_at) if i.closed_at else None,
    }


def _fmt_pr(pr) -> dict:
    return {
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "body": pr.body,
        "url": pr.html_url,
        "user": pr.user.login,
        "head": pr.head.ref,
        "base": pr.base.ref,
        "mergeable": pr.mergeable,
        "merged": pr.merged,
        "draft": pr.draft,
        "created_at": str(pr.created_at),
        "updated_at": str(pr.updated_at),
    }


def _fmt_commit(c) -> dict:
    return {
        "sha": c.sha,
        "message": c.commit.message,
        "author": c.commit.author.name,
        "date": str(c.commit.author.date),
        "url": c.html_url,
    }


def _fmt_branch(b) -> dict:
    return {
        "name": b.name,
        "sha": b.commit.sha,
        "protected": b.protected,
    }


def _fmt_comment(c) -> dict:
    return {
        "id": c.id,
        "user": c.user.login,
        "body": c.body,
        "created_at": str(c.created_at),
        "updated_at": str(c.updated_at),
        "url": c.html_url,
    }


# ---------------------------------------------------------------------------
# User tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_authenticated_user() -> dict:
    """Return profile information for the authenticated GitHub user."""
    u = gh.get_user()
    return {
        "login": u.login,
        "name": u.name,
        "email": u.email,
        "bio": u.bio,
        "company": u.company,
        "location": u.location,
        "public_repos": u.public_repos,
        "followers": u.followers,
        "following": u.following,
        "url": u.html_url,
    }


@mcp.tool()
def get_user(username: str) -> dict:
    """Return public profile information for a GitHub user.

    Args:
        username: GitHub username.
    """
    u = gh.get_user(username)
    return {
        "login": u.login,
        "name": u.name,
        "bio": u.bio,
        "company": u.company,
        "location": u.location,
        "public_repos": u.public_repos,
        "followers": u.followers,
        "following": u.following,
        "url": u.html_url,
    }


# ---------------------------------------------------------------------------
# Repository tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_repositories(
    username: Optional[str] = None,
    repo_type: str = "all",
    sort: str = "updated",
    per_page: int = 30,
) -> list[dict]:
    """List repositories for a user or the authenticated user.

    Args:
        username: GitHub username. Omit to use the authenticated user.
        repo_type: Filter type — all, owner, member, public, private.
        sort: Sort order — created, updated, pushed, full_name.
        per_page: Number of results (max 100).
    """
    user = gh.get_user(username) if username else gh.get_user()
    repos = user.get_repos(type=repo_type, sort=sort)
    return [_fmt_repo(r) for r in repos[:per_page]]


@mcp.tool()
def get_repository(owner: str, repo: str) -> dict:
    """Return detailed information about a repository.

    Args:
        owner: Repository owner (user or org).
        repo: Repository name.
    """
    return _fmt_repo(_repo(owner, repo))


@mcp.tool()
def create_repository(
    name: str,
    description: str = "",
    private: bool = False,
    auto_init: bool = True,
    gitignore_template: Optional[str] = None,
    license_template: Optional[str] = None,
) -> dict:
    """Create a new repository for the authenticated user.

    Args:
        name: Repository name.
        description: Short description.
        private: Whether the repo is private.
        auto_init: Initialise with a README.
        gitignore_template: e.g. "Python", "Node".
        license_template: e.g. "mit", "apache-2.0".
    """
    user = gh.get_user()
    kwargs = dict(
        name=name,
        description=description,
        private=private,
        auto_init=auto_init,
    )
    if gitignore_template:
        kwargs["gitignore_template"] = gitignore_template
    if license_template:
        kwargs["license_template"] = license_template
    r = user.create_repo(**kwargs)
    return _fmt_repo(r)


@mcp.tool()
def delete_repository(owner: str, repo: str) -> dict:
    """Delete a repository. Irreversible — use with caution.

    Args:
        owner: Repository owner.
        repo: Repository name.
    """
    _repo(owner, repo).delete()
    return {"deleted": True, "repository": f"{owner}/{repo}"}


@mcp.tool()
def fork_repository(owner: str, repo: str) -> dict:
    """Fork a repository to the authenticated user's account.

    Args:
        owner: Source repository owner.
        repo: Source repository name.
    """
    fork = _repo(owner, repo).create_fork()
    return _fmt_repo(fork)


@mcp.tool()
def search_repositories(
    query: str,
    sort: str = "stars",
    order: str = "desc",
    per_page: int = 20,
) -> list[dict]:
    """Search GitHub repositories.

    Args:
        query: GitHub search query (e.g. 'language:python topic:mcp').
        sort: stars, forks, help-wanted-issues, updated.
        order: asc or desc.
        per_page: Number of results (max 100).
    """
    results = gh.search_repositories(query=query, sort=sort, order=order)
    return [_fmt_repo(r) for r in results[:per_page]]


# ---------------------------------------------------------------------------
# Branch tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_branches(owner: str, repo: str) -> list[dict]:
    """List all branches in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
    """
    return [_fmt_branch(b) for b in _repo(owner, repo).get_branches()]


@mcp.tool()
def get_branch(owner: str, repo: str, branch: str) -> dict:
    """Get details for a specific branch.

    Args:
        owner: Repository owner.
        repo: Repository name.
        branch: Branch name.
    """
    return _fmt_branch(_repo(owner, repo).get_branch(branch))


@mcp.tool()
def create_branch(
    owner: str,
    repo: str,
    new_branch: str,
    from_branch: Optional[str] = None,
) -> dict:
    """Create a new branch from an existing branch or default branch.

    Args:
        owner: Repository owner.
        repo: Repository name.
        new_branch: Name for the new branch.
        from_branch: Source branch name. Defaults to the repo's default branch.
    """
    r = _repo(owner, repo)
    source = from_branch or r.default_branch
    sha = r.get_branch(source).commit.sha
    ref = r.create_git_ref(ref=f"refs/heads/{new_branch}", sha=sha)
    return {"name": new_branch, "sha": ref.object.sha, "source": source}


@mcp.tool()
def delete_branch(owner: str, repo: str, branch: str) -> dict:
    """Delete a branch from a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        branch: Branch name to delete.
    """
    r = _repo(owner, repo)
    ref = r.get_git_ref(f"heads/{branch}")
    ref.delete()
    return {"deleted": True, "branch": branch}


# ---------------------------------------------------------------------------
# Issue tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: Optional[str] = None,
    assignee: Optional[str] = None,
    per_page: int = 30,
) -> list[dict]:
    """List issues in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: open, closed, or all.
        labels: Comma-separated label names to filter by.
        assignee: Filter by assignee login.
        per_page: Number of results (max 100).
    """
    kwargs: dict = {"state": state}
    if labels:
        kwargs["labels"] = [lb.strip() for lb in labels.split(",")]
    if assignee:
        kwargs["assignee"] = assignee
    issues = _repo(owner, repo).get_issues(**kwargs)
    # get_issues returns PRs too; filter them out
    return [_fmt_issue(i) for i in issues if not i.pull_request][:per_page]


@mcp.tool()
def get_issue(owner: str, repo: str, issue_number: int) -> dict:
    """Get a specific issue by number.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number.
    """
    return _fmt_issue(_repo(owner, repo).get_issue(issue_number))


@mcp.tool()
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: Optional[str] = None,
    assignees: Optional[str] = None,
) -> dict:
    """Create a new issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Issue title.
        body: Issue body (Markdown).
        labels: Comma-separated label names.
        assignees: Comma-separated GitHub logins to assign.
    """
    kwargs: dict = {"title": title, "body": body}
    if labels:
        kwargs["labels"] = [lb.strip() for lb in labels.split(",")]
    if assignees:
        kwargs["assignees"] = [a.strip() for a in assignees.split(",")]
    return _fmt_issue(_repo(owner, repo).create_issue(**kwargs))


@mcp.tool()
def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    labels: Optional[str] = None,
    assignees: Optional[str] = None,
) -> dict:
    """Update an existing issue (title, body, state, labels, assignees).

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number.
        title: New title.
        body: New body.
        state: open or closed.
        labels: Comma-separated label names (replaces existing labels).
        assignees: Comma-separated logins (replaces existing assignees).
    """
    issue = _repo(owner, repo).get_issue(issue_number)
    kwargs: dict = {}
    if title is not None:
        kwargs["title"] = title
    if body is not None:
        kwargs["body"] = body
    if state is not None:
        kwargs["state"] = state
    if labels is not None:
        kwargs["labels"] = [lb.strip() for lb in labels.split(",")]
    if assignees is not None:
        kwargs["assignees"] = [a.strip() for a in assignees.split(",")]
    issue.edit(**kwargs)
    return _fmt_issue(issue)


@mcp.tool()
def add_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    body: str,
) -> dict:
    """Add a comment to an issue or pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue or PR number.
        body: Comment text (Markdown).
    """
    issue = _repo(owner, repo).get_issue(issue_number)
    return _fmt_comment(issue.create_comment(body))


@mcp.tool()
def list_issue_comments(
    owner: str,
    repo: str,
    issue_number: int,
    per_page: int = 30,
) -> list[dict]:
    """List comments on an issue or pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue or PR number.
        per_page: Number of results.
    """
    issue = _repo(owner, repo).get_issue(issue_number)
    return [_fmt_comment(c) for c in issue.get_comments()][:per_page]


# ---------------------------------------------------------------------------
# Pull request tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    head: Optional[str] = None,
    base: Optional[str] = None,
    per_page: int = 30,
) -> list[dict]:
    """List pull requests in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: open, closed, or all.
        head: Filter by head branch (user:branch).
        base: Filter by base branch.
        per_page: Number of results (max 100).
    """
    kwargs: dict = {"state": state}
    if head:
        kwargs["head"] = head
    if base:
        kwargs["base"] = base
    prs = _repo(owner, repo).get_pulls(**kwargs)
    return [_fmt_pr(pr) for pr in prs[:per_page]]


@mcp.tool()
def get_pull_request(owner: str, repo: str, pr_number: int) -> dict:
    """Get a specific pull request by number.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: Pull request number.
    """
    return _fmt_pr(_repo(owner, repo).get_pull(pr_number))


@mcp.tool()
def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    draft: bool = False,
) -> dict:
    """Create a new pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: PR title.
        head: Branch containing changes (e.g. 'feature-branch' or 'user:branch').
        base: Branch to merge into (e.g. 'main').
        body: PR description (Markdown).
        draft: Create as a draft PR.
    """
    pr = _repo(owner, repo).create_pull(
        title=title, body=body, head=head, base=base, draft=draft
    )
    return _fmt_pr(pr)


@mcp.tool()
def merge_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    commit_title: Optional[str] = None,
    commit_message: Optional[str] = None,
    merge_method: str = "merge",
) -> dict:
    """Merge a pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: Pull request number.
        commit_title: Title for the merge commit.
        commit_message: Extra detail for the merge commit.
        merge_method: merge, squash, or rebase.
    """
    pr = _repo(owner, repo).get_pull(pr_number)
    kwargs: dict = {"merge_method": merge_method}
    if commit_title:
        kwargs["commit_title"] = commit_title
    if commit_message:
        kwargs["commit_message"] = commit_message
    status = pr.merge(**kwargs)
    return {"merged": status.merged, "message": status.message, "sha": status.sha}


# ---------------------------------------------------------------------------
# File / content tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_file_contents(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
) -> dict:
    """Get the contents of a file in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path inside the repo (e.g. 'src/main.py').
        ref: Branch, tag, or commit SHA. Defaults to the default branch.
    """
    kwargs: dict = {}
    if ref:
        kwargs["ref"] = ref
    content = _repo(owner, repo).get_contents(path, **kwargs)
    decoded = base64.b64decode(content.content).decode("utf-8", errors="replace")
    return {
        "path": content.path,
        "sha": content.sha,
        "size": content.size,
        "encoding": content.encoding,
        "content": decoded,
        "url": content.html_url,
    }


@mcp.tool()
def list_directory_contents(
    owner: str,
    repo: str,
    path: str = "",
    ref: Optional[str] = None,
) -> list[dict]:
    """List files and directories at a given path in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: Directory path. Empty string lists the root.
        ref: Branch, tag, or commit SHA.
    """
    kwargs: dict = {}
    if ref:
        kwargs["ref"] = ref
    items = _repo(owner, repo).get_contents(path, **kwargs)
    if not isinstance(items, list):
        items = [items]
    return [
        {
            "name": i.name,
            "path": i.path,
            "type": i.type,
            "size": i.size,
            "sha": i.sha,
            "url": i.html_url,
        }
        for i in items
    ]


@mcp.tool()
def create_or_update_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: Optional[str] = None,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
) -> dict:
    """Create or update a file in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path inside the repo.
        content: New file content (plain text; will be base64-encoded).
        message: Commit message.
        branch: Target branch. Defaults to the default branch.
        author_name: Commit author name.
        author_email: Commit author email.
    """
    r = _repo(owner, repo)
    kwargs: dict = {}
    if branch:
        kwargs["branch"] = branch
    if author_name and author_email:
        kwargs["author"] = InputGitAuthor(author_name, author_email)

    encoded = base64.b64encode(content.encode()).decode()

    try:
        existing = r.get_contents(path, ref=branch or r.default_branch)
        result = r.update_file(path, message, content, existing.sha, **kwargs)
        action = "updated"
    except GithubException:
        result = r.create_file(path, message, content, **kwargs)
        action = "created"

    return {
        "action": action,
        "path": path,
        "commit_sha": result["commit"].sha,
        "commit_message": result["commit"].commit.message,
    }


@mcp.tool()
def delete_file(
    owner: str,
    repo: str,
    path: str,
    message: str,
    branch: Optional[str] = None,
) -> dict:
    """Delete a file from a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path to delete.
        message: Commit message.
        branch: Branch to delete from. Defaults to the default branch.
    """
    r = _repo(owner, repo)
    ref = branch or r.default_branch
    file_content = r.get_contents(path, ref=ref)
    kwargs: dict = {}
    if branch:
        kwargs["branch"] = branch
    result = r.delete_file(path, message, file_content.sha, **kwargs)
    return {
        "deleted": True,
        "path": path,
        "commit_sha": result["commit"].sha,
    }


# ---------------------------------------------------------------------------
# Commit tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_commits(
    owner: str,
    repo: str,
    branch: Optional[str] = None,
    path: Optional[str] = None,
    author: Optional[str] = None,
    per_page: int = 30,
) -> list[dict]:
    """List commits in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        branch: Branch or SHA to list commits from.
        path: Only commits that modified this path.
        author: Filter by author login or email.
        per_page: Number of results (max 100).
    """
    kwargs: dict = {}
    if branch:
        kwargs["sha"] = branch
    if path:
        kwargs["path"] = path
    if author:
        kwargs["author"] = author
    commits = _repo(owner, repo).get_commits(**kwargs)
    return [_fmt_commit(c) for c in commits[:per_page]]


@mcp.tool()
def get_commit(owner: str, repo: str, sha: str) -> dict:
    """Get details for a specific commit.

    Args:
        owner: Repository owner.
        repo: Repository name.
        sha: Commit SHA.
    """
    c = _repo(owner, repo).get_commit(sha)
    return {
        **_fmt_commit(c),
        "files_changed": [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch,
            }
            for f in c.files
        ],
    }


# ---------------------------------------------------------------------------
# Search tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_code(
    query: str,
    per_page: int = 20,
) -> list[dict]:
    """Search code across GitHub.

    Args:
        query: GitHub code search query (e.g. 'FastMCP repo:anthropics/mcp').
        per_page: Number of results (max 100).
    """
    results = gh.search_code(query=query)
    return [
        {
            "name": r.name,
            "path": r.path,
            "repository": r.repository.full_name,
            "url": r.html_url,
            "sha": r.sha,
        }
        for r in results[:per_page]
    ]


@mcp.tool()
def search_issues(
    query: str,
    sort: str = "created",
    order: str = "desc",
    per_page: int = 20,
) -> list[dict]:
    """Search issues and pull requests across GitHub.

    Args:
        query: GitHub issues search query (e.g. 'is:open label:bug repo:owner/repo').
        sort: comments, reactions, created, updated.
        order: asc or desc.
        per_page: Number of results (max 100).
    """
    results = gh.search_issues(query=query, sort=sort, order=order)
    return [_fmt_issue(i) for i in results[:per_page]]


# ---------------------------------------------------------------------------
# Release tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_releases(owner: str, repo: str, per_page: int = 10) -> list[dict]:
    """List releases for a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        per_page: Number of results.
    """
    releases = _repo(owner, repo).get_releases()
    return [
        {
            "id": r.id,
            "tag_name": r.tag_name,
            "name": r.title,
            "body": r.body,
            "draft": r.draft,
            "prerelease": r.prerelease,
            "created_at": str(r.created_at),
            "published_at": str(r.published_at),
            "url": r.html_url,
        }
        for r in releases[:per_page]
    ]


@mcp.tool()
def create_release(
    owner: str,
    repo: str,
    tag_name: str,
    name: str = "",
    body: str = "",
    draft: bool = False,
    prerelease: bool = False,
    target_commitish: Optional[str] = None,
) -> dict:
    """Create a new release for a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        tag_name: Tag for the release (e.g. 'v1.0.0').
        name: Release title.
        body: Release notes (Markdown).
        draft: Create as a draft.
        prerelease: Mark as a pre-release.
        target_commitish: Branch or SHA the tag should point to.
    """
    kwargs: dict = dict(
        tag=tag_name,
        name=name or tag_name,
        message=body,
        draft=draft,
        prerelease=prerelease,
    )
    if target_commitish:
        kwargs["target_commitish"] = target_commitish
    r = _repo(owner, repo)
    release = r.create_git_release(**kwargs)
    return {
        "id": release.id,
        "tag_name": release.tag_name,
        "name": release.title,
        "url": release.html_url,
        "draft": release.draft,
        "prerelease": release.prerelease,
    }


# ---------------------------------------------------------------------------
# Label tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_labels(owner: str, repo: str) -> list[dict]:
    """List all labels in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
    """
    return [
        {"name": lb.name, "color": lb.color, "description": lb.description}
        for lb in _repo(owner, repo).get_labels()
    ]


@mcp.tool()
def create_label(
    owner: str,
    repo: str,
    name: str,
    color: str,
    description: str = "",
) -> dict:
    """Create a label in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        name: Label name.
        color: Hex colour without '#' (e.g. 'ff0000').
        description: Optional description.
    """
    lb = _repo(owner, repo).create_label(name=name, color=color, description=description)
    return {"name": lb.name, "color": lb.color, "description": lb.description}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    print(f"Starting GitHub MCP Server (transport={transport}) ...")
    mcp.run(transport=transport)
