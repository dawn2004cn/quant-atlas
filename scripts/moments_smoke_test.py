from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.application.services.moments_service import MomentsService
from app.config import AppSettings, BASE_DIR
from app.infrastructure.repositories.moments_repository import MomentsRepository


def main() -> None:
    s = AppSettings.from_env()
    repo = (
        MomentsRepository(mysql=s.mysql)
        if s.use_mysql
        else MomentsRepository((BASE_DIR / "instance" / "moments.db").resolve())
    )
    svc = MomentsService(repo)
    out = svc.create_post(
        actor_type="agent",
        actor_id="Macro",
        author_name="Agent·Macro",
        content_text=f"smoke test {datetime.now().strftime('%H:%M:%S')}",
        attachments=[],
        content={"hello": "world"},
        market_date=datetime.now().strftime("%Y-%m-%d"),
    )
    print("create_post:", out)
    feed = svc.list_feed(limit=5, before_post_id=None)
    print("feed_items:", len(feed.get("items") or []))
    if feed.get("items"):
        print(json.dumps(feed["items"][0], ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()

