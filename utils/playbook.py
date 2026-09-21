"""The rep playbook — ideas a rep came up with themselves, reused elsewhere.

Christina's case: the rep doesn't run any of the suggested pitches and does
something of their own instead. Today that idea dies on that one visit. Here it
is recorded against the situation it was used in (the customer's RFM segment
plus the ranges they buy) and offered to other customers in the same situation,
labelled with where it came from so the rep can see whose idea they're running.

An idea then learns from the same accept/skip taps as everything else, but
GLOBALLY: `confidence` climbs with each rep who takes it up and falls with each
one who skips it, and below RETIRE_BELOW it stops being offered at all. That is
the difference between a shared playbook and a noticeboard.

Stored one file per idea under the feedback dir, so the deployed persistent
disk covers it without another env var.
"""
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from constants.config import PLAYBOOK_DIR
from constants.playbook import (
    ACCEPT_STEP,
    CONFIDENCE_START,
    IDEA_GROUPS,
    MAX_BORROWED_IDEAS,
    MAX_CONFIDENCE,
    MAX_DETAIL_LENGTH,
    MAX_IDEA_LENGTH,
    MAX_OWN_IDEAS,
    MIN_CONFIDENCE,
    MIN_IDEA_LENGTH,
    MIN_SHARED_GROUPS,
    REJECT_STEP,
    RETIRE_BELOW,
    IdeaField,
    IdeaOrigin,
)


@dataclass
class Idea:
    id: str
    title: str
    detail: str
    groups: Tuple[str, ...]      # the ranges the origin customer buys
    segment: str                 # Segment.name at the time it was written
    origin_code: str
    origin_name: str
    ts: str
    accepted: int = 0
    rejected: int = 0

    @property
    def confidence(self) -> float:
        """How far this idea has earned the right to travel."""
        raw = CONFIDENCE_START + ACCEPT_STEP * self.accepted - REJECT_STEP * self.rejected
        return max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, round(raw, 3)))

    @property
    def retired(self) -> bool:
        """Nobody takes it up — stop putting it in front of new customers."""
        return self.confidence < RETIRE_BELOW

    @property
    def when(self) -> str:
        return self.ts[:10]


def _path(idea_id: str) -> str:
    return os.path.join(PLAYBOOK_DIR, f"{idea_id}.json")


def _read(idea_id: str) -> Optional[Idea]:
    try:
        with open(_path(idea_id), encoding="utf-8") as fh:
            d = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    d[IdeaField.GROUPS] = tuple(d.get(IdeaField.GROUPS, ()))
    known = {k: d[k] for k in Idea.__dataclass_fields__ if k in d}
    try:
        return Idea(**known)
    except TypeError:
        return None


def _write(idea: Idea) -> Idea:
    os.makedirs(PLAYBOOK_DIR, exist_ok=True)
    with open(_path(idea.id), "w", encoding="utf-8") as fh:
        json.dump({**asdict(idea), IdeaField.GROUPS: list(idea.groups)}, fh, indent=2)
    return idea


def load_all() -> List[Idea]:
    """Every idea ever written, newest first."""
    try:
        names = os.listdir(PLAYBOOK_DIR)
    except FileNotFoundError:
        return []
    ideas = []
    for name in names:
        idea_id, ext = os.path.splitext(name)
        if ext == ".json":
            idea = _read(idea_id)
            if idea:
                ideas.append(idea)
    return sorted(ideas, key=lambda i: i.ts, reverse=True)


def record(profile, title: str, detail: str = "") -> Idea:
    """File what the rep actually pitched, against the situation they were in."""
    title = " ".join((title or "").split())
    if len(title) < MIN_IDEA_LENGTH:
        raise ValueError("Give the idea a title — one line is enough.")
    groups = tuple(g.name for g in profile.bought_groups[:IDEA_GROUPS])
    return _write(Idea(
        id=uuid.uuid4().hex[:10],
        title=title[:MAX_IDEA_LENGTH],
        detail=" ".join((detail or "").split())[:MAX_DETAIL_LENGTH],
        groups=groups,
        segment=profile.segment.name,
        origin_code=profile.customer.code,
        origin_name=profile.customer.name,
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    ))


def note_outcome(idea_id: str, accepted: bool) -> Optional[Idea]:
    """A rep took the idea up, or skipped it — the only thing that moves an
    idea's reach."""
    idea = _read(idea_id)
    if not idea:
        return None
    if accepted:
        idea.accepted += 1
    else:
        idea.rejected += 1
    return _write(idea)


def _similar(idea: Idea, profile) -> bool:
    """Same segment and at least one range in common — see constants/playbook.py
    for why this is deliberately narrow."""
    if idea.segment != profile.segment.name:
        return False
    shared = set(idea.groups) & set(profile.bought_group_names)
    return len(shared) >= MIN_SHARED_GROUPS


def for_customer(profile) -> List[Tuple[Idea, IdeaOrigin]]:
    """The rep's own ideas for this customer, then ideas borrowed from similar
    ones (best-earned first)."""
    own, borrowed = [], []
    for idea in load_all():
        if idea.origin_code == profile.customer.code:
            own.append(idea)
        elif not idea.retired and _similar(idea, profile):
            borrowed.append(idea)
    borrowed.sort(key=lambda i: (-i.confidence, i.ts))
    return ([(i, IdeaOrigin.OWN) for i in own[:MAX_OWN_IDEAS]]
            + [(i, IdeaOrigin.BORROWED) for i in borrowed[:MAX_BORROWED_IDEAS]])
