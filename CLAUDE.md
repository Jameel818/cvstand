# Project rules

## CV/resume template generation — always close the loop

After generating or editing ANY CV/resume template in this project, run a
**brief-compliance pass** before reporting back. Never deliver a template that
has only been generated, not checked.

The pass is:

1. **Restate the locked spec** for that template — the palette hexes, type
   pairing, skill pattern, section order, and any explicit user instruction
   from the request ("name font same size as Summary", "sidebar sky blue",
   "line ends at the paragraph"). Pull it from the request, not from memory.
2. **Walk `references/brief-compliance-checklist.md`** and mark each row
   pass/fail against the actual rendered output.
3. **Fix every fail, then re-check.** Loop until clean or two rounds have
   passed with no progress; then say plainly what still does not comply.
4. **Report only the deltas** — what failed and what was changed. Do not
   restate the whole spec back to the user.

Standing requirements for every template here, checked every time:

- Skill graphics carry name AND level as real selectable text, never
  color/shape alone.
- Stat chips hide entirely when the metric is empty — never a bordered chip
  with a floating caption and no number.
- No content in CSS (`::before { content: }`), no text baked into backgrounds.
- Repeating entries are true siblings with identical structure — no
  specially-styled first entry.
- Pure-white templates use rules and whitespace for structure, no background
  tints except the skill graphic and the accent marker.
- When a reference image was supplied, at least three named divergence axes
  from that reference, stated in writing.

## Persistent user preferences

- Templates live as numbered blocks in `Resume Templates Coded.dc.html`, each
  with a `<!-- N -->` marker and an `id="tN"` wrapper. Keep that convention.
- Colors always diverge from any uploaded reference, for copyright reasons.
- Deliverable format is coded HTML that Claude Code can port to Jinja2.
