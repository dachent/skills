# External test corpus

Manual, third-party fixtures for tests that the small generated corpus cannot
represent. Nothing here is vendored or downloaded by CI.

## Rules

- Download into a disposable directory; pin the resolved URL, byte size, and
  SHA-256 (or ETag for a mutable source) in the run record.
- Re-inspect every download. Links, content, and mutable datasets can change.
- Treat sources without an explicit license as local-test-only; do not mirror
  or redistribute them.
- Never enable macros from an external fixture outside a disposable VM.
- An `.xlsx` sheet has 1,048,576 rows. With a header in row 1, load at most
  1,048,575 data rows.

## Core fixtures

| Fixture | Verified shape | Use | Acquisition / reuse |
| --- | --- | --- | --- |
| [Excel Project Dataset.xlsx](https://raw.githubusercontent.com/ShreevaniRao/Data-Analysis-with-Excel-Power-Query/main/Excel%20Project%20Dataset.xlsx) | 316,483-byte `.xlsx`; two value-backed Tables. `Table2=A1:O1001`; column 13 (`Age Brackets`) is calculated; one cache feeds six Pivots and slicers; no connection part. | Best real Table→shared-cache→multi-Pivot→slicer preservation seed. Scale its 14 writable columns; let Excel propagate the calculated column. | No repository license: local testing only. |
| [PowerQuery.xlsx](https://raw.githubusercontent.com/ShreevaniRao/Data-Analysis-with-Excel-Power-Query/main/PowerQuery.xlsx) | 120,869-byte `.xlsx`; 11 workbook connections; query-backed Table feeds a Pivot. | Existing-connection routing, attributable per-connection refresh, recalc, save, and cleanup. Not the generic value-backed Table path. | No repository license: local testing only. |
| [Microsoft Financial Sample.xlsx](https://go.microsoft.com/fwlink/?LinkID=521962) | 83,418-byte `.xlsx`; one 700-row Table (`financials`); no Pivot cache or connection. | Official Table-only/plain-workbook baseline. | Microsoft tutorial sample. |
| [MiniExcel Test1,000,000x10.xlsx](https://raw.githubusercontent.com/mini-software/MiniExcel/master/benchmarks/MiniExcel.Benchmarks/Test1%2C000%2C000x10.xlsx) | Native `.xlsx`; `A1:J1000000`; 1,000,000 rows, 10,000,000 repeated-string cells; 33,420,761 bytes; no Table/Pivot/connection/shared-strings part. | Dense, low-cardinality native Excel open/save, memory, timeout, and PID-cleanup control. It does **not** test Table replacement or Pivot refresh. | Apache-2.0. SHA-256 `3f3cd992ff51886ce4832838563572dd471a582d864d820d5db9bd3f9144b6df`. |
| [CSVBase Chrome Top Million.xlsx](https://csvbase.com/calpaterson/crux-top-list.xlsx) | Native `.xlsx`; `A1:C1000001`; 1,000,000 data rows + header; 1,131,063 populated cells; 65,530 hyperlinks/relationships; 9,898,705 bytes; no Table/Pivot/connection. | Sparse-row and relationship-pressure native Excel control. It does **not** test Pivot refresh. | Table metadata has no license: local testing only. SHA-256 `71e8909f4da8517ae05c2d110eaadebd7934a14f9214927cf24ec2308e95015a`. |
| [Redfin county Market Tracker](https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/county_market_tracker.tsv000.gz) | Mutable gzip TSV; observed 1,351,879 data rows + header, 58 columns, 241,131,599 compressed bytes. Mixed dates, categories, integers, decimals, nulls, and geographic cardinality. | Preferred realistic source for deterministic 100k/500k/750k/1m Table→Pivot slices. The full source cannot fit one sheet. | Official Redfin Data Center; terms do not state a dataset-specific redistribution license. Attribute, use locally, re-count, and capture ETag. |
| [NYC 311 one-million-row sample](https://raw.githubusercontent.com/wiki/jqnatividad/qsv/files/NYC_311_SR_2010-2020-sample-1M.7z) | 48,111,517-byte 7z → 538,951,068-byte CSV; 1,000,000 data rows + header; 41 columns with dates, long text, nulls, and coordinates. | Wide/high-cardinality adversarial sidecar. Run 500k before 1m; harder on marshaling and Pivot-cache cardinality than repeated strings. | qsv redistribution of NYC Open Data. Archive SHA-256 `5c5f876b097ed6b51d52a5309c029ac605e959204cfb64a41f847bdc3ef3165b`; CSV `18f0dd774a6c4b79da3dbf3aa0cd878d374dab132226af2c629d9eef9595061b`. |

### Larger Redfin tiers

Reachable but intentionally excluded from routine certification because county
already exceeds the required row scale:

| Geography | Direct source | Observed compressed size |
| --- | --- | ---: |
| City | [city_market_tracker.tsv000.gz](https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/city_market_tracker.tsv000.gz) | 1,001,106,945 bytes |
| ZIP code | [zip_code_market_tracker.tsv000.gz](https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz) | 1,548,403,907 bytes |
| Neighborhood | [neighborhood_market_tracker.tsv000.gz](https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/neighborhood_market_tracker.tsv000.gz) | 2,353,602,188 bytes |

## Supplemental fixtures

| Family | Files | Use / caveat |
| --- | --- | --- |
| TrumpExcel plain tables | [Retail Inventory](https://www.dropbox.com/scl/fi/f7thmp8268s7vwgksidfr/01-Retail-Inventory.xlsx?rlkey=lu181vqokcewwvco8ak1rxmk7&dl=1), [Project Management](https://www.dropbox.com/scl/fi/4x53npvymfmrgr0extvgx/02-Project-Management.xlsx?rlkey=qtj9bwnlt94jm7jhfppwzgrbq&dl=1), [Real Estate](https://www.dropbox.com/scl/fi/z6kbab7psonkymmr722i6/03-Real-Estate-Listings.xlsx?rlkey=7hx0ojbiuxb34kqd9g1y0jjse&dl=1), [Restaurant Sales](https://www.dropbox.com/scl/fi/qnk47lzecilxt1suz2tsg/04-Restaurant-Sales.xlsx?rlkey=1ovujyhw1ox6banzbophcegrf&dl=1) | Small schema/date/category baselines; no formal license. |
| Excelx plain tables | [Product Sales](https://excelx.com/wp-content/uploads/2025/06/Product-Sales-Region.xlsx), [Online Orders](https://excelx.com/wp-content/uploads/2025/06/Online-Store-Orders.xlsx), [Retail Transactions](https://excelx.com/wp-content/uploads/2025/06/Retail-Store-Transactions.xlsx), [Purchase History](https://excelx.com/wp-content/uploads/2025/06/Customer-Purchase-History.xlsx) | Small router/recalc baselines; no formal license. |
| Fragile States Index | [2023](https://fragilestatesindex.org/wp-content/uploads/2023/06/FSI-2023-DOWNLOAD.xlsx), [2022](https://fragilestatesindex.org/wp-content/uploads/2022/07/fsi-2022-download.xlsx) | Small two-file schema/append baseline. The 2023 workbook has only 180 populated rows; it is not a scale fixture. |
| Macro sample | [Employee Sample Data.zip](https://www.thespreadsheetguru.com/wp-content/uploads/2022/12/EmployeeSampleData.zip) | Macro detection and allowlist rejection only; never enable content. No formal license. |

More candidates: [Chandoo VBA examples](https://chandoo.org/wp/excel-vba/examples/),
[Contextures samples](https://www.contextures.com/xlsampledata01.html),
[MIT-licensed practice datasets](https://github.com/rohanmistry231/Practice-Datasets-for-Excel),
and the [Power Query source repository](https://github.com/ShreevaniRao/Data-Analysis-with-Excel-Power-Query).
The former Chris Webb OneDrive sample is omitted because it returns HTTP 403.

## Scenario matrix

| Goal | Fixtures | Procedure | Required evidence |
| --- | --- | --- | --- |
| Router inventory | Financial Sample, Project Dataset, PowerQuery | Run `control_plane/cli.py route`; compare raw OOXML inventory. | Table-only → `openpyxl`; Pivot/connection → `excel_required`; exact detected features. |
| Existing connection refresh | PowerQuery | Run the supported `open → refresh → recalc → save_as` job in owned Excel. | Every named connection outcome, `xlDone`, `ok=true`, valid saved package, zero owned Excel PIDs. |
| Native scale controls | MiniExcel, Chrome Top Million | Inventory read-only; then owned-Excel open/save-as/close in separate fresh processes. Do not perform a normal editable `openpyxl` load. | Bounded phase time/memory, package opens, saved dimensions/values survive, zero orphaned PID. |
| Real Table→Pivot scale | Project Dataset + generated 500k sidecar; then purpose-built redistributable template + pinned Redfin slices | Preserve/resize the existing Table; bulk-write bounded 2-D chunks only to writable column runs; refresh linked cache once and all reports. Test 100k → 500k → 750k → 1m in fresh processes. | Typed Table-body equality; formula propagation; same Table/cache/report/slicer graph; independent Pivot aggregates; resource telemetry; atomic publish only on full success. |
| Width/cardinality stress | NYC 311 at 500k, then 1m | Use a template with a deliberately small Pivot field set; retain the wide Table payload. | Same semantic/resource/cleanup gates; compare against low-cardinality MiniExcel control without treating either as a substitute. |
| Macro policy | Employee sample | Inventory and empty-allowlist check only. | `has_macros=true`; execution rejected; no macro runs. |

The external corpus supplements deterministic CI; it never replaces it. A
large native `.xlsx`, a large sidecar, and a Pivot-bearing workbook test
different failure surfaces and must not be used as evidence for one another.
