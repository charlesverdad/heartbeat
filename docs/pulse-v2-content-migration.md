# Pulse v2 content migration (2026-10-22)

The v1 spaces, collections and pages are now in production Pulse v2, along with new beginner pages and a Policies & Forms
space. This was done by Opus 5.5 working unattended, and is not yet acknowledged by Charles.

- **Source:** the v1 `pg_dump` (`backups/pulse-v1/vm-20261021-155457/`), the church website (About, Locations, History,
  Internal) and announcement slides in the sermon transcripts.
- **Scripts and output:** in `backups/pulse-v2-content/` (gitignored, because it holds church content).
  - `build_content.py` writes `spec.json`.
  - `hb-content-sql.ts`, run from a pulse-v2 checkout at v0.2.0, writes `import.sql`.
  - All rows are `nod_hb_*` and authored by Charles. Re-running the import replaces them, along with any edits made to
    those pages since.
- **Rollback point:** D1 bookmark `00000077-00000000-0000510c-680e7c5a4a2cfd994c535e9c3c89daba`, taken before the import.

## New structure

| Space | Collections and items | Access |
| --- | --- | --- |
| **Start Here** (new) | About Heartbeat: Welcome to Heartbeat, Our Vision, What is a House Church?, What is a Partner?, plus links to Statement of Faith, Brief History and About Pastor Joshua Choi. Church Life: Sunday Service, Early Morning Prayer, How Can I Serve?, Ministry Calendar 2026, FAQs | Members; EC edit |
| **Policies & Forms** (new) | Code of Conduct (**draft placeholder**), Reimbursement Form for Sydney, Gold Coast and Melbourne, Prayer Request, Partnership Class, Baptism Course and Living Life registrations, Service Log, PJ Kitchen | Members; EC edit |
| **Sydney Campus** (was Operations (Syd)) | Hosting & Presiding: Hosting Guide, Service Order Manual, Communion. Rosters & Guidelines: Rosters, Building Use Guidelines, Bin Collection Schedule. How-to Guides: How to Clean. Media Team Guides (empty) | Members; EC edit. Media Team Guides: Partners only, Shepherds and EC edit |
| **Resources** | Discipleship Materials: Christianity Explained, Survival Kit, Experiencing God, Practicing the Way, and a link to Our Daily Bread. Shepherd's School: Shepherd's Covenant, House Church Shepherd Report link, Session Recordings, and the Discussion Summaries series (sessions 1–4) | Members; EC and Shepherds edit. Shepherd's School: Shepherds and EC only. Session Recordings: Shepherds only |

## What changed from v1

- **New pages, written for beginners:** Welcome to Heartbeat, Sunday Service and FAQs (the FAQs include a glossary: HC,
  VIP, PJ, EMP, EC, partner, multiplication).
- **Empty v1 drafts written up:** Our Vision, The House Church Model (now "What is a House Church?"), What is a Partner?,
  Early Morning Prayer and How Can I Serve?.
- **Forms are direct links**, taken from the website's /internal page. Reimbursement is one link per campus.
- **Service Order Manual:**
  - "Roles:" is now "Who:".
  - The Bible reading step said "begin immediately after the offering song", which clashed with the announcement video
    step. It now says the reading starts after the welcome and announcements. **Please check this.**
- **Hosting Guide:** a tip at the end links to the Service Order Manual and the Communion page.
- **Communion:** the plain-text sub-labels are now headings.
- **Rosters:** an intro line, the sheet embed, and an "Open in Google Sheets" link instead of the bare URL.
- **Building Use Guidelines:** a one-line intro; the empty 14th rule is removed.
- **Bin schedule:** the text now comes before the calendar.
- **How to Clean:** an intro line above the Canva checklist.
- **Christianity Explained:** grammar fixes.
- **Survival Kit and Experiencing God:** the lost v1 images are removed.
- **Practicing the Way:** rewritten intro. "Taiwanese subtitles" is now "Traditional Chinese subtitles", and there is a
  folder link under the Drive embed.
- **Discipleship Materials:** the description gives the study order from Shepherd's School session 3 (Christianity
  Explained → Living Life → Survival Kit → Practicing the Way → Experiencing God).
- **Shepherd's Covenant:** verse formatting fixed, and the sign-up link is in a callout.
- **Discussion summaries:** unchanged apart from titles ("Session 1: Spirit and Posture").

## Not migrated

- **Announcements:** Gold Coast Camp! (April) and the Partnership Class draft (23 March) are past, and their images were
  lost. Use v2 Notices for new announcements.
- **Empty drafts:** Running EMP, CCTV Access, Overflow Monitor Setup, House Church Finder and the "Untitled" pages.
- **The v1 user-specific rule on Media Team Guides:** that person isn't in v2 yet. Add them once they sign in.

## Needs Charles

- **Missing form URLs:** Ministry Forms, Safe Ministry and New Shepherds Form (from the design) aren't on the website.
  Add them as links in Policies & Forms with New → Link.
- **Code of Conduct:** paste in the real text, then publish.
- **Facts to check:**
  - Early morning prayer is at the Sydney church building.
  - The Partnership Class is usually on Zoom.
  - "Service Log" and "PJ Kitchen" are copied from the website without a description.
- **Access is empty:** the Shepherds, Partners and EC groups have no members, so restricted pages are visible only to
  admins until people are added.
- **Home quick links** (design: roster, Code of Conduct, FAQs) are set in Admin → Home.
