"""How much AI one visitor may use per day, and the whole site per month.

docs/AI_ASSISTANT_PLAN.md §5. Two guards, both in the SQLite database on the
Railway volume (app/db.py), so a restart does not reset them:

    ai_usage(day, who, action, count)   per visitor per UTC day per action
    ai_spend(month, usd)                the month's spend, from the usage
                                        counters every reply carries

"who" is the signed-in account when there is one, else the visitor's client
key (app/limits.client_key). Nothing else about a request is stored - no
text, no file, no reply.

The monthly budget is the app's OWN stop, below the spend limit the operator
sets on the Anthropic workspace (the hard stop that holds even if this count
is wrong). Its default is in code; CVSTAND_AI_MONTHLY_USD overrides it on the
server - set by the operator, never by this code.

A use is RESERVED before the call and REFUNDED if the call never reached the
model (no key, provider busy, network) - the user is not charged a use for
our failure. A refusal or a malformed reply was billed, so it stays counted.
"""
from __future__ import annotations

import datetime as _dt
import os

from . import db

DAILY_LIMITS = {"import": 10}
DEFAULT_MONTHLY_USD = 15.0


class LimitReached(Exception):
    pass


class BudgetReached(Exception):
    pass


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _month() -> str:
    return _today()[:7]


def who() -> str:
    from .auth import current_user
    from .limits import client_key

    user = current_user()
    return f"user:{user['id']}" if user is not None else f"ip:{client_key()}"


def monthly_budget() -> float:
    try:
        return float(os.environ.get("CVSTAND_AI_MONTHLY_USD", DEFAULT_MONTHLY_USD))
    except ValueError:
        return DEFAULT_MONTHLY_USD


def month_spend() -> float:
    row = db.query_one("SELECT usd FROM ai_spend WHERE month = ?", (_month(),))
    return float(row["usd"]) if row else 0.0


def check_budget() -> None:
    if month_spend() >= monthly_budget():
        raise BudgetReached()


def used_today(action: str) -> int:
    row = db.query_one("SELECT count FROM ai_usage WHERE day = ? AND who = ? AND action = ?",
                       (_today(), who(), action))
    return int(row["count"]) if row else 0


def reserve(action: str) -> int:
    """Take one use; return how many are left today. Atomic: two requests at
    once cannot both take the last one."""
    limit = DAILY_LIMITS[action]
    cur = db.execute(
        """INSERT INTO ai_usage (day, who, action, count) VALUES (?, ?, ?, 1)
           ON CONFLICT (day, who, action) DO UPDATE SET count = count + 1
           WHERE count < ?""", (_today(), who(), action, limit))
    if cur.rowcount == 0:
        raise LimitReached()
    return limit - used_today(action)


def refund(action: str) -> None:
    db.execute("UPDATE ai_usage SET count = count - 1 WHERE day = ? AND who = ? AND action = ? "
               "AND count > 0", (_today(), who(), action))


def add_spend(usd: float) -> None:
    db.execute("""INSERT INTO ai_spend (month, usd) VALUES (?, ?)
                  ON CONFLICT (month) DO UPDATE SET usd = usd + excluded.usd""",
               (_month(), float(usd)))
