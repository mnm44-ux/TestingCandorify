"""Accuracy scoring: compares check-engine findings to the generator answer key.

Reports precision, recall, and false-positive rate. Target for the prototype:
recall >= 0.95 with a false-positive rate < 0.05.

Matching rule: a finding is a true positive if there exists an answer-key entry
of the same ``kind`` whose line positions overlap the finding's line positions
(total_mismatch matches on kind alone, since it has no specific line).
"""
from __future__ import annotations

from dataclasses import dataclass

from .engine import Finding


@dataclass
class AnswerItem:
    kind: str
    line_positions: list[int]


@dataclass
class ScoreResult:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0

    @property
    def false_positive_rate(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.false_positives / denom if denom else 0.0


def _matches(finding: Finding, answer: AnswerItem) -> bool:
    if finding.kind != answer.kind:
        return False
    if finding.kind == "total_mismatch":
        return True
    return bool(set(finding.line_positions) & set(answer.line_positions))


def score_bill(findings: list[Finding], answers: list[AnswerItem]) -> ScoreResult:
    matched_answers: set[int] = set()
    tp = 0
    fp = 0

    for finding in findings:
        hit = False
        for ai, answer in enumerate(answers):
            if ai in matched_answers:
                continue
            if _matches(finding, answer):
                matched_answers.add(ai)
                hit = True
                break
        if hit:
            tp += 1
        else:
            fp += 1

    fn = len(answers) - len(matched_answers)
    return ScoreResult(true_positives=tp, false_positives=fp, false_negatives=fn)


def aggregate(results: list[ScoreResult]) -> ScoreResult:
    return ScoreResult(
        true_positives=sum(r.true_positives for r in results),
        false_positives=sum(r.false_positives for r in results),
        false_negatives=sum(r.false_negatives for r in results),
    )
