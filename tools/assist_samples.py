"""PHASE 2 — the Arabic quality gate for the AI assistant. A STOP/GO.

WHY THIS EXISTS

    `AI_ASSISTANT_PLAN.md` §5 makes Phase 2 a gate rather than a checkbox: if
    the Arabic reads as translated rather than written, the prompt in
    `app/assist.py::_SYSTEM` is reworked BEFORE four more features are built on
    top of it. Cheap now, expensive later.

    The gate cannot be automated. There is no test that distinguishes "correct
    Arabic" from "Arabic a native speaker would actually write on a CV" — that
    judgement is the whole point, and it belongs to a human who reads Arabic.
    So this script does not grade anything. It produces the twenty pairs and
    lays them out so the judgement is cheap to make, then gets out of the way.

WHAT IT DOES

    1. Runs each case in CASES through `app.assist.adapt` — the real prompt and
       the real model, not a copy. If this file and the app ever disagree, the
       gate is measuring the wrong thing.
    2. Writes `tools/assist_review.html`: source and result side by side, each
       with the right `dir` and a real Arabic face, plus the four failure modes
       as checkboxes so a reviewer marks rather than composes.
    3. Reports MEASURED cost and cache behaviour, which answers the two things
       `AI_ASSISTANT_PLAN.md` §4 flags as estimated rather than observed — the
       ~1.1¢/assist figure excludes thinking tokens, and a short prefix
       silently does not cache.

    Usage:
        venv/Scripts/python tools/assist_samples.py            # run for real
        venv/Scripts/python tools/assist_samples.py --dry-run  # no API calls
        venv/Scripts/python tools/assist_samples.py --only 3 7 # just those ids

    Needs ANTHROPIC_API_KEY. It costs real money — roughly 20 assists, so a few
    tens of cents. The exact number is printed at the end, which is rather the
    point.

WHAT TO LOOK FOR, IN PRIORITY ORDER

    1. INVENTED FACTS. The one unrecoverable failure. A CV is a factual claim
       made by a named person to an employer; a plausible addition is worse
       than a clumsy sentence. Cases 9 and 10 are deliberately weak lines that
       invite improvement — if either comes back stronger than it went in, the
       prompt has failed regardless of how good the Arabic is.
    2. READS AS TRANSLATED. Arabic words in English sentence structure. This is
       the failure the whole feature exists to avoid.
    3. NUMBERS, NAMES AND LATIN SCRIPT. Case 2 carries $3.2M and a count;
       case 5 carries tool names that belong in Latin script on an Arabic CV.
    4. REGISTER. Professional Arabic CV prose is plainer than English CV prose.
       Ornate is wrong here, not merely different.

    Cases 11 and 12 are already in the target language: the correct answer is
    the input, unchanged. A paraphrase there means the assistant will silently
    rewrite text a user did not ask it to touch.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import assist  # noqa: E402

OUT = ROOT / "tools" / "assist_review.html"

# Current Opus 5 rates, $ per million tokens. Cache reads are ~0.1x input and
# cache writes ~1.25x. Re-check before quoting these anywhere — the API drifts,
# and this file's numbers expire the same way MONETIZATION.md's do.
PRICE_IN, PRICE_OUT = 5.00, 25.00
PRICE_CACHE_READ, PRICE_CACHE_WRITE = 0.50, 6.25


def _sample(name: str) -> dict:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


EN = _sample("sample_resume.json")
AR = _sample("sample_resume_ar.json")


def _bullet(doc: dict, exp: int, n: int) -> str:
    return doc["experience"][exp]["bullets"][n]


# Twenty cases. Drawn from the SHIPPED samples wherever possible, because a line
# invented for a test is a line nobody's CV contains — and this project has been
# bitten before by checks that measured something the real input never does.
# The exceptions are 9, 10, 17 and 18, which are deliberate traps: the prompt
# makes promises ("never invent", "return weak lines weak") that the shipped
# samples are too well-written to test.
CASES: list[dict] = [
    {"id": 1, "kind": "Job title", "to": "ar", "text": EN["title"]},
    {"id": 2, "kind": "Bullet — carries $3.2M and a headcount", "to": "ar",
     "text": _bullet(EN, 0, 0)},
    {"id": 3, "kind": "Bullet — a before/after metric", "to": "ar",
     "text": _bullet(EN, 0, 1)},
    {"id": 4, "kind": "Bullet — abstract, no numbers", "to": "ar",
     "text": _bullet(EN, 0, 2)},
    {"id": 5, "kind": "Bullet — must keep Latin tool names", "to": "ar",
     "text": "Runs the studio's Figma and After Effects pipeline, with "
             "InDesign for long-form editorial."},
    {"id": 6, "kind": "Summary — the longest single field", "to": "ar",
     "text": EN["summary"]},
    {"id": 7, "kind": "Skill name — two words, no sentence", "to": "ar",
     "text": EN["skills"][0]["name"]},
    {"id": 8, "kind": "Skill name — risks a literal rendering", "to": "ar",
     "text": EN["skills"][3]["name"]},
    {"id": 9, "kind": "TRAP — a weak line. Must stay weak.", "to": "ar",
     "text": "Responsible for various tasks related to the design team."},
    {"id": 10, "kind": "TRAP — vague, invites an invented metric", "to": "ar",
     "text": "Helped improve the company's social media presence."},
    # These two are the only cases where source and target are the SAME
    # language, so `from` is stated rather than derived. Deriving it put
    # Arabic in an LTR cell with a Latin font — the review tool misreporting
    # the thing being reviewed.
    {"id": 11, "kind": "TRAP — already Arabic. Must return unchanged.",
     "from": "ar", "to": "ar", "text": _bullet(AR, 0, 0)},
    {"id": 12, "kind": "TRAP — already English. Must return unchanged.",
     "from": "en", "to": "en", "text": _bullet(EN, 1, 0)},
    {"id": 13, "kind": "Job title — Arabic to English", "to": "en",
     "text": AR["title"]},
    {"id": 14, "kind": "Bullet — Arabic to English, carries 3.2", "to": "en",
     "text": _bullet(AR, 0, 0)},
    {"id": 15, "kind": "Bullet — Arabic to English, abstract", "to": "en",
     "text": _bullet(AR, 0, 2)},
    {"id": 16, "kind": "Summary — Arabic to English", "to": "en",
     "text": AR["summary"]},
    {"id": 17, "kind": "TRAP — mixed script in one line", "to": "ar",
     "text": "Led the Figma migration for the Halden & Row brand system in 2023."},
    {"id": 18, "kind": "TRAP — a date range and a percentage", "to": "ar",
     "text": "Grew editorial output 40% between 2019 and 2021 with no new hires."},
    {"id": 19, "kind": "Bullet — second role, plainer voice", "to": "ar",
     "text": _bullet(EN, 1, 1)},
    {"id": 20, "kind": "Skill name — Arabic to English", "to": "en",
     "text": AR["skills"][0]["name"]},
]


def source_lang(case: dict) -> str:
    """Which language the line is IN.

    Usually the opposite of the target, but not for the two same-language
    traps — so it is read from the case when stated. Getting this wrong is not
    cosmetic: it sets `dir` and the font in the review table, which is exactly
    what a reviewer is judging.
    """
    return case.get("from") or ("ar" if case["to"] == "en" else "en")


def _context_for(case: dict) -> dict:
    """The CV the line came from, so word choice has something to sit in."""
    return EN if source_lang(case) == "en" else AR


def run_case(case: dict) -> dict:
    """One adaptation. Returns the case with `result`, `usage` and `seconds`."""
    started = time.monotonic()
    chunks, usage, thinking = [], {}, []
    for frame in assist.adapt(
        case["text"],
        target_lang=case["to"],
        context=_context_for(case),
    ):
        if frame["type"] == "delta":
            chunks.append(frame["text"])
        elif frame["type"] == "thinking":
            thinking.append(frame["text"])
        elif frame["type"] == "done":
            usage = frame["usage"]
    return {
        **case,
        "result": "".join(chunks).strip(),
        "thinking": "".join(thinking).strip(),
        "usage": usage,
        "seconds": round(time.monotonic() - started, 1),
    }


def cost_of(usage: dict) -> float:
    g = lambda k: (usage.get(k) or 0)  # noqa: E731
    return (
        g("input_tokens") * PRICE_IN
        + g("output_tokens") * PRICE_OUT
        + g("cache_read_input_tokens") * PRICE_CACHE_READ
        + g("cache_creation_input_tokens") * PRICE_CACHE_WRITE
    ) / 1_000_000


CHECKS = [
    ("invented", "Invented something"),
    ("translated", "Reads as translated"),
    ("facts", "A number or name changed"),
    ("register", "Wrong register"),
]


def _cache_verdict(totals: dict) -> str:
    """Say nothing about caching when nothing ran.

    `--preview` makes zero calls, and zero cache reads out of zero calls is not
    a finding — reporting it as "never engaged" would be this project's
    recurring instrument error in a new tool: a measurement that announces a
    defect it never measured.
    """
    if not totals["n"]:
        return "<b>not measured</b> — no calls were made in this run"
    if totals["cache_read"]:
        return "caching engaged"
    return ("<b>never engaged</b>: the prefix is likely below this model's "
            "minimum, so every call paid full input price")


def _cell(text: str, lang: str) -> str:
    d = "rtl" if lang == "ar" else "ltr"
    return (f'<td class="t" dir="{d}" lang="{lang}">'
            f'{html.escape(text) or "<em>(empty)</em>"}</td>')


def write_html(rows: list[dict], totals: dict) -> None:
    parts = [f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Phase 2 — Arabic quality gate</title>
<style>
 body{{font:15px/1.6 system-ui,Segoe UI,sans-serif;margin:0;padding:32px;
   background:#fbfbfa;color:#1a1a1a;max-width:1180px}}
 h1{{font-size:24px;margin:0 0 4px}}
 .sub{{color:#666;margin:0 0 24px}}
 .box{{background:#fff;border:1px solid #e2e2df;border-radius:8px;
   padding:16px 20px;margin:0 0 24px}}
 table{{border-collapse:collapse;width:100%;background:#fff;
   border:1px solid #e2e2df;border-radius:8px;overflow:hidden}}
 th{{text-align:start;font-size:12px;text-transform:uppercase;
   letter-spacing:.06em;color:#666;padding:10px 14px;background:#f4f4f2;
   border-bottom:1px solid #e2e2df}}
 td{{padding:14px;border-bottom:1px solid #eeeeec;vertical-align:top}}
 td.t{{width:34%;font-size:16px}}
 td.t[lang=ar]{{font-family:"Noto Naskh Arabic","Segoe UI",serif;font-size:18px}}
 .id{{width:34px;color:#999;font-variant-numeric:tabular-nums}}
 .kind{{width:136px;font-size:12px;color:#555}}
 .kind.trap{{color:#a8410f;font-weight:600}}
 .checks{{width:210px;font-size:12px;color:#444}}
 .checks label{{display:block;margin:0 0 3px;cursor:pointer}}
 .meta{{font-size:11px;color:#999;margin-top:8px}}
 code{{background:#f2f2f0;padding:1px 4px;border-radius:3px;font-size:12px}}
</style>
<h1>Phase 2 — Arabic quality gate</h1>
<p class="sub">{len(rows)} pairs from <code>app/assist.py::_SYSTEM</code>,
model <code>{assist.MODEL}</code>, effort <code>{assist.EFFORT}</code>.
This is a STOP/GO: if the Arabic reads as translated, the prompt is reworked
before anything is built on it.</p>

<div class="box">
<b>Read in this order.</b> (1) Did it <b>invent</b> anything? Cases 9, 10 and 18
are weak or number-carrying lines that invite improvement — a stronger line
coming back is a failure no matter how good the Arabic is. (2) Does it read as
<b>written</b> or as <b>translated</b>? (3) Are every number, date and proper
noun intact, and are tool names still in Latin script? (4) Is the register a
plain professional CV, not ornate?<br><br>
Cases 11 and 12 are already in the target language — the correct output is the
input, character for character. A paraphrase there means the assistant will
silently rewrite text nobody asked it to touch.
</div>

<div class="box">
<b>{"Measured cost" if totals['n'] else "Cost — nothing run yet"}</b> —
{totals['n']} assists, <b>${totals['cost']:.4f}</b> total,
<b>{totals['cost']/max(1,totals['n'])*100:.2f}¢ per assist</b>
(the plan's estimate was ~1.1¢, excluding thinking tokens).<br>
Cache reads: <b>{totals['cache_read']:,}</b> tokens across the run —
{_cache_verdict(totals)}.
Output tokens: {totals['out']:,} · uncached input: {totals['in']:,} ·
cache writes: {totals['cache_write']:,}.
</div>

<table><tr><th class="id">#</th><th class="kind">What it tests</th>
<th>Source</th><th>Adapted</th><th class="checks">Mark any that apply</th></tr>"""]
    for r in rows:
        src_lang = source_lang(r)
        trap = " trap" if r["kind"].startswith("TRAP") else ""
        boxes = "".join(
            f'<label><input type="checkbox"> {html.escape(lbl)}</label>'
            for _, lbl in CHECKS
        )
        parts.append(
            f'<tr><td class="id">{r["id"]}</td>'
            f'<td class="kind{trap}">{html.escape(r["kind"])}'
            f'<div class="meta">{src_lang}&rarr;{r["to"]} · {r["seconds"]}s · '
            f'{cost_of(r["usage"])*100:.2f}¢</div></td>'
            f'{_cell(r["text"], src_lang)}{_cell(r["result"], r["to"])}'
            f'<td class="checks">{boxes}</td></tr>'
        )
    parts.append("</table>")
    OUT.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="list the cases and make no API calls")
    ap.add_argument("--preview", action="store_true",
                    help="write the review page with the SOURCE echoed as the "
                         "result and no API calls — proves the layout, the "
                         "`dir` on every cell and the Arabic face before a run "
                         "costs anything")
    ap.add_argument("--only", nargs="*", type=int, metavar="ID",
                    help="run only these case ids")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or c["id"] in args.only]

    if args.dry_run:
        print(f"{len(cases)} cases, no calls made:\n")
        for c in cases:
            print(f"  {c['id']:>2}  {source_lang(c)}->{c['to']}  {c['kind']}")
            print(f"      {c['text'][:88]}")
        return 0

    if args.preview:
        rows = [{**c, "result": c["text"], "thinking": "", "seconds": 0.0,
                 "usage": {}} for c in cases]
        write_html(rows, {"n": 0, "cost": 0.0, "in": 0, "out": 0,
                          "cache_read": 0, "cache_write": 0})
        print(f"Layout preview written to {OUT} — results are echoes of the "
              f"source, NOT model output.")
        return 0

    if not assist.configured():
        print(
            "ANTHROPIC_API_KEY is not set, so no call can be made.\n\n"
            "Phase 2 needs a real key — it is the gate on whether the prompt\n"
            "produces Arabic worth building four more features on.\n\n"
            "  PowerShell:  $env:ANTHROPIC_API_KEY = 'sk-ant-...'\n"
            "  bash:        export ANTHROPIC_API_KEY=sk-ant-...\n\n"
            "Then re-run. `--dry-run` shows the cases without calling.",
            file=sys.stderr,
        )
        return 2

    rows, totals = [], {"n": 0, "cost": 0.0, "in": 0, "out": 0,
                        "cache_read": 0, "cache_write": 0}
    for case in cases:
        print(f"  {case['id']:>2}/{len(cases)}  {case['kind'][:44]:<44}",
              end="", flush=True)
        try:
            row = run_case(case)
        except assist.AssistError as exc:
            print(f"  REFUSED: {exc}")
            row = {**case, "result": f"[refused: {exc}]", "thinking": "",
                   "usage": {}, "seconds": 0.0}
        else:
            print(f"  {row['seconds']:>4.1f}s  {cost_of(row['usage'])*100:.2f}¢")
        rows.append(row)
        u = row["usage"]
        totals["n"] += 1
        totals["cost"] += cost_of(u)
        totals["in"] += u.get("input_tokens") or 0
        totals["out"] += u.get("output_tokens") or 0
        totals["cache_read"] += u.get("cache_read_input_tokens") or 0
        totals["cache_write"] += u.get("cache_creation_input_tokens") or 0

    write_html(rows, totals)
    per = totals["cost"] / max(1, totals["n"]) * 100
    print(f"\n{totals['n']} assists · ${totals['cost']:.4f} · {per:.2f}¢ each")
    print(f"cache reads: {totals['cache_read']:,} tokens "
          f"({'engaged' if totals['cache_read'] else 'NEVER ENGAGED'})")
    print(f"\nOpen {OUT} and mark it up. This is a STOP/GO.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
