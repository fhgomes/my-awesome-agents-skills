---
name: andela-profile
description: >-
  Fill in, rewrite or audit a talent profile on the Andela talent platform (app.andela.com/profile)
  through the user's logged-in browser: Overview (profile summary), Work experience (add, edit,
  reorder by date), Education, and the skills Andela derives from them. Use WHENEVER the user asks
  to "update my Andela profile", "edit my overview on Andela", "rewrite my experiences on Andela",
  "add my current job to Andela", "add education to Andela", "sync my Andela profile with my CV",
  "why does Andela say I have N years of experience", or shares an app.andela.com/profile link and
  asks for changes. Covers where the content must come from (the user's CV, never invented), the
  field map and character limits, the markdown rules of each field, the browser-automation traps of
  this site (Enter in the skills box submits the whole form, the "I currently work here" checkbox
  ignores programmatic input, another extension's iframe can block screenshots and scripts, section
  pencils that only scroll when clicked by reference), automatic skill extraction on save, and how
  to verify the saved result. Also triggers on the equivalent phrases in other languages.
---

# Andela talent profile

Andela matches talent to client roles from the profile. A stale profile (missing recent jobs,
wrong dates, wall-of-text descriptions) silently lowers the match and the "years of experience"
shown in the header. This skill is the procedure to bring the profile in line with the user's
current CV, field by field, and prove it was saved.

## 0. Ground rules

- **Only on the user's request.** Every save is visible to recruiters and clients. The user asking
  to "update/rewrite my profile" authorizes the edits it names; it does not authorize touching the
  rate, contact data, availability, headline or photo unless those were named too.
- **Content comes from the user's sources, never from imagination.** Look for, in order: the most
  recent CV (text, PDF, LaTeX, DOCX), the LinkedIn profile, notes or project files the user points
  to. Dates, employers, numbers and titles are copied, not "improved". If a field has no source
  (a start date, an old job with no description), ask or mark it clearly in the final report as
  written by the agent.
- **Read before writing.** Extract the current profile text first (section 5), so the report can
  say what changed and nothing is lost by accident.
- Use the user's existing logged-in browser session (e.g. claude-in-chrome). Never type passwords,
  never call the private API with tokens; the UI is the supported path.

## 1. Page map

`https://app.andela.com/profile` is one long page with a left nav:
About · Skills · Assessments · Experience · Projects · Certifications · Education · Languages.

| Section | How to open the editor | Dialog | Fields and limits |
|---|---|---|---|
| Header (About) | pencil top-right of the header card | — | headline, rate, location, hours. **"N yrs experience" is computed** from the earliest experience start date; it is not editable directly |
| Overview | pencil left of "Overview" (`Edit summary`) | "Profile summary" | one textarea, **1000 chars**, plain text rendered with `white-space: pre-line` (newlines kept, no markdown) |
| Experience | pencil left of "Experience" (`Edit experience`) | "Work experience" list → `Add job` or a row's pencil → "Add job"/"Edit job" | Title\*, Company\*, Location, Industry, "I currently work here", Start date\*, End date\* (disabled and shown as "Present" when current), Description (**markdown, 2500 chars**), Skills (combobox with chips) |
| Education | `Add education` button | "Add degree" | Degree, Field of study, Institution, **Start date\* (required)**, End date (or expected), Description |
| Projects / Certifications | `Add project` / `Add certification` | — | optional; good place for talks, OSS, certificates |

Buttons in the job form: `Save and add another`, `Cancel`, and the submit (`Add job` on a new
entry, `Save job` on an edit). The experience list on the page is sorted by start date
automatically; there is no manual reorder.

## 2. Writing the content

### Overview (≤ 1000 chars, plain text)

Plain text, so use real line breaks and a literal bullet character (`•`) — a `- ` will show as a
hyphen. A shape that fits the limit:

```
<Level> <Role> with <N>+ years building <what> in <domains>. <Remote/team context>.

Impact & Leadership:
• <biggest quantified result, from the CV>
• <second result>
• <third result>
• <leadership / hiring / founding signal>

Tech & AI Stack:
• <core stack in one line>
• <differentiator line>

Targeting <roles> in <domains>.
```

Check the character counter under the textarea (e.g. `906/1000`) before saving. A pasted text that
lost its newlines (sections glued together like `...teams.Impact & Leadership:•`) is the most common
defect of existing overviews; fix it.

### Experience description (markdown, ≤ 2500 chars)

Rendered as markdown: a first paragraph becomes `<p>`, lines starting with `- ` become a bulleted
list. Use:

```
<One or two sentences: company context and the scope you owned.>

- <Result with a number, from the CV>
- <Result with a number>
- <Architecture / leadership item>
- Tech: <comma-separated stack for this job>
```

Keep the `Tech:` line: Andela extracts skills from the description text (section 3), so naming the
stack there is what populates the skill chips.

Fill **Location** (e.g. `Remote (Country / Country)`, `City, Country (Hybrid)`) and **Industry**
(e.g. `Payments / FinTech`) on every entry; old imports often leave them empty.

### Education

Start date is required. If the CV only has the graduation year, look for the start date in the
user's other sources before asking; do not guess silently.

## 3. Skills are extracted automatically

When a job is saved, Andela parses the description and **adds skill chips by itself** (and merges
them into the global Skills list). Consequences:

- You rarely need to add chips by hand; a good `Tech:` line is enough.
- Extraction is noisy: expect stray chips such as generic words or near-miss technologies.
  Removing them with the chip's `×` may not stick — the next save can re-extract them. Report the
  noise to the user instead of looping on it.
- If you do add chips by hand, see the Enter trap in section 4.

## 4. Browser-automation traps (verified on this site)

1. **Enter in the Skills combobox submits the whole form** when no option is highlighted — and
   options load asynchronously. Never type a skill and press Enter blindly. Safe sequence: type the
   name → wait ~2 s for results → `ArrowDown` (highlights the first option) → `Enter`, or click the
   option. Type the canonical name (`Microsoft Azure`, not `Azure`, which lists dozens of Azure
   products first). An accidental submit just saves the form; reopen the entry and continue.
2. **"I currently work here" ignores programmatic input.** A form-fill tool may report the checkbox
   as checked while the UI (and the saved data) stays unchecked. Click it for real and confirm the
   End date turns into a disabled "Present".
3. **Section pencils clicked by accessibility reference may only scroll** the page instead of opening
   the dialog. Click by coordinates after a screenshot, or run a DOM `click()` on the button found by
   its text/aria-label.
4. **Another extension can block screenshots and page scripts** while a form is open (error:
   *"Cannot access a chrome-extension:// URL of different extension"* — a password manager or
   writing assistant injecting an iframe into the inputs). Accessibility-tree reads, element search
   and form filling by reference still work. Reloading the page clears it; nothing is saved by
   reloading, so only do it with no unsaved form.
5. **Screenshots can time out** when the browser window is hidden or minimized. Fall back to the
   accessibility tree / page text and retry the screenshot later.
6. **Form filling by reference works** for text inputs, date inputs (`YYYY-MM-DD`) and the
   description textarea, and the tool returns the previous value — keep it, it is the "before" for
   the report.
7. Element references change every time a dialog re-renders. Re-run the element search after each
   save before clicking the next row's pencil.

## 5. Procedure

1. **Gather sources** (section 0). Build a table per job: title, company, location, industry,
   start, end/current, 3–5 result bullets, stack. Note conflicts between sources (dates that differ
   between CV and profile) and resolve them in favor of the most recent CV.
2. **Snapshot the current profile**: open the page and extract the main element's text (page-text
   tool, or `document.querySelector('main').innerText`). Keep it for the before/after report.
3. **Experience first** (it changes the computed years):
   - Open the Work experience list. Add missing recent jobs with `Add job`; for each existing row,
     open its pencil and overwrite title, company, location, industry, dates and description.
   - Click the real "I currently work here" checkbox for the current job.
   - Save each entry with the submit button, then re-locate elements (trap 7).
4. **Overview**: open "Profile summary", replace the text, check the counter, save.
5. **Education** (and Projects/Certifications if requested).
6. **Verify**: reload the page and re-extract the text. Confirm every entry shows the new title,
   company, dates and description, the header's "N yrs experience" changed as expected, and the
   overview line breaks render. Do not report success from the form tool's return values alone.
7. **Report** to the user: what changed per section, anything the agent wrote without a source,
   noisy auto-extracted skills, and empty sections worth filling. If the user keeps career notes,
   offer to record the update there.
