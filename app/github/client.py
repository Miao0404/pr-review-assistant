from github import Github
from app.core.config import settings


def get_github_client() -> Github:
    return Github(settings.github_token)


def get_pr_files(repo_full_name: str, pr_number: int) -> list[dict]:
    """
    拉取 PR 里所有改动的文件，返回文件名和 diff 内容。
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    files = []
    for f in pr.get_files():
        files.append({
            "filename": f.filename,
            "status": f.status,        # added / modified / removed
            "patch": f.patch or "",    # diff 内容，删除的文件没有 patch
        })

    return files


def post_review_comment(repo_full_name: str, pr_number: int, body: str) -> None:
    """
    把 review 结果作为评论发回到 PR 上。
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment(body)