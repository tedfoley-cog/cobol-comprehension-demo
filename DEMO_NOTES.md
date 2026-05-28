# Demo Cheat Sheet — COBOL Comprehension & Modernization

## Setup (do this before joining the call)
- [ ] Open the repo in a fresh Devin session
- [ ] Confirm the submodule is checked out: `ls carddemo-source/app/cbl/` should show COBOL files

## The Prompt

Paste this into the Devin session to start the demo:

> Analyze the CardDemo COBOL application in `carddemo-source/`. Run the comprehension pipeline and open the dashboard. Then extract the business logic from the sign-on flow through the transaction screens — read the actual COBOL PROCEDURE DIVISIONs and document every business rule you find. After that, tell me what would break if we retired the `COCOM01Y` copybook — trace every program that uses it and classify the impact by field. Finally, convert the sign-on program `COSGN00C` to a Spring Boot REST controller with equivalent authentication logic and write it to `modernization_example/`.

## Demo Flow (3 phases, ~10-15 minutes total)

### Phase 1: Comprehension & Business Logic Extraction (~5 min)

**What the audience sees**: Devin reads actual COBOL source code, traces program
flow, and produces structured business documentation.

1. Devin runs the analysis pipeline → dashboard populates with 44 programs,
   629 dependencies, 181 field cross-references, 27 COMMAREA flows
2. Devin opens the dashboard in the browser — walk through the summary cards
3. Devin reads `COSGN00C.cbl` (sign-on) line by line and extracts:
   - Authentication logic: read USRSEC file, compare passwords
   - Role routing: admin → COADM01C, regular user → COMEN01C
   - Error handling: user not found (RESP=13), wrong password
4. Devin traces through `COMEN01C.cbl` (menu) and finds 11 menu options
   defined in the `COMEN02Y.cpy` copybook — dynamic dispatch via XCTL
5. Devin reads `COTRN02C.cbl` (transaction add) and finds input validation
   rules, cross-reference lookups, confirmation flow
6. Output: `docs/business_rules.md` with specific COBOL line references

**Talk track**: "Notice Devin isn't just running a regex — it's reading the
PROCEDURE DIVISION, understanding EVALUATE branches, tracing MOVE statements,
and explaining what each paragraph does in business terms. This is the work that
takes a mainframe team weeks."

### Phase 2: Copybook Impact Analysis (~3 min)

**What the audience sees**: Devin answers "what would break if we changed this
shared data structure?" by tracing every program that touches it.

1. Devin reads `COCOM01Y.cpy` — the COMMAREA shared by 17+ CICS programs
2. Devin traces field-by-field: CDEMO-USER-ID used for auth in every program,
   CDEMO-TO-PROGRAM used for XCTL navigation, CDEMO-CUST-ID passed to
   downstream screens
3. Devin classifies impact categories:
   - **Navigation** (FROM/TO PROGRAM/TRANID) — all 17 programs break
   - **Authentication** (USER-ID, USER-TYPE) — sign-on and menu programs
   - **Customer context** (CUST-ID, CUST-FNAME) — account/card screens
   - **Screen state** (LAST-MAP, PGM-CONTEXT) — all CICS programs
4. Devin proposes the modern equivalent: COMMAREA → JWT + session store
5. Output: `docs/impact_analysis_COCOM01Y.md`

**Talk track**: "COCOM01Y is 50 lines of COBOL but it's the nervous system of
the entire application. Every screen depends on it for session state. This is
exactly the kind of invisible coupling that breaks modernization projects —
you retire one copybook and 17 programs stop working."

### Phase 3: Live Modernization (~5 min)

**What the audience sees**: Devin converts a COBOL program to Spring Boot Java,
mapping every construct to its modern equivalent.

1. Devin reads `COSGN00C.cbl` and maps:
   - `EXEC CICS READ DATASET('USRSEC')` → `UserRepository.findById()`
   - `IF SEC-USR-PWD = WS-USER-PWD` → `passwordEncoder.matches()`
   - `EXEC CICS XCTL PROGRAM('COADM01C')` → redirect response
   - COMMAREA fields → session context DTO
2. Devin generates working Spring Boot code:
   - `AuthController.java` — REST endpoints
   - `AuthService.java` — business logic (the 4 login paths)
   - `User.java` — entity mapping SEC-USER-DATA byte layout
   - `SessionContext.java` — maps CARDDEMO-COMMAREA fields
   - `AuthServiceTest.java` — tests all 4 paths
3. Devin writes `CONVERSION_NOTES.md` — field-by-field mapping table with
   byte offsets, paragraph-by-paragraph method mapping
4. Output: working Maven project in `modernization_example/`

**Talk track**: "The conversion isn't line-by-line transliteration. Devin
understands that CICS pseudo-conversational programming doesn't exist in REST,
so it restructures the flow. The COMMAREA becomes a session DTO. The BMS map
becomes request/response objects. The EVALUATE on EIBAID becomes separate
endpoints. This is semantic migration, not syntax translation."

## Key Numbers to Verify
| Metric | Expected |
|---|---|
| Programs analyzed | 44 |
| Copybooks | 62 (30 shared) |
| JCL jobs | 46 |
| Dependency edges | 629 |
| Field cross-references | 181 |
| Implicit connections | 100 |
| COMMAREA flows | 27 |
| REDEFINES chains | 617 |
| High-risk fields | 25 |
| Programs using COCOM01Y | 17 (online CICS) |

## If Asked...

**"Can it handle our codebase?"** — "CardDemo is 24K lines. The analysis
scales — the field cross-referencing is O(programs × fields), not exponential.
For a 5M LOC codebase, you'd run it in batches by subsystem and Devin would
stitch the results together."

**"How accurate is the business logic extraction?"** — "Every rule Devin
extracts references the specific COBOL paragraph and line it came from. You can
verify it against the source. The byte offsets in the copybook analysis are
computed from PIC clauses, not guessed."

**"What about COMP-3 / packed decimal?"** — "The byte-size calculator handles
COMP and COMP-3 fields. COMP-3 uses ceil((digits+1)/2) bytes. We verified this
against the CardDemo copybooks."
