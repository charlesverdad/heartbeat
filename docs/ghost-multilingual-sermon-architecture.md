# Heartbeat Church Ghost Multilingual Sermon Architecture

## Goal

Add Mandarin (Simplified Chinese) and Farsi/Persian translations of sermon-summary posts to the existing Ghost site while:

- preserving the current English sermon URLs, e.g.  
  `https://www.heartbeatchurch.com.au/he-fights-for-his-glory/`
- publishing translated versions at stable, crawlable URLs:
  - `https://www.heartbeatchurch.com.au/zh/he-fights-for-his-glory/`
  - `https://www.heartbeatchurch.com.au/fa/he-fights-for-his-glory/`
- keeping translated posts out of the normal English homepage/feed
- allowing Google to index each language version independently
- linking translations together using `hreflang`
- keeping the implementation primarily inside Ghost rather than adding a separate proxy/runtime unless necessary

---

## Recommended Architecture

Use **one Ghost instance** with:

1. **one Ghost post per language**
2. **internal tags** to assign translated posts to language collections
3. **Ghost `routes.yaml` collections** to create `/zh/` and `/fa/` URL namespaces
4. **theme logic** to output `hreflang`, language selectors, and language-aware metadata
5. optional automation later to generate/create translated posts via the Ghost Admin API

Conceptually:

```text
Ghost
│
├── English sermon post
│   ├── slug: he-fights-for-his-glory
│   ├── no language-internal tag
│   └── URL: /he-fights-for-his-glory/
│
├── Mandarin translation
│   ├── slug: he-fights-for-his-glory
│   ├── internal tag: #zh
│   └── URL: /zh/he-fights-for-his-glory/
│
└── Farsi translation
    ├── slug: he-fights-for-his-glory
    ├── internal tag: #fa
    └── URL: /fa/he-fights-for-his-glory/
```

The translated posts are real Ghost posts, so they remain server-rendered, crawlable documents rather than client-side language swaps.

---

## Ghost Routing

Ghost supports multiple **collections** in `routes.yaml`, and each collection can define its own permalink structure and filter.

A suitable starting point is:

```yaml
routes:

collections:
  /:
    permalink: /{slug}/
    template: index
    filter: "tag:-hash-zh+tag:-hash-fa"

  /zh/:
    permalink: /zh/{slug}/
    template: index-zh
    filter: "tag:hash-zh"

  /fa/:
    permalink: /fa/{slug}/
    template: index-fa
    filter: "tag:hash-fa"

taxonomies:
  tag: /tag/{slug}/
  author: /author/{slug}/
```

### Why internal tags

In Ghost, internal tags begin with `#`, for example:

```text
#zh
#fa
```

Their generated slugs are typically:

```text
hash-zh
hash-fa
```

Those slugs are what should be used in `routes.yaml` filters.

### Important

The collections need to remain **mutually exclusive**.

An English post should not have `#zh` or `#fa`.

A Mandarin post should have `#zh`.

A Farsi post should have `#fa`.

Do not casually add both language tags to the same post because Ghost routing filters can conflict when content matches multiple collections.

---

## Homepage / Feed Behaviour

The root collection excludes language-tagged posts:

```yaml
filter: "tag:-hash-zh+tag:-hash-fa"
```

Therefore:

```text
/he-fights-for-his-glory/
```

appears in the normal English collection/homepage.

But:

```text
/zh/he-fights-for-his-glory/
/fa/he-fights-for-his-glory/
```

belong to separate collections and do not need to appear in the English homepage feed.

The language collection templates (`index-zh.hbs` and `index-fa.hbs`) may initially be minimal or even intentionally not linked from the primary site navigation.

---

## Translation Grouping

Ghost does not natively model “these three posts are translations of the same post.”

We therefore need a deterministic way to associate them.

### Recommended first implementation

Use the **same Ghost slug** for every translation:

```text
English:  he-fights-for-his-glory
Mandarin: he-fights-for-his-glory
Farsi:    he-fights-for-his-glory
```

Because the collections have different permalink prefixes, these do not collide:

```text
/he-fights-for-his-glory/
/zh/he-fights-for-his-glory/
/fa/he-fights-for-his-glory/
```

This makes translation discovery and `hreflang` generation straightforward.

If same-slug behaviour proves inconvenient in the Ghost Admin UI/API, introduce a small translation-group identifier using an internal tag or another controlled metadata convention.

---

## SEO Requirements

Google recommends separate URLs for different language versions and using `hreflang` to associate localized equivalents.

Each translated page should:

- return a normal HTTP 200 response
- contain server-rendered translated text
- have its own translated `<title>`
- have its own translated meta description
- have a self-referencing canonical URL
- be indexable (`noindex` must not be present)
- link to the other language versions
- contain reciprocal `hreflang` annotations

### Example

For the English page:

```html
<link rel="alternate"
      hreflang="en"
      href="https://www.heartbeatchurch.com.au/he-fights-for-his-glory/" />

<link rel="alternate"
      hreflang="zh-Hans"
      href="https://www.heartbeatchurch.com.au/zh/he-fights-for-his-glory/" />

<link rel="alternate"
      hreflang="fa"
      href="https://www.heartbeatchurch.com.au/fa/he-fights-for-his-glory/" />

<link rel="alternate"
      hreflang="x-default"
      href="https://www.heartbeatchurch.com.au/he-fights-for-his-glory/" />
```

The Mandarin and Farsi pages should emit the **same complete set** of alternate links.

### Canonicals

Each translation should canonicalize to itself.

Correct:

```text
English canonical  → /he-fights-for-his-glory/
Chinese canonical  → /zh/he-fights-for-his-glory/
Farsi canonical    → /fa/he-fights-for-his-glory/
```

Do **not** canonicalize Mandarin/Farsi back to the English version merely because they are translations.

`hreflang` describes the localization relationship; canonical URLs describe which URL represents that particular page.

---

## Language Codes

Recommended values:

```text
English             en
Simplified Chinese  zh-Hans
Persian / Farsi     fa
```

For the Mandarin pages, use `zh-Hans` if the site is publishing Simplified Chinese.

The actual page should also have an appropriate HTML language attribute where practical:

```html
<html lang="en">
<html lang="zh-Hans">
<html lang="fa">
```

Farsi pages should render right-to-left:

```html
<html lang="fa" dir="rtl">
```

or apply equivalent RTL styling to the main translated content.

---

## Language Switcher

Each sermon page should expose a visible language switcher when translations exist.

Example:

```text
English · 中文 · فارسی
```

Links should point directly to the equivalent sermon:

```text
/he-fights-for-his-glory/
/zh/he-fights-for-his-glory/
/fa/he-fights-for-his-glory/
```

Do not use automatic locale redirects as the primary mechanism.

A user or Googlebot should always be able to request a specific URL and receive that language consistently.

---

## Theme Implementation

Likely files to inspect/change:

```text
routes.yaml
post.hbs
default.hbs
index.hbs
```

Potential additions:

```text
index-zh.hbs
index-fa.hbs
partials/language-switcher.hbs
partials/hreflang.hbs
```

The exact implementation depends on the current Heartbeat Ghost theme.

### Required theme behaviour

On a sermon post:

1. determine whether it is English, Mandarin, or Farsi
2. determine its base slug
3. construct equivalent URLs
4. output alternate `hreflang` links
5. show language-switcher links
6. set RTL rendering for Farsi
7. preserve existing Ghost SEO metadata and structured data unless intentionally overridden

Be careful not to emit `hreflang` links for translations that do not actually exist. A later implementation can query Ghost content or maintain translation metadata to determine availability.

---

## Publishing Workflow

### Phase 1 — Manual

For each sermon:

1. publish the English sermon as usual
2. duplicate/create a new Ghost post for Mandarin
3. translate:
   - title
   - excerpt
   - body
   - headings
   - SEO title
   - meta description
   - meaningful image alt text
4. give it the same slug as the English sermon
5. apply internal tag `#zh`
6. publish
7. repeat for Farsi with `#fa`
8. verify all three URLs
9. verify canonical + `hreflang`
10. request indexing / inspect in Google Search Console if desired

### Phase 2 — Automated

Later, use Ghost webhooks + Admin API:

```text
English sermon published
        ↓
Ghost webhook
        ↓
translation job
      ↙     ↘
 zh-Hans    fa
      ↘     ↙
create/update Ghost posts
        ↓
attach #zh / #fa
        ↓
publish translations
```

The translation process can use an LLM, but translated posts should ideally remain editable/reviewable in Ghost.

---

## Bible Quotations

Do not automatically “translate” long English Bible quotations with an LLM if an established local-language Bible translation is desired.

Prefer:

1. retain structured references such as `John 3:16`
2. use an approved/licensed Chinese or Persian Bible source where appropriate
3. otherwise clearly distinguish sermon-summary translation from verbatim Bible translation

This is both a translation-quality and potential licensing concern.

---

## Sitemap / Discovery

Ghost already generates sitemap infrastructure for published content.

After routing changes, verify that:

- English posts remain discoverable
- `/zh/...` posts are represented/discoverable
- `/fa/...` posts are represented/discoverable
- translated posts are not blocked by `robots.txt`
- no theme metadata adds `noindex`
- canonical URLs use the translated URL

Google can also discover translations through normal internal links and the reciprocal `hreflang` annotations.

---

## Implementation Validation Checklist

- [ ] Existing English URLs are unchanged
- [ ] `/zh/{slug}/` resolves to Mandarin Ghost posts
- [ ] `/fa/{slug}/` resolves to Farsi Ghost posts
- [ ] Mandarin/Farsi posts do not appear in the English homepage feed
- [ ] English posts do not enter language collections
- [ ] No post belongs to multiple language collections
- [ ] Each language page returns HTTP 200
- [ ] Each page has a self-referencing canonical
- [ ] No translated page canonicalizes to English
- [ ] Reciprocal `hreflang` annotations exist
- [ ] `en`, `zh-Hans`, and `fa` are used consistently
- [ ] `x-default` points to English
- [ ] Farsi content renders RTL
- [ ] Language switcher links to the corresponding sermon
- [ ] Missing translations do not produce broken alternate links
- [ ] Sitemap/indexability verified
- [ ] Google Search Console URL inspection succeeds

---

## Known Ghost Caveat

Ghost does **not** currently provide a first-class multilingual-post data model comparable to a CMS where translations are directly attached to one canonical content object.

This architecture therefore uses Ghost's existing primitives:

```text
posts + internal tags + collections + theme logic
```

It is a pragmatic workaround, but one that matches Ghost's supported dynamic-routing system.

Keep the routing filters simple. Ghost's own documentation warns that complex or overlapping collection filters can produce unexpected behaviour.

---

## Sources

### Ghost — Dynamic Routing

Ghost Developer Docs: **URLs & Dynamic Routing**

https://docs.ghost.org/themes/routing

Relevant points:

- `routes.yaml` controls dynamic routing.
- collections can have their own URL/permalink structures.
- collections support filters.
- a root collection can use `/{slug}/`, while other collections can use prefixed paths.

### Ghost — Routing Filter Caveats

Ghost Developer Docs: **Filter Property Not Working In Routing**

https://docs.ghost.org/faq/filter-property-routes-yaml

Relevant point:

- complex/overlapping collection filters can cause conflicts or unexpected behaviour; keep language collections mutually exclusive.

### Ghost Community — Multilingual Routing

Ghost Forum: **How to create Multilanguage Posts?**

https://forum.ghost.org/t/how-to-create-multilanguage-posts/2537

Discusses using language-specific tags with Ghost dynamic routing so posts can be exposed under language-specific URLs.

Ghost Forum: **Is Ghost's multi-language tutorial still valid?**

https://forum.ghost.org/t/is-ghosts-multi-language-tutorial-still-valid/13828

Discusses using Ghost collections such as `/fr/` for additional languages.

Ghost Forum: **Ghost Post Translation - Multi Language content**

https://forum.ghost.org/t/ghost-post-translation-multi-language-content/30494

Community discussion of tag/collection-based multilingual Ghost implementations.

### Google — Localized URLs and hreflang

Google Search Central: **Localized Versions of your Pages**

https://developers.google.com/search/docs/specialty/international/localized-versions

Relevant requirements/recommendations:

- use `hreflang` to identify localized equivalents
- alternate pages should reference each other
- each language URL can represent a localized version of the same content

### Google — Multilingual Sites

Google Search Central: **Managing Multi-Regional and Multilingual Sites**

https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites

Relevant recommendation:

- use different URLs for different language versions
- use `hreflang` so Google can connect them

### Google — Locale-Adaptive Pages

Google Search Central: **How Google Crawls Locale-Adaptive Pages**

https://developers.google.com/search/docs/specialty/international/locale-adaptive-pages

Relevant recommendation:

- prefer separate locale-specific URLs rather than serving different languages from the same URL based only on locale detection.

### Google — Canonical URLs

Google Search Central: **Canonicalization**

https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls

Relevant point:

- localized URLs participating in `hreflang` clusters should be handled consistently; translated pages should not simply be collapsed into an unrelated canonical configuration.

---

## Implementation Priority

Implement in this order:

```text
1. Back up current routes.yaml/theme
2. Add #zh / #fa collection routing
3. Prove URLs using test posts
4. Confirm root homepage excludes translations
5. Add RTL support
6. Add language switcher
7. Add hreflang logic
8. Verify canonicals
9. Verify sitemap/indexing
10. Automate translation creation only after routing/SEO is proven
```

Do not begin with translation automation.

First make the content model, routing and SEO behaviour correct using manually created test posts. Once that works reliably, automation is straightforward.
