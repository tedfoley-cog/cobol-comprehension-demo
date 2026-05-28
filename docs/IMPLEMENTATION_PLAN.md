# Implementation Plan — COBOL Comprehension Demo

## 1. What the Demo Proves

Devin can take a large, real-world COBOL codebase (~60 programs, 30+ copybooks, 38 JCL jobs) and produce a comprehensive system-wide comprehension map — dependency graphs, copybook tracing, batch-flow documentation, data lineage, and dead-code identification — in minutes rather than the months it typically takes human teams. As a secondary step, Devin converts one representative program to Python with equivalence tests, proving the comprehension-to-conversion pipeline.

## 2. What Devin Does Live

Devin runs the full comprehension workflow end-to-end: parsing COBOL source, tracing copybook dependencies, mapping batch flows from JCL, identifying dead code, and populating an interactive dashboard — then optionally converts one program to Python with tests.

## 3. Stack and Rationale

| Component | Choice | Source / Rationale |
|---|---|---|
| COBOL source | AWS Card Demo (`aws-samples/aws-mainframe-modernization-carddemo`) | Well-known public COBOL project with realistic credit card transaction processing; 31 core programs, 30 copybooks, 38 JCL, 17 BMS maps. Apache 2.0 licensed. |
| Source integration | Git submodule at `carddemo-source/` | Keeps demo repo clean; references upstream without copying |
| Analysis scripts | Python 3.11+ | Standard library + `re` for COBOL parsing; no exotic deps |
| Dashboard | Static HTML + vanilla JS + CSS | Opens with `python -m http.server`; no build step; consumes JSON from `dashboard/data/` |
| Dependency visualization | D3.js (CDN) | Interactive force-directed graph for program dependencies |
| Modernization target | Python | Natural choice for readable side-by-side comparison |
| CI | GitHub Actions | Checkout, pip install, ruff lint, HTML validation |
| COBOL syntax reference | IBM Enterprise COBOL Language Reference (SC27-1408), COBOL-85 standard | Column-based formatting (cols 7–72), COPY statement, WORKING-STORAGE SECTION, PROCEDURE DIVISION |
| JCL syntax reference | IBM z/OS JCL Reference (SA23-1385) | `//stepname EXEC PGM=`, `//ddname DD DSN=` patterns |

## 4. Repo Layout

```
cobol-comprehension-demo/
├── carddemo-source/              # Git submodule → aws-samples/aws-mainframe-modernization-carddemo
├── analysis/
│   ├── __init__.py
│   ├── parse_cobol.py            # Parse COBOL programs: extract divisions, COPY refs, CALL targets
│   ├── parse_copybooks.py        # Parse copybook field definitions, REDEFINES, byte offsets
│   ├── parse_jcl.py              # Parse JCL: extract job steps, PGM refs, DD statements
│   ├── build_dependency_graph.py # Build program→copybook→program dependency graph
│   ├── find_dead_code.py         # Identify unreferenced programs/copybooks
│   ├── trace_data_lineage.py     # Trace data flow: files→programs→copybooks→fields
│   └── generate_dashboard_data.py # Orchestrator: runs all analyses, writes JSON to dashboard/data/
├── dashboard/
│   ├── index.html                # Main dashboard shell (empty state until Devin populates)
│   ├── css/
│   │   └── style.css             # Dashboard styling
│   ├── js/
│   │   └── app.js                # Dashboard JS: loads JSON, renders panels
│   └── data/
│       └── .gitkeep              # Empty — populated by analysis scripts at demo time
├── modernization_example/
│   └── README.md                 # Placeholder: Devin fills this during the live demo
├── docs/
│   ├── IMPLEMENTATION_PLAN.md    # This file
│   ├── flowchart.html            # Standalone HTML flowchart
│   └── flowchart.png             # Rasterized flowchart screenshot
├── .github/workflows/
│   └── ci.yml                    # Simple CI: lint + validate
├── requirements.txt              # Python dependencies (ruff for linting)
├── README.md                     # Project overview, flowchart, instructions
├── DEMO_NOTES.md                 # Presenter cheat sheet (5–8 bullets)
└── .gitignore
```

## 5. Flowchart Outline

**Nodes:**
1. `COBOL` — COBOL Codebase (AWS Card Demo)
2. `PROMPT` — Prompt Devin
3. `PARSE` — Parse Programs
4. `COPY` — Trace Copybooks
5. `DEPS` — Map Dependencies
6. `BATCH` — Analyze Batch Flows
7. `DEAD` — Identify Dead Code
8. `LINEAGE` — Trace Data Lineage
9. `DASHBOARD` — Generate Dashboard
10. `VIEW` — Open in Browser
11. `CONVERT` — Convert to Python (optional)

**Edges:**
- COBOL → PROMPT → PARSE
- PARSE → COPY → DEPS
- PARSE → BATCH
- PARSE → DEAD
- DEPS → LINEAGE → DASHBOARD
- BATCH → DASHBOARD
- DEAD → DASHBOARD
- DASHBOARD → VIEW
- VIEW → CONVERT (dashed, optional)

## 6. Runtime Plan

1. Presenter opens the repo in a Devin session
2. Devin is prompted: "Analyze the COBOL source in carddemo-source/ and populate the comprehension dashboard"
3. Devin runs `python analysis/generate_dashboard_data.py` which orchestrates all analysis scripts
4. Analysis scripts parse 31 COBOL programs, 30 copybooks, 38 JCL files
5. JSON output is written to `dashboard/data/`
6. Devin opens `dashboard/index.html` via `python -m http.server 8000`
7. Presenter shows the populated dashboard in the browser tab
8. (Optional) Devin picks one program (e.g., CBTRN02C — transaction processing) and converts it to Python in `modernization_example/`

## 7. CI Plan

Single workflow (`ci.yml`):
- Checkout with submodules
- Set up Python 3.11
- Install deps (`pip install -r requirements.txt`)
- Run ruff linter on `analysis/` scripts
- Validate dashboard HTML (basic syntax check)
- Run analysis scripts in dry-run mode to verify they execute without errors

## 8. Risks and Unknowns

- **COBOL parsing without a proper compiler**: The analysis scripts use regex-based parsing, not a full COBOL grammar. This is sufficient for the demo's comprehension use case (extracting COPY references, CALL targets, WORKING-STORAGE fields) but won't handle every edge case in production COBOL.
- **AWS Card Demo structure may change**: Pinned to the current commit via submodule to avoid breakage.
- **BMS map parsing**: BMS maps use assembler-like syntax; the analysis scripts provide basic BMS inventory but don't parse individual map fields. This could be added as a future enhancement.
- **EBCDIC data files**: The data files in `app/data/EBCDIC/` are binary. The analysis scripts focus on source code (`.cbl`, `.cpy`, `.jcl`, `.bms`), not data files.
