"""Fireworks client + agent pipeline tests with a mocked transport.

No network, no credentials: the transport is injected, so these tests
exercise the exact code path that will run live once credits land.
"""

import json

from app.agent import process
from app.model.fireworks_client import (FireworksClient, ModelNotConfigured,
                                        _extract_json)


def make_client(reply_content: str) -> FireworksClient:
    """Client whose 'API' always answers with the given message content."""
    def transport(payload):
        # Sanity: payload must look like a chat-completions request.
        assert payload["messages"][0]["role"] == "system"
        return {"choices": [{"message": {"content": reply_content}}]}
    return FireworksClient(transport=transport)


# --- JSON extraction ---------------------------------------------------------

def test_extract_plain_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert _extract_json('Here you go:\n{"a": 1}\nDone.') == {"a": 1}


def test_extract_garbage_returns_none():
    assert _extract_json("no json here") is None


# --- client ------------------------------------------------------------------

def test_unconfigured_client_raises():
    client = FireworksClient()          # real transport, no env credentials
    if client.is_configured:            # skip if the dev has real creds set
        return
    try:
        client.rewrite_to_comply("text", [])
        raise AssertionError("expected ModelNotConfigured")
    except ModelNotConfigured:
        pass


def test_rewrite_parses_model_json():
    reply = json.dumps({"rewritten": "1. Fixed text.",
                        "change_log": ["UN-NUM-003: numbered paragraph"]})
    client = make_client(reply)
    out = client.rewrite_to_comply("draft", [{"rule_id": "UN-NUM-003"}])
    assert out["rewritten"] == "1. Fixed text."
    assert out["change_log"] == ["UN-NUM-003: numbered paragraph"]


def test_rewrite_rejects_garbage_response():
    client = make_client("I cannot help with that.")
    try:
        client.rewrite_to_comply("draft", [])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_thinking_prose_before_json_is_handled():
    """Reasoning models often narrate before the JSON — extraction must
    find the answer anyway (the exact failure seen in live testing)."""
    reply = ("Let me analyze the document and the violation. The violation "
             "is about paragraph numbering coverage.\n\n"
             + json.dumps({"rewritten": "1. Fixed.", "change_log": ["x"]}))
    out = make_client(reply).rewrite_to_comply("draft", [])
    assert out["rewritten"] == "1. Fixed."


def test_think_tags_stripped():
    reply = ("<think>internal musing here</think>"
             + json.dumps({"rewritten": "ok", "change_log": []}))
    out = make_client(reply).rewrite_to_comply("draft", [])
    assert out["rewritten"] == "ok"


def test_reasoning_content_fallback():
    """MiniMax-style responses may omit 'content'; fall back gracefully."""
    def transport(payload):
        return {"choices": [{"message": {"reasoning_content":
                json.dumps({"rewritten": "ok", "change_log": []})}}]}
    client = FireworksClient(transport=transport)
    out = client.rewrite_to_comply("draft", [])
    assert out["rewritten"] == "ok"


def test_empty_content_gives_clear_error():
    def transport(payload):
        return {"choices": [{"message": {"content": ""},
                             "finish_reason": "length"}]}
    client = FireworksClient(transport=transport)
    try:
        client.rewrite_to_comply("draft", [])
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "finish_reason=length" in str(e)


def test_answer_question():
    client = make_client("It is covered in paragraph 2.")
    ans = client.answer_question("Where is the budget covered?", "1. ...")
    assert "paragraph 2" in ans


# --- agent pipeline ------------------------------------------------------------

# Three unnumbered body paragraphs (>=20 words each) so UN-NUM-001 remains
# an ERROR after autofix — that is what routes the pipeline to the model.
SAMPLE = """I. INTRODUCTION

The present report of the UN mission covers developments in Vietnam during
the reporting period and is submitted for the consideration of the relevant
intergovernmental bodies of the Organization.

The mission received 5 mandates during the reporting period under review,
and continued its work with partners in the region as described below in
this report to the General Assembly session.

Cooperation with regional organizations remained strong throughout the
period, and the mission continued to coordinate closely with all relevant
entities in the region on matters within its mandate.
"""


def test_pipeline_without_model():
    result = process(SAMPLE, use_model=False)
    assert result["model_used"] is False
    assert result["autofix_log"]                        # autofix did work
    assert "United Nations" in result["text"]           # UN expanded
    assert "Viet Nam" in result["text"]                 # UNTERM fixed


def test_pipeline_with_mock_model_fixes_remaining():
    # The mock model "fixes" whatever remains by returning a compliant doc.
    compliant = ("I. Introduction\n\n"
                 "1. The present report of the United Nations mission covers "
                 "events in Viet Nam during the period under review.\n\n"
                 "2. The mission received five mandates and continued its "
                 "work with partners as described in the present report.")
    reply = json.dumps({"rewritten": compliant,
                        "change_log": ["UN-NUM-001: numbered body paragraphs"]})
    result = process(SAMPLE, client=make_client(reply))
    assert result["model_used"] is True
    assert result["model_log"] == ["UN-NUM-001: numbered body paragraphs"]
    assert result["summary"]["errors"] == 0
    assert result["text"].startswith("I. Introduction")


def test_regression_guard_rejects_worse_rewrite():
    """If the model's rewrite scores WORSE than the deterministic result,
    the pipeline must keep the deterministic text (live-testing bug:
    2 warnings before AI pass became 9 errors after)."""
    worse = ("I. INTRODUCTION IN SHOUTING CAPS\n\n"
             "3. A paragraph numbered wrongly out of sequence in Vietnam.\n\n"
             "7. Another with USD 500 and 'single quotes' and organise.")
    reply = json.dumps({"rewritten": worse, "change_log": ["made it worse"]})
    result = process(SAMPLE, client=make_client(reply))
    assert result["model_used"] is False
    assert "rejected by verification" in (result["model_error"] or "")
    assert "Viet Nam" in result["text"]        # deterministic result kept


def test_pipeline_degrades_when_model_fails():
    def broken_transport(payload):
        raise OSError("network unreachable")
    client = FireworksClient(transport=broken_transport)
    result = process(SAMPLE, client=client)
    assert result["model_used"] is False
    assert result["model_error"] is not None
    assert "Viet Nam" in result["text"]     # autofix results preserved
