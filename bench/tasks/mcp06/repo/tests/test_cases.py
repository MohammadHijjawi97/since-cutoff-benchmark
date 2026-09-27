from pathlib import Path

from mcp.types import CallToolResult, TextContent

from mcpcheck.cases import Case, Mismatch, compare, load_cases

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "cases.toml"


def result(text: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=text)])


def test_load_example_cases():
    assert load_cases(EXAMPLES) == [Case("add", {"a": 2, "b": 3}, "5"), Case("greet", {"name": "Ada"}, "Hello, Ada!")]


def test_compare():
    case = Case("greet", {"name": "Ada"}, "Hello, Ada!")
    assert compare(case, result("Hello, Ada!\n")) is None
    assert compare(case, result("Hi Ada")) == Mismatch(case, "Hi Ada")
