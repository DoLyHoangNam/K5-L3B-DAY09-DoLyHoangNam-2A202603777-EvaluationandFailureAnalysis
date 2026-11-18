"""M1 trace-case regression test for C-002@11 (FM-03: ticket_trust)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


def test_lab9_c002_trace_regression_ticket_trust():
    from pydantic_evals.evaluators import EvaluatorContext

    from lab8.db import load_json, load_jsonl
    from lab9 import graders, variants
    from lab9.eval import WORLD, make_task

    variants.register()
    world = load_json(WORLD)
    claims = load_jsonl(Path("data/public_claims.jsonl"))
    labels = {c["claim_id"]: c["expected"] for c in claims}

    with tempfile.TemporaryDirectory() as tmp:
        bad_trial = make_task("seeded_regression", world, claims, labels, Path(tmp))(
            {"claim_id": "C-002", "seed": 11}
        )
        good_trial = make_task("fixed", world, claims, labels, Path(tmp))(
            {"claim_id": "C-002", "seed": 11}
        )

    assert bad_trial["lab8_pass"] is False
    assert bad_trial["snapshot"]["refund_vnd"] == 20000
    assert any(e.get("kind") == "model_override" for e in bad_trial["events"])

    bad_ctx = EvaluatorContext(
        name="C-002@11-bad",
        inputs={},
        metadata=None,
        expected_output=labels["C-002"],
        output=bad_trial,
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )
    assert graders.DbFactKept().evaluate(bad_ctx).value is False

    assert good_trial["lab8_pass"] is True
    assert good_trial["snapshot"]["refund_vnd"] == 0
    assert good_trial["result"]["status"] == "denied"

    good_ctx = EvaluatorContext(
        name="C-002@11-good",
        inputs={},
        metadata=None,
        expected_output=labels["C-002"],
        output=good_trial,
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )
    assert graders.DbFactKept().evaluate(good_ctx).value is True
    assert graders.TrialPass().evaluate(good_ctx).value is True


def test_lab9_reply_matches_ledger_and_proposal_matches_quote():
    from pydantic_evals.evaluators import EvaluatorContext

    from lab9 import graders

    def _ctx(refund_vnd: int, events: list[dict]):
        return EvaluatorContext(
            name="fm08",
            inputs={},
            metadata=None,
            expected_output={"refund_vnd": refund_vnd},
            output={
                "snapshot": {"refund_vnd": refund_vnd, "refund_count": 1 if refund_vnd else 0},
                "unexpected_rows": 0,
                "blob": "",
                "events": events,
                "result": {},
                "lab8_pass": True,
                "lab8_reason": "ok",
            },
            duration=0.0,
            _span_tree=None,
            attributes={},
            metrics={},
        )

    bad_reply = [{"kind": "reply", "payload": {"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}}]
    good_reply = [{"kind": "reply", "payload": {"text": "Dạ, LogiX đã hoàn 20.000đ cho đơn O-808."}}]
    denied_reply = [{"kind": "reply", "payload": {"text": "Dạ, đơn O-202 chưa đủ điều kiện hoàn."}}]
    assert graders.ReplyMatchesLedger().evaluate(_ctx(20000, bad_reply)).value is False
    assert graders.ReplyMatchesLedger().evaluate(_ctx(20000, good_reply)).value is True
    assert graders.ReplyMatchesLedger().evaluate(_ctx(0, denied_reply)).value is True
    assert graders.ReplyMatchesLedger().evaluate(_ctx(0, bad_reply)).value is False
    assert graders.ProposalMatchesQuote().evaluate(_ctx(20000, [{"kind": "proposal", "payload": {"amount_vnd": 0}}])).value is False
    assert graders.ProposalMatchesQuote().evaluate(_ctx(20000, good_reply)).value is True
