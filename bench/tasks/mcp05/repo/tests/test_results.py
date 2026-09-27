from mcp.types import CallToolResult, TextContent

from kb.results import split_titles


def test_split_titles_ignores_blank_lines():
    result = CallToolResult(content=[TextContent(type="text", text="Rotating API keys\n\n  Onboarding \n")])
    assert split_titles(result) == ["Rotating API keys", "Onboarding"]


def test_split_titles_empty():
    assert split_titles(CallToolResult(content=[])) == []
