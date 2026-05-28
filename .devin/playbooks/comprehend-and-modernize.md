# COBOL Comprehension & Modernization

You are analyzing a real COBOL credit-card transaction processing system
(AWS CardDemo — 44 programs, 62 copybooks, 46 JCL jobs, ~24K LOC) and
producing three deliverables:

1. **Business logic extraction** — structured documentation of what the code does
2. **Copybook impact analysis** — trace what breaks if a shared data structure changes
3. **Live modernization** — convert a COBOL program to Spring Boot Java

Work in the repo root: the COBOL source is in `carddemo-source/app/`.

---

## Phase 1 — Comprehension & Business Logic Extraction

### Step 1: Run the analysis pipeline

```bash
python -m analysis.generate_dashboard_data carddemo-source/app dashboard/data
```

This builds the knowledge graph: dependency edges, field cross-references,
COMMAREA flows, implicit connections, REDEFINES chains, impact rankings.
Wait for it to complete (~15-20 seconds).

### Step 2: Serve the dashboard

```bash
python -m http.server 8000 --directory dashboard &
```

Open `http://localhost:8000` in the browser so the audience can see the
visualization. Walk through the summary cards briefly — call out the numbers
(44 programs, 629 dependencies, 181 field cross-references, 27 COMMAREA flows).

### Step 3: Extract business logic from the sign-on flow

Read each of these programs in order and extract business rules by reading the
actual COBOL source. Do NOT just describe the file headers — read the
PROCEDURE DIVISION and trace the actual logic.

**Programs to analyze (in this order — this is the user's login-to-menu flow):**

1. `carddemo-source/app/cbl/COSGN00C.cbl` — Sign-on screen
2. `carddemo-source/app/cbl/COMEN01C.cbl` — Main menu (regular users)
3. `carddemo-source/app/cbl/COADM01C.cbl` — Admin menu
4. `carddemo-source/app/cbl/COTRN00C.cbl` — Transaction listing
5. `carddemo-source/app/cbl/COTRN02C.cbl` — Transaction add (online)
6. `carddemo-source/app/cbl/CBTRN02C.cbl` — Daily transaction posting (batch)

Also read the key copybooks these programs share:

- `carddemo-source/app/cpy/COCOM01Y.cpy` — COMMAREA (session state)
- `carddemo-source/app/cpy/CSUSR01Y.cpy` — User security record
- `carddemo-source/app/cpy/COMEN02Y.cpy` — Menu option definitions
- `carddemo-source/app/cpy/CVTRA05Y.cpy` — Transaction record (350 bytes)
- `carddemo-source/app/cpy/CVACT01Y.cpy` — Account record (300 bytes)
- `carddemo-source/app/cpy/CVACT03Y.cpy` — Card-account cross-reference

**For each program, extract:**

- **Purpose**: one-line business function
- **Entry conditions**: what triggers this program (transaction ID, XCTL from where)
- **Data inputs**: which VSAM files / CICS datasets it reads (e.g., `USRSEC`, `TRANSACT`, `ACCTDAT`)
- **Data outputs**: what it writes or updates
- **Business rules**: the actual decision logic from EVALUATE/IF/PERFORM statements.
  Quote the specific COBOL conditions — e.g., "IF SEC-USR-PWD = WS-USER-PWD" or
  "EVALUATE TRUE WHEN USERIDI OF COSGN0AI = SPACES" — not vague summaries.
- **Navigation**: where control transfers next (XCTL/LINK targets, both literal and dynamic)
- **COMMAREA usage**: which fields from COCOM01Y it reads vs writes

Write the output to `docs/business_rules.md` with a section per program.

### Step 4: Show the application architecture

After extracting business rules, summarize the overall application architecture
as an ASCII diagram showing how programs connect through COMMAREA/XCTL:

```
COSGN00C (Sign-on)
  ├── [admin] ──XCTL──> COADM01C (Admin Menu)
  │                        └── same 11 options as regular menu
  └── [user] ──XCTL──> COMEN01C (Main Menu)
                          ├── Opt 1: COACTVWC (Account View)
                          ├── Opt 2: COACTUPC (Account Update)
                          ├── ...
                          └── Opt 8: COTRN02C (Transaction Add)
```

---

## Phase 2 — Copybook Impact Analysis

### Step 5: Analyze COCOM01Y retirement impact

The question is: **"What would break if we retired the COCOM01Y copybook?"**

Read `carddemo-source/app/cpy/COCOM01Y.cpy` to understand its structure (the
CARDDEMO-COMMAREA — session state passed between all CICS programs).

Then systematically trace the impact:

1. **Find all programs that COPY COCOM01Y** — there are 17 CICS online programs
   that include it. List every one.

2. **Classify how each program uses the COMMAREA fields.** Read the actual source
   of at least 5-6 programs to find specific field references:
   - `CDEMO-FROM-TRANID` / `CDEMO-FROM-PROGRAM` — navigation breadcrumbs
   - `CDEMO-TO-TRANID` / `CDEMO-TO-PROGRAM` — XCTL dispatch targets
   - `CDEMO-USER-ID` / `CDEMO-USER-TYPE` — authentication & authorization
   - `CDEMO-CUST-ID` / `CDEMO-CUST-FNAME` / `CDEMO-CUST-LNAME` — customer context
   - `CDEMO-ACCT-ID` / `CDEMO-ACCT-STATUS` — account context
   - `CDEMO-CARD-NUM` — card context
   - `CDEMO-LAST-MAP` / `CDEMO-LAST-MAPSET` — screen state
   - `CDEMO-PGM-CONTEXT` (88 levels: CDEMO-PGM-ENTER / CDEMO-PGM-REENTER) — first-entry vs re-entry

3. **Assess blast radius**: COCOM01Y is the application's nervous system. Every
   CICS program uses it to know where the user came from, where to go next, who
   the user is, and what customer/account/card is selected. Retiring it means
   replacing the entire session management, navigation, and authorization mechanism.

4. **Identify implicit connections**: Use the deep analysis data
   (`dashboard/data/deep_analysis.json`) to find fields in OTHER copybooks that
   have matching PIC and size to COCOM01Y fields — these are the invisible
   connections that would also break.

5. **Propose a migration path**: If the audience asks "so how would we actually
   do it?", explain that COCOM01Y maps to a session/JWT token in modern architecture:
   - `CDEMO-USER-ID` + `CDEMO-USER-TYPE` → JWT claims
   - `CDEMO-FROM-PROGRAM` / `CDEMO-TO-PROGRAM` → URL routing / browser history
   - `CDEMO-CUST-ID` / `CDEMO-ACCT-ID` / `CDEMO-CARD-NUM` → request parameters or session store
   - `CDEMO-PGM-CONTEXT` → HTTP method (GET = first entry, POST = re-entry)

Write the output to `docs/impact_analysis_COCOM01Y.md`.

---

## Phase 3 — Live Modernization

### Step 6: Convert COSGN00C to Spring Boot

Convert the sign-on program (`COSGN00C.cbl`) to a Spring Boot REST controller.
This is the right program to convert because:
- It's small enough to finish in a demo (~260 lines)
- It has clear business logic (authenticate, route by role)
- It touches 3 data sources (USRSEC file, COMMAREA, BMS screen)
- It demonstrates the COBOL-to-Java mapping concretely

**Read the full source** of `carddemo-source/app/cbl/COSGN00C.cbl` and the
copybooks it uses (`COCOM01Y.cpy`, `CSUSR01Y.cpy`, `COTTL01Y.cpy`).

**Create these files in `modernization_example/`:**

```
modernization_example/
├── src/main/java/com/carddemo/
│   ├── CardDemoApplication.java        # Spring Boot main class
│   ├── controller/
│   │   └── AuthController.java         # Maps COSGN00C logic
│   ├── model/
│   │   ├── User.java                   # Maps CSUSR01Y (SEC-USER-DATA)
│   │   └── SessionContext.java         # Maps COCOM01Y (CARDDEMO-COMMAREA)
│   ├── repository/
│   │   └── UserRepository.java         # Maps USRSEC VSAM file reads
│   ├── service/
│   │   └── AuthService.java            # Business logic from PROCESS-ENTER-KEY
│   └── dto/
│       ├── LoginRequest.java           # Maps COSGN0AI (BMS input)
│       └── LoginResponse.java          # Maps COSGN0AO (BMS output)
├── src/main/resources/
│   └── application.properties
├── src/test/java/com/carddemo/
│   └── service/
│       └── AuthServiceTest.java        # Tests the 4 COSGN00C paths
├── pom.xml
└── CONVERSION_NOTES.md                 # Field-by-field mapping table
```

**Key mapping rules (trace these from the actual COBOL source):**

| COBOL Construct | Java Equivalent |
|---|---|
| `EXEC CICS READ DATASET('USRSEC')` | `userRepository.findById(userId)` |
| `IF SEC-USR-PWD = WS-USER-PWD` | `passwordEncoder.matches(request.getPassword(), user.getPassword())` |
| `IF CDEMO-USRTYP-ADMIN` (88-level) | `if (user.getType() == UserType.ADMIN)` |
| `EXEC CICS XCTL PROGRAM('COADM01C')` | Return `LoginResponse` with `redirectUrl = "/admin/menu"` |
| `EXEC CICS XCTL PROGRAM('COMEN01C')` | Return `LoginResponse` with `redirectUrl = "/menu"` |
| `MOVE WS-USER-ID TO CDEMO-USER-ID` | Set session context: `session.setUserId(userId)` |
| `EVALUATE EIBAID` (PF key handling) | Different HTTP endpoints or request parameters |
| `MOVE 'User not found' TO WS-MESSAGE` | Throw `AuthenticationException` with message |
| `RESP(WS-RESP-CD) ... WHEN 13` | `userRepository.findById()` returns `Optional.empty()` |

**The 4 business logic paths in COSGN00C (extract from PROCEDURE DIVISION):**

1. **First entry** (`EIBCALEN = 0`): Display blank sign-on screen → `GET /login` returns login page
2. **Valid admin login**: Read USRSEC, password matches, user type = 'A' → redirect to admin menu
3. **Valid regular login**: Read USRSEC, password matches, user type = 'U' → redirect to user menu
4. **Failed login**: Wrong password (resp=0 but pwd mismatch) or user not found (resp=13)

**In CONVERSION_NOTES.md**, include:
- A field-by-field mapping table (COBOL field → Java field, with byte offsets)
- A paragraph-by-paragraph mapping (COBOL paragraph → Java method)
- What was preserved vs. what changed (e.g., CICS pseudo-conversational pattern
  doesn't exist in REST — explain why)
- The COMMAREA fields this program writes and how they map to session state

### Step 7: Verify the conversion compiles

If Maven is available, run `mvn compile` in the modernization_example directory.
If not, at minimum verify the Java files have no obvious syntax errors by
reviewing them.

---

## Delivery

After completing all three phases, send the user a summary with:

1. Link to the dashboard (localhost:8000)
2. The three documents produced:
   - `docs/business_rules.md`
   - `docs/impact_analysis_COCOM01Y.md`
   - `modernization_example/CONVERSION_NOTES.md`
3. The working Spring Boot code in `modernization_example/`
4. Commit everything and create a PR

**Important**: The value of this demo is that Devin READ the actual COBOL source
and reasoned about it. Every business rule cited should reference the specific
COBOL line or paragraph it came from. Every mapping should trace back to the
source. Do not generate generic descriptions — ground everything in the code.
