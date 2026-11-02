"""The team activity feed: every note and update the sales team has saved,
across all customers, newest first — so anyone can see which customers were
contacted and when. Read fresh per request, like the notes themselves."""
from typing import List

from constants.activity import ACTIVITY_LIMIT
from utils.intel import all_updates
from utils.recommend import all_profiles


def activity_payload(limit: int = ACTIVITY_LIMIT) -> List[dict]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    profiles = all_profiles()
    feed = []
    for u in all_updates()[:limit]:
        profile = profiles.get(u.customer_code)
        feed.append({
            "id": u.id,
            "code": u.customer_code,
            # A note can outlive its customer in Unleashed: show the code, don't link.
            "name": profile.customer.name if profile else u.customer_code,
            "known": profile is not None,
            "ts": u.ts,
            "source": u.source,
            "hooks": u.hooks,
            "advice": u.advice,
        })
    return feed
