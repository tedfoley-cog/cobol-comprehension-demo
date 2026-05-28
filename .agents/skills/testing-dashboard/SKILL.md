---
name: testing-cobol-dashboard
description: Test the COBOL comprehension dashboard end-to-end. Use when verifying analysis pipeline output, dashboard rendering, or data accuracy after code changes.
---

# Testing the COBOL Comprehension Dashboard

## Prerequisites

- Python 3 available
- The `carddemo-source/` submodule must be initialized (`git submodule update --init`)
- No external services or secrets required — everything runs locally

## Step 1: Run the Analysis Pipeline

```bash
cd /home/ubuntu/cobol-comprehension-demo
python -m analysis.generate_dashboard_data carddemo-source/app dashboard/data
```

Expected output: 6 JSON files in `dashboard/data/` (inventory, dependency_graph, dead_code, data_lineage, deep_analysis, summary).

Pipeline takes ~15-20 seconds for the full CardDemo corpus (44 programs, 62 copybooks, 46 JCL).

## Step 2: Serve the Dashboard

```bash
python -m http.server 8000 --directory dashboard &
```

Navigate to `http://localhost:8000` in the browser.

## Step 3: Verify Summary Cards

The dashboard header shows 8 summary cards. Expected values for the current CardDemo corpus:

| Card | Expected |
|------|----------|
| Programs | 44 |
| Copybooks | 62 (30 shared) |
| JCL Jobs | 46 |
| Dependencies | 629 |
| Cross-Refs | 181 (100 implicit) |
| High Risk | 25 (27 COMMAREA) |
| Dead Code | 12 |
| REDEFINES | 617 |

These numbers may change if the CardDemo source is updated.

## Step 4: Navigate All Tabs

The dashboard has 8 main tabs and 5 sub-tabs under Field Cross-Ref:

**Main tabs:** Programs, Dependencies, Field Cross-Ref, Data Lineage, Batch Flows, Dead Code, Copybooks, Impact Analysis

**Field Cross-Ref sub-tabs:** Shared Fields, Implicit Connections, COMMAREA Flow, REDEFINES Chains, Program Coupling

Tabs use `data-panel` attributes. Click each tab button to activate the corresponding panel.

## Step 5: Byte-Size Accuracy Assertions

The most critical accuracy check is byte sizes in the Field Cross-Ref tab. Compare against the actual COBOL source copybooks in `carddemo-source/app/cpy/`.

Key assertions (verify these haven't regressed):

| Field | Source PIC | Expected Size | Expected Offset |
|-------|-----------|---------------|----------------|
| COCOM01Y.CDEMO-FROM-TRANID | X(04) | 4B | 0 |
| COCOM01Y.CDEMO-FROM-PROGRAM | X(08) | 8B | 4 |
| COTTL01Y.CCDA-TITLE01 | X(40) | 40B | 0 |
| COTTL01Y.CCDA-TITLE02 | X(40) | 40B | 40 |

If sizes are doubled (8B, 16B, 81B), the PIC-counting bug in `parse_copybooks.py` has regressed.

Also verify CUSTREC shows 500 bytes total (not ~1000).

## Step 6: COMMAREA Flow Verification

Under Field Cross-Ref → COMMAREA Flow:
- Should show 27 rows
- COSGN00C → COADM01C should show dispatch type "literal"
- COPAUS0C → COSGN00C should show dispatch type "dynamic"
- A D3 force-directed graph SVG should render above the table

## Step 7: Impact Analysis Verification

The Impact Analysis tab should show:
- First row: HIGH risk, COCOM01Y.CDEMO-FROM-TRANID, 21 programs affected
- COTTL01Y.CCDA-TITLE01 should show writers = "—" (read-only field)
- Fields with writers should list actual program IDs

## Step 8: Program Coupling

Under Field Cross-Ref → Program Coupling:
- Top pair should be COACTUPC ↔ COACTVWC with score 12
- Shared copybooks should be listed for each pair

## Known Issues

- The browser tool's `type` action may fail on the filter input fields. Use Playwright via CDP or JS console to test filter functionality programmatically. The browser tool's `console` action may also not capture logs reliably — use `document.title` to pass data back, or use Playwright.
- The Copybooks tab renders all 62 copybooks in a single long page. CUSTREC may be offscreen — use the browser tool's full HTML output or grep the page HTML to verify its data.
- COMP/COMP-3 byte sizes depend on the USAGE keyword NOT being stripped before the COMP check runs. If `S9(7)V99 USAGE COMP-3` shows 9B instead of 5B, check the keyword strip list in `_estimate_pic_size()` in `parse_copybooks.py`.

## Devin Secrets Needed

None — all testing is local with no external dependencies.
