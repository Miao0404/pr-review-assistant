from unittest.mock import MagicMock, patch

from app.schemas.review import ReviewResult

VALID_REVIEW_DATA = {
    "logic_issues": [],
    "security_issues": [],
    "code_quality": [],
    "performance_issues": [],
    "test_coverage": [],
    "summary": "No issues found.",
}


def make_mock_response(tool_input: dict) -> MagicMock:
    """构造一个假的 Anthropic API 响应对象。"""
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "submit_review"
    tool_use_block.input = tool_input

    response = MagicMock()
    response.content = [tool_use_block]
    response.stop_reason = "tool_use"
    return response


def run_review_pr(tool_input: dict) -> ReviewResult:
    """把所有外部依赖 mock 掉，只跑 unwrap 逻辑。"""
    from app.agent import reviewer

    with patch("app.agent.reviewer.client") as mock_client, \
         patch("app.agent.reviewer.chunk_pr_files", return_value=[]), \
         patch("app.agent.reviewer.embed_chunks",   return_value=[]), \
         patch("app.agent.reviewer.store_chunks"), \
         patch("app.agent.reviewer.search_chunks",  return_value=[]):

        mock_client.messages.create.return_value = make_mock_response(tool_input)
        return reviewer.review_pr([])


def test_direct_response_parses_correctly():
    """Claude 直接返回字段时，能正确解析成 ReviewResult。"""
    result = run_review_pr(VALID_REVIEW_DATA)
    assert isinstance(result, ReviewResult)
    assert result.summary == "No issues found."


def test_wrapped_response_unwraps_correctly():
    """Claude 把字段包在 'review' 键里时，能正确解开并解析。"""
    result = run_review_pr({"review": VALID_REVIEW_DATA})
    assert isinstance(result, ReviewResult)
    assert result.summary == "No issues found."


def test_result_has_all_fields():
    """ReviewResult 包含所有预期字段。"""
    result = run_review_pr(VALID_REVIEW_DATA)
    assert hasattr(result, "logic_issues")
    assert hasattr(result, "security_issues")
    assert hasattr(result, "code_quality")
    assert hasattr(result, "performance_issues")
    assert hasattr(result, "test_coverage")
    assert hasattr(result, "summary")


def test_direct_and_wrapped_produce_same_result():
    """两种 Claude 返回格式最终结果一致。"""
    direct  = run_review_pr(VALID_REVIEW_DATA)
    wrapped = run_review_pr({"review": VALID_REVIEW_DATA})
    assert direct.summary == wrapped.summary
    assert direct.logic_issues == wrapped.logic_issues
