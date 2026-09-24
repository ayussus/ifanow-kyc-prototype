"""Fuzzy name matching used by the Reconcile stage.

Tolerates expanded initials, word order and small spelling differences, and
returns a 0-1 score plus the action the engine takes. In production this would
be a trained entity-resolution model; the thresholds here are illustrative.
"""
import re
from difflib import SequenceMatcher

TITLES = {"MR", "MRS", "MS", "MISS", "DR", "SHRI", "SMT", "KUMARI", "M/S"}
ACCEPT, DECLARE = 0.90, 0.75  # >= ACCEPT auto-accept; >= DECLARE self-declaration; below -> fix at source


ABBR = {"PRIVATE": "PVT", "LIMITED": "LTD", "COMPANY": "CO", "CORPORATION": "CORP", "BROTHERS": "BROS"}


def _tokens(name: str) -> list[str]:
    name = re.sub(r"[^A-Z ]", " ", (name or "").upper())
    return [ABBR.get(t, t) for t in name.split() if t and t not in TITLES]


def _token_score(a: str, b: str, first: bool) -> float:
    if a == b:
        return 0.6 if len(a) == 1 else 1.0          # two identical initials = weak evidence
    if len(a) == 1 or len(b) == 1:
        full, init = (b, a) if len(a) == 1 else (a, b)
        if full[0] == init:
            return 0.5 if first else 0.8             # initial vs full name
        return 0.0
    r = SequenceMatcher(None, a, b).ratio()
    return r if r >= 0.8 else 0.0                    # small spelling differences


def _directional(a: list[str], b: list[str]) -> float:
    if not a:
        return 0.0
    used, total = set(), 0.0
    for i, ta in enumerate(a):
        best, best_j = 0.0, None
        for j, tb in enumerate(b):
            if j in used:
                continue
            s = _token_score(ta, tb, first=(i == 0 or j == 0))
            if s > best:
                best, best_j = s, j
        if best_j is not None:
            used.add(best_j)
        total += best
    return total / len(a)


def name_score(reference: str, other: str) -> float:
    a, b = _tokens(reference), _tokens(other)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    p, r = _directional(a, b), _directional(b, a)
    return round(0 if p + r == 0 else 2 * p * r / (p + r), 2)


def match_action(score: float, source: str) -> dict:
    if score >= ACCEPT:
        return {"level": "ok", "action": f"Accept {source} name automatically; log the variation for audit."}
    if score >= DECLARE:
        return {"level": "warn", "action": f"Ask for a one-line self-declaration now that the {source} name belongs to the same person."}
    return {"level": "fail", "action": f"Name on {source} must be corrected at source; only the tier that needs {source} is blocked."}


def reconcile(reference_name: str, others: dict) -> list[dict]:
    """Compare the PAN name (reference) with names from other sources."""
    rows = []
    for source, nm in others.items():
        if not nm:
            continue
        sc = name_score(reference_name, nm)
        rows.append({"source": source, "name": nm, "score": sc, **match_action(sc, source)})
    return rows
