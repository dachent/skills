# External test-file catalog (manual / exploratory, not part of the automated corpus)

A reference list of publicly downloadable, real-world `.xlsx`/`.xlsm` files for manually stress-testing `xlsx-win` against realistic Power Query, VBA, dashboard, and large-data workbooks. This is **not** wired into `run_corpus.py` or CI -- it exists for a human to pull a file from here and run it through the router / job contract / validation contract by hand when the synthetic corpus (`corpus.py`) doesn't cover a scenario well enough.

## Why this is separate from `corpus.py`

`corpus.py` generates small, purpose-built workbooks on demand specifically so the automated corpus stays fast, deterministic, and license-free -- see its own module docstring. Nothing here is committed to this repo or downloaded automatically: every entry below is a link to a third party's file, verified live as of the date in the "Verified" column, not mirrored. Two real, proprietary production workbooks were also used earlier in this project's development for one-off real-world validation (documented in `README.md`'s "Real-world validation against production workbooks" section) -- those are confidential and are not, and will never be, listed here.

## Before using any of these

- **Not mirrored.** Always fetch fresh from the source link; nothing here is vendored into this repo.
- **Licensing varies per entry** -- see the "License / attribution" column. Several of these are blog-provided "free sample" downloads with no formal license file, meaning reuse beyond local testing is not clearly granted. Treat anything not explicitly MIT/public-domain as "fine for local testing, don't redistribute as your own."
- **Link rot is expected.** "Verified" reflects a live HTTP check on 2026-07-18 (status code + a byte-range fetch confirming a real ZIP/OOXML signature, `50 4B 03 04`) -- not a guarantee it stays live. Re-check before depending on an entry.
- **Macro content is untrusted.** `xlsx-win`'s own job contract cannot execute macros at all (`run_approved_macro` is unimplemented -- issue #73), so nothing here can be macro-executed *through the skill*. But a human opening one of the `.xlsm`/VBA files directly in real Excel to inspect it manually can still get Excel's own "Enable Content" prompt -- never click through that for these files outside a disposable VM/sandbox.

## Power Query focused

| File | Link | Exercises | License / attribution | Verified |
| --- | --- | --- | --- | --- |
| Microsoft Financial Sample workbook (`Financial Sample.xlsx`) | [download](https://go.microsoft.com/fwlink/?LinkID=521962) | Tables + PivotTables -> `excel_required` routing (`has_pivots`); refresh/recalc on a well-known official sample | Official Microsoft sample data, published for tutorial/testing use | 2026-07-18: HTTP 200, confirmed ZIP signature, 83,418 bytes |
| `PowerQuery.xlsx` (ShreevaniRao repo) | [download](https://raw.githubusercontent.com/ShreevaniRao/Data-Analysis-with-Excel-Power-Query/main/PowerQuery.xlsx) | Real Power Query transformations, cleaning, consolidation -> genuine `has_connections` routing + refresh | Repo has **no LICENSE file** (checked via GitHub API) -- author's copyright, reuse terms unclear beyond viewing; treat as local-testing-only | 2026-07-18: HTTP 200, confirmed ZIP signature, 120,869 bytes |
| `Excel Project Dataset.xlsx` (same repo) | [download](https://raw.githubusercontent.com/ShreevaniRao/Data-Analysis-with-Excel-Power-Query/main/Excel%20Project%20Dataset.xlsx) | Multi-tab analysis, pivots, dashboard -> combined `has_pivots`/`has_connections` routing | Same repo, no LICENSE file -- local-testing-only | 2026-07-18: HTTP 200, confirmed ZIP signature, 316,483 bytes |
| TrumpExcel Retail Inventory | [download](https://www.dropbox.com/scl/fi/f7thmp8268s7vwgksidfr/01-Retail-Inventory.xlsx?rlkey=lu181vqokcewwvco8ak1rxmk7&dl=1) | Plain tabular workbook -- good `openpyxl`-path baseline before layering PQ on top by hand | Blog-provided free sample (Puneet Gogia / TrumpExcel), no formal license -- personal/testing use as advertised on the blog | 2026-07-18: HTTP 200, confirmed ZIP signature, 79,154 bytes |
| TrumpExcel Project Management | [download](https://www.dropbox.com/scl/fi/4x53npvymfmrgr0extvgx/02-Project-Management.xlsx?rlkey=qtj9bwnlt94jm7jhfppwzgrbq&dl=1) | Same as above, project-tracking shape (dates, dependencies) | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 72,352 bytes |
| TrumpExcel Real Estate Listings | [download](https://www.dropbox.com/scl/fi/z6kbab7psonkymmr722i6/03-Real-Estate-Listings.xlsx?rlkey=7hx0ojbiuxb34kqd9g1y0jjse&dl=1) | Same as above, listings/pricing shape | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 74,873 bytes |
| TrumpExcel Restaurant Sales | [download](https://www.dropbox.com/scl/fi/qnk47lzecilxt1suz2tsg/04-Restaurant-Sales.xlsx?rlkey=1ovujyhw1ox6banzbophcegrf&dl=1) | Same as above, sales/menu shape | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 65,404 bytes |
| Excelx Product Sales Region | [download](https://excelx.com/wp-content/uploads/2025/06/Product-Sales-Region.xlsx) | Router baseline, refresh/recalc on a plain sales table | Blog-provided free sample, no formal license -- local-testing-only | 2026-07-18: HTTP 200, confirmed ZIP signature, 149,740 bytes |
| Excelx Online Store Orders | [download](https://excelx.com/wp-content/uploads/2025/06/Online-Store-Orders.xlsx) | Same as above, order-line shape | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 107,744 bytes |
| Excelx Retail Store Transactions | [download](https://excelx.com/wp-content/uploads/2025/06/Retail-Store-Transactions.xlsx) | Same as above, transaction-log shape | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 148,489 bytes |
| Excelx Customer Purchase History | [download](https://excelx.com/wp-content/uploads/2025/06/Customer-Purchase-History.xlsx) | Same as above, customer-history shape | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 110,233 bytes |

## VBA / macro-enabled and mixed

| File | Link | Exercises | License / attribution | Verified |
| --- | --- | --- | --- | --- |
| Chris Webb Power Query + VBA integration example | [OneDrive share](https://1drv.ms/x/s!AjFffgoO_-9rgSSi7X6s7pOUhVb1?e=Iqjv6x) | Would exercise `has_macros` + `has_connections` routing together, and macro-policy rejection, if reachable | Individual blogger's (Chris Webb, well-known Power Query blogger) personal share -- terms unclear | **2026-07-18: DEAD -- HTTP 403 Forbidden.** Personal OneDrive share links like this are known to expire/require the owner's account; do not rely on this entry without finding a live replacement |
| Employee Sample Data (zip) | [download](https://www.thespreadsheetguru.com/wp-content/uploads/2022/12/EmployeeSampleData.zip) | VBA automation examples once unzipped -- `has_macros` routing, macro-policy rejection | Blog-provided free sample, no formal license -- local-testing-only | 2026-07-18: HTTP 200, confirmed ZIP signature, 125,295 bytes (the zip archive itself; unzip to get at the workbook(s) inside) |

## Large-scale / plain data (no Power Query, no macros)

| File | Link | Exercises | License / attribution | Verified |
| --- | --- | --- | --- | --- |
| Fragile States Index 2023 | [download](https://fragilestatesindex.org/wp-content/uploads/2023/06/FSI-2023-DOWNLOAD.xlsx) | Multi-year, larger real dataset -- plain-data `openpyxl` path, recalculation on a bigger sheet | Published by the Fund for Peace (a research organization) for public use; check the site's terms before any redistribution, fine for local testing | 2026-07-18: HTTP 200, confirmed ZIP signature, 26,952 bytes |
| Fragile States Index 2022 | [download](https://fragilestatesindex.org/wp-content/uploads/2022/07/fsi-2022-download.xlsx) | Same as above, prior year -- useful for a two-file "append rows" scale test | Same as above | 2026-07-18: HTTP 200, confirmed ZIP signature, 61,507 bytes |

## Repos and landing pages (browse for more, not single direct files)

These are not individual download links -- they're pages/repos to pull additional files from if the above isn't enough. Confirmed reachable (HTTP 200) on 2026-07-18; contents and structure can change over time.

| Source | Link | Note |
| --- | --- | --- |
| Chandoo VBA examples | <https://chandoo.org/wp/excel-vba/examples/> | Multiple downloadable `.xlsm` workbooks, individually linked from the page -- no single direct-download URL |
| Contextures sample data | <https://www.contextures.com/xlsampledata01.html> | Multiple small sample workbooks for specific Excel features |
| rohanmistry231/Practice-Datasets-for-Excel | <https://github.com/rohanmistry231/Practice-Datasets-for-Excel> | **MIT licensed** (confirmed via GitHub API) -- the cleanest reuse terms of anything in this catalog |
| ShreevaniRao/Data-Analysis-with-Excel-Power-Query | <https://github.com/ShreevaniRao/Data-Analysis-with-Excel-Power-Query> | Source repo for the two PowerQuery/Project-Dataset files above; **no LICENSE file** |

## What to actually test with these

- **Router decisions** (`control_plane/cli.py route`) -- confirm `has_pivots`/`has_connections`/`has_macros` are detected correctly against a real file, not just the corpus's placeholder OOXML parts.
- **Refresh** (`refresh` job step) -- run the Power Query files through `cli.py run` and confirm every connection refreshes individually and the result's `ok` field is trustworthy.
- **Macro policy** -- confirm `.xlsm` files here are correctly flagged `has_macros=True` and rejected by `macro_policy.is_macro_approved` against an empty allowlist; do **not** attempt to exercise `run_approved_macro` against these (unimplemented, issue #73).
- **Scale** -- the Fragile States Index files (or several of the above concatenated) are a reasonable stand-in for "bigger than the synthetic corpus's few-row fixtures" without needing a real customer workbook.
- **Validation contracts** -- write a one-off contract (`validate_contract.schema.json` shape) asserting something concrete about one of these (a known sheet name, an expected row-count floor) and confirm `validate-contract` reports it correctly.

None of this replaces the synthetic corpus for CI -- it's for a human to reach for when a specific real-world shape is worth checking by hand.
