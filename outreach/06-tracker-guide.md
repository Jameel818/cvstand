# How to use `05-tracker.csv`

Opens in Excel, Numbers or Google Sheets. One row per institution, filled left
to right as the conversation moves. Delete the example row first.

**Set the encoding when you open it.** The file is UTF-8. Excel on Windows
sometimes assumes the system codepage and will mangle Arabic in
`personal_line_used` or `notes` — if that happens, open Excel first, then
Data → From Text/CSV → and choose **65001: Unicode (UTF-8)**.

| Column | What goes in it |
|---|---|
| `institution` | Name |
| `tier` | 1–4, from `04-targets.md` |
| `city` | Helps when you get a meeting |
| `contact_name` / `contact_role` | A person, not a department |
| `email` | **Taken from their site, never guessed** |
| `how_found` | Site page, LinkedIn, referral — so you can repeat what works |
| `personal_line_used` | The line you personalised with. Stops you reusing it and reminds you what you said |
| `lang` | `ar` or `en` — whichever you wrote in. They reply in kind |
| `sent_1` / `sent_2` / `sent_3` | Dates. `sent_2` is `sent_1` + 7, `sent_3` is + 21 |
| `replied` | Date of their first reply |
| `outcome` | `no reply` · `not interested` · `interested` · `using it` · `wants a call` |
| `next_action` | The one thing you owe them |
| `next_date` | When |
| `notes` | Anything said that you would otherwise forget |

## The only two views you need

Sort by `next_date` to see what you owe people today. Filter `outcome` for
blanks where `sent_1` is over 7 days old to see who needs follow-up 2.

## What to read from it after twenty

You asked whether this can be automated. The sending can't, but the *learning*
is mechanical — after twenty rows there is a real answer to:

- **Reply rate by tier.** If private universities answer and public ones do
  not, stop writing to public ones.
- **Reply rate by language.** If Arabic emails get answered and English ones
  do not, that changes every email from then on.
- **Which `how_found` produced replies.** A named person from LinkedIn versus
  a general address from the site is the difference worth measuring.
- **Which personal line got a response.** Reuse the shape, not the words.

Twenty emails is a small sample and will not settle anything statistically —
but a 0/20 reply rate and a 6/20 reply rate are different enough to act on
without statistics, and either is more information than exists today.

## One rule

**Log it before you send, not after.** The row you do not write is the follow-up
you never send.
