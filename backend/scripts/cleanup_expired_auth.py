"""Explicit bounded cleanup of expired authentication state; no scheduler."""

import argparse
import json

from app.auth.session_store import SessionStore
from app.database.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 10_000:
        parser.error("--batch-size must be between 1 and 10000")
    with SessionLocal() as db:
        print(json.dumps(SessionStore(db).cleanup_expired(batch_size=args.batch_size), sort_keys=True))


if __name__ == "__main__":
    main()
