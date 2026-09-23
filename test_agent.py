from app.github.client import get_pr_files
from app.agent.reviewer import review_pr

files = get_pr_files("fastapi/fastapi", 16393)
result = review_pr(files)
print(f"findings: {sum(len(getattr(result, k)) for k in ['logic_issues','security_issues','code_quality','performance_issues','test_coverage'])}")
print(result.summary)