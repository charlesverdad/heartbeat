# Pulse Migration Plan

Migration from BookStack (docs.heartbeatchurch.com.au) to Pulse (pulse.heartbeatchurch.com.au).

## Hierarchy Comparison

| BookStack (4 levels) | Pulse (3 levels)       |
|----------------------|------------------------|
| Shelf                | **Space**              |
| Book                 | **Collection**         |
| Chapter              | _(no equivalent)_      |
| Page                 | **Document**           |

The key constraint: Pulse has no "chapter" equivalent. Where BookStack uses chapters to group pages within a book, those pages must become flat documents within a Pulse collection. Use document naming prefixes or ordering to preserve grouping where needed.

---

## Roles

| Role          | Description                                    |
|---------------|------------------------------------------------|
| `ec`          | Executive Committee — full access everywhere   |
| `shepherds`   | Shepherds / house church leaders               |
| `partners`    | Church partners (members)                      |

---

## Proposed Pulse Structure

### Space 1: **Welcome**
> _Permissions: `partners` — view; `shepherds` — view+edit_

Public-facing intro content for all partners.

| Collection               | Documents (from BookStack)                                                        | Source                |
|--------------------------|-----------------------------------------------------------------------------------|-----------------------|
| **About Heartbeat**      | Our Vision · The House Church Model · What is a Partner?                          | Welcome! (book)       |
| **Church Life**          | Early Morning Prayer · How Can I Serve? · Ministry Calendar 2026                  | Welcome! (book)       |

---

### Space 2: **Sydney Campus**
> _Permissions: `partners` — view; `shepherds` — view+edit_
>
> (Compound ACL not needed — all Sydney content is relevant to all partners for now. Revisit if campus-specific roles are added later.)

| Collection                      | Documents (from BookStack)                                                                                     | Source                          |
|---------------------------------|----------------------------------------------------------------------------------------------------------------|---------------------------------|
| **Hosting & Presiding**         | Hosting Guide · Sunday Service Order Manual (Presiding) · How to Set Up for Communion                          | Sydney > Hosting and Presiding Guide (chapter) |
| **Rosters & Guidelines**        | Hosting, Presiding and Cleaning Rosters · Church Building Use Guidelines                                       | Sydney (top-level pages)        |
| **Runbooks**                    | Cleaning Guide · Running EMP · CCTV Access                                                                    | Sydney > Runbooks and How-To's (chapter) |

---

### Space 3: **Melbourne Campus**
> _Permissions: `partners` — view; `shepherds` — view+edit_

Currently empty in BookStack. Create the space as a placeholder — populate when Melbourne content is ready.

---

### Space 4: **Gold Coast Campus**
> _Permissions: `partners` — view; `shepherds` — view+edit_

Currently empty in BookStack. Create the space as a placeholder.

---

### Space 5: **Ministries**
> _Permissions: `partners` — view; `shepherds` — view+edit_

Each BookStack "book" under the Ministries shelf becomes a collection. Chapters within those books flatten into documents.

| Collection                 | Documents (from BookStack)                                                           | Source                    |
|----------------------------|--------------------------------------------------------------------------------------|---------------------------|
| **Missions Team**          | Description · Upcoming Mission Opportunities (flatten chapter intro + any sub-pages) | Missions Team (book)      |
| **Media Team**             | Connecting Remotely to the Church Media PC                                           | Media Team (book)         |
| **Praise Team**            | _(currently empty — placeholder)_                                                    | Praise Team (book)        |
| **Welcome Team**           | _(currently empty — placeholder)_                                                    | Welcome Team (book)       |
| **Intercessory Prayer**    | _(currently empty — placeholder)_                                                    | Intercessory Prayer (book)|
| **Sunday Service**         | _(currently empty — placeholder)_                                                    | Sunday Service (book)     |
| **Neighbours Ministry**    | _(currently empty — placeholder)_                                                    | Neighbours Ministry (book)|
| **Kidswave**               | _(currently empty — placeholder)_                                                    | Kidswave (book)           |
| **Lighthouse**             | _(currently empty — placeholder)_                                                    | Lighthouse (book)         |
| **Digital Platform Team**  | Social Media Policy · How to Post a Sermon Summary · Organisation Accounts (Google)  | Digital Platform Team (book) |

> **Note on Digital Platform Team:** The "Internal" chapter (Organisation Accounts) contains sensitive info. Consider moving it to the Leadership & Governance space instead, or applying compound ACL (`ec` + `shepherds`) on that specific document.

---

### Space 6: **Resources**
> _Permissions: `partners` — view; `shepherds` — view+edit_

| Collection                  | Documents (from BookStack)                      | Source                      |
|-----------------------------|--------------------------------------------------|-----------------------------|
| **House Churches**          | House Church Finder                              | House Churches (book)       |
| **Discipleship Materials**  | _(migrate existing content)_                     | Discipleship Materials (book)|
| **Shepherd's School**       | _(new — to be populated)_                        | New content                 |

> **Shepherd's School collection permissions:** Override space-level permissions.
> Set to `shepherds` — view+edit. Partners should **not** see this collection.

---

### Space 7: **Leadership & Governance**
> _Permissions: `ec` — view+edit (EC only, no other roles)_

| Collection                     | Documents (from BookStack)    | Source                          |
|--------------------------------|-------------------------------|---------------------------------|
| **Digital Resources & Tools**  | _(migrate existing content)_  | Digital Resources and Tools (book) |

---

## Content NOT migrated

| BookStack Item             | Reason                                                      |
|----------------------------|-------------------------------------------------------------|
| Structure & Usage Guide    | BookStack-specific meta docs — not relevant to Pulse        |
| Templates                  | BookStack template system — recreate natively in Pulse      |

---

## Permissions Summary

| Space                    | `ec`        | `shepherds`  | `partners`  | Notes                                          |
|--------------------------|-------------|--------------|-------------|-------------------------------------------------|
| Welcome                  | view+edit   | view+edit    | view        |                                                |
| Sydney Campus            | view+edit   | view+edit    | view        |                                                |
| Melbourne Campus         | view+edit   | view+edit    | view        |                                                |
| Gold Coast Campus        | view+edit   | view+edit    | view        |                                                |
| Ministries               | view+edit   | view+edit    | view        |                                                |
| Resources                | view+edit   | view+edit    | view        | Shepherd's School collection: `shepherds` only |
| Leadership & Governance  | view+edit   | —            | —            | EC-restricted                                  |

### Compound ACL Examples

- **Shepherd's School** (collection within Resources): Require `shepherds` role to view. Partners can see the rest of Resources but not this collection.
- **Digital Platform Team > Organisation Accounts**: If kept in Ministries, apply compound ACL requiring `ec` to view this specific document.

---

## Migration Order

1. **Create roles** — `ec`, `shepherds`, `partners`
2. **Create spaces** with permissions (start with Welcome + Sydney Campus)
3. **Migrate Sydney Campus** — most content, good first test
4. **Migrate Welcome** — small, high-visibility
5. **Migrate Ministries** — largest space, mostly placeholders
6. **Migrate Resources** — includes new Shepherd's School collection
7. **Migrate Leadership & Governance** — EC-only, smallest
8. **Create placeholder campus spaces** (Melbourne, Gold Coast)
9. **Verify permissions** — test each role can see/not-see the right content
10. **Redirect or decommission** BookStack

---

## Open Questions

- [ ] Should campus spaces eventually use compound ACL (e.g., `partners` + `syd`) if campus-specific roles are introduced?
- [ ] Should Digital Platform Team stay under Ministries or move to Leadership & Governance given its internal/ops nature?
- [ ] What content goes into Shepherd's School initially?
- [ ] Should empty ministry collections be created as placeholders or only created when content is ready?
