# 7. Performance, accessibility, security and privacy review (i41)

## Performance (Sweep)
- **Weight:** `site/style.css` is 15,525 bytes (was 11,940). Home is about 15.6 KB of HTML, so about 31 KB with the CSS, against a 100 KB budget. The heaviest page is the Research Arena at about 65 KB with the CSS.
- **Requests:** no new requests, no fonts, no images beyond the existing avatar SVGs.
- **Done:** the budget check runs in CI on every page.

## Accessibility (User Advocate, Trial)
- **Done:**
  - Every text color pair is at least 4.5:1 in both themes (lowest 5.54:1).
  - Tap targets are 44px or more on all 42 pages at 7 widths.
  - Focus is visible, nothing depends on hover, and motion is reduced when asked.
  - Status is shown by words and chip shape, never by color alone.
  - There's one h1 per page, and sections are labelled.
- **Unverified:** a real screen reader pass and a 200% zoom pass.

## Security and privacy (Shield, c283)
- **Done:**
  - No scripts, forms, external stylesheets or fonts.
  - No new data sources. Home only reads data the site already publishes (wins, ledger totals, Timeline records, updates, issues, run counts).
  - No personal data. The PII and secret checks pass.
  - No change to CI, `check.py`, `patterns.json`, CODEOWNERS or permissions.
- **Not touched:** the guardrail files. The only non-additive test change is that `tests/test_prototype.py` became `tests/test_home.py` along with the page it checked, disclosed in #88.

## Measurement (Analyst, c285)
No analytics or tracking. Health is measured from the repo: page weight, the mobile audit, the contrast test and the data counts. Nothing is collected from visitors.
