"""Tests for AI bill extraction from PII-redacted text (mocked LLM, no network)."""
from __future__ import annotations

from app.llm import LLMUnavailable
from app.pdf.extract import extract_bill

GOOD = (
    '{"provider_name":"St. Mary\'s Hospital","service_date":"2026-05-14",'
    '"stated_total":105.00,"line_items":['
    '{"code":"85025","code_system":"CPT","description":"CBC","quantity":1,'
    '"unit_price":60.0,"line_total":60.0,"plain_english":"Complete blood count"},'
    '{"code":"80053","description":"Panel","quantity":1,"unit_price":45.0,'
    '"line_total":45.0,"plain_english":"Blood chemistry"},'
    '{"code":"NOPE","description":"invalid code, must be dropped","unit_price":9}]}'
)


class FakeLLM:
    def __init__(self, resp):
        self.resp = resp

    def generate(self, prompt, **kw):
        return self.resp


class DownLLM:
    def generate(self, *a, **k):
        raise LLMUnavailable("down")


def test_extracts_valid_lines_and_metadata():
    b = extract_bill("redacted text", llm_client=FakeLLM(GOOD))
    assert b is not None
    assert b.provider_name.startswith("St. Mary")
    assert b.service_date == "2026-05-14"
    assert b.stated_total == 105.0
    codes = [li.code for li in b.line_items]
    assert codes == ["85025", "80053"]  # NOPE dropped — never fabricated
    assert b.line_items[0].plain_english == "Complete blood count"


def test_code_fence_is_stripped():
    fenced = "```json\n" + GOOD + "\n```"
    b = extract_bill("x", llm_client=FakeLLM(fenced))
    assert b is not None and len(b.line_items) == 2


def test_returns_none_when_llm_down():
    assert extract_bill("x", llm_client=DownLLM()) is None


def test_returns_none_on_garbage():
    assert extract_bill("x", llm_client=FakeLLM("sorry, I cannot help")) is None


def test_returns_none_when_no_valid_lines():
    resp = '{"provider_name":"X","line_items":[{"code":"ZZZ","unit_price":5}]}'
    assert extract_bill("x", llm_client=FakeLLM(resp)) is None
