# Impact Analysis: Retiring COCOM01Y (CARDDEMO-COMMAREA)

## Executive Summary

**COCOM01Y cannot be retired without replacing the entire session management,
navigation, authorization, and entity-context subsystem of the CardDemo
application.** It is the application's nervous system — every CICS online
program depends on it. Retiring it would break **17 programs** across **14
fields**, affecting authentication, navigation, role-based access control,
and cross-screen data passing.

---

## 1. What COCOM01Y Contains

The copybook defines `CARDDEMO-COMMAREA` — the CICS communication area passed
between all online programs via `EXEC CICS XCTL COMMAREA(...)` and
`EXEC CICS RETURN COMMAREA(...)`:

```cobol
01 CARDDEMO-COMMAREA.
   05 CDEMO-GENERAL-INFO.
      10 CDEMO-FROM-TRANID          PIC X(04).     ← offset 0
      10 CDEMO-FROM-PROGRAM         PIC X(08).     ← offset 4
      10 CDEMO-TO-TRANID            PIC X(04).     ← offset 12
      10 CDEMO-TO-PROGRAM           PIC X(08).     ← offset 16
      10 CDEMO-USER-ID              PIC X(08).     ← offset 24
      10 CDEMO-USER-TYPE            PIC X(01).     ← offset 32
         88 CDEMO-USRTYP-ADMIN      VALUE 'A'.
         88 CDEMO-USRTYP-USER       VALUE 'U'.
      10 CDEMO-PGM-CONTEXT          PIC 9(01).     ← offset 33
         88 CDEMO-PGM-ENTER         VALUE 0.
         88 CDEMO-PGM-REENTER       VALUE 1.
   05 CDEMO-CUSTOMER-INFO.
      10 CDEMO-CUST-ID              PIC 9(09).     ← offset 34
      10 CDEMO-CUST-FNAME           PIC X(25).     ← offset 43
      10 CDEMO-CUST-MNAME           PIC X(25).     ← offset 68
      10 CDEMO-CUST-LNAME           PIC X(25).     ← offset 93
   05 CDEMO-ACCOUNT-INFO.
      10 CDEMO-ACCT-ID              PIC 9(11).     ← offset 118
      10 CDEMO-ACCT-STATUS          PIC X(01).     ← offset 129
   05 CDEMO-CARD-INFO.
      10 CDEMO-CARD-NUM             PIC 9(16).     ← offset 130
   05 CDEMO-MORE-INFO.
      10 CDEMO-LAST-MAP             PIC X(7).      ← offset 146
      10 CDEMO-LAST-MAPSET          PIC X(7).      ← offset 153
```

---

## 2. Programs That COPY COCOM01Y

All **17 CICS online programs** include this copybook. Every one would fail to
compile if COCOM01Y were removed:

| # | Program | Function | Trans ID |
|---|---------|----------|----------|
| 1 | COSGN00C | Sign-on / Authentication | CC00 |
| 2 | COMEN01C | Main Menu (regular users) | CM00 |
| 3 | COADM01C | Admin Menu | CA00 |
| 4 | COACTVWC | Account View | CA01 |
| 5 | COACTUPC | Account Update | CA02 |
| 6 | COCRDLIC | Credit Card List | CC01 |
| 7 | COCRDSLC | Credit Card View | CC02 |
| 8 | COCRDUPC | Credit Card Update | CC03 |
| 9 | COTRN00C | Transaction List | CT00 |
| 10 | COTRN01C | Transaction View | CT01 |
| 11 | COTRN02C | Transaction Add | CT02 |
| 12 | COBIL00C | Bill Payment | CB00 |
| 13 | CORPT00C | Transaction Reports | CR00 |
| 14 | COUSR00C | User List | CU00 |
| 15 | COUSR01C | User Add | CU01 |
| 16 | COUSR02C | User Update | CU02 |
| 17 | COUSR03C | User Delete | CU03 |

---

## 3. Impact by Field

### Category A: Navigation & Session Flow (breaks every program)

| Field | PIC | Programs | Total Refs | Impact |
|-------|-----|----------|-----------|--------|
| `CDEMO-FROM-TRANID` | X(04) | **21** (all 17 + 4 subsystem pgms) | 53 | Every program writes this before XCTL to record "where the user came from." Without it, no program knows its caller's transaction context. |
| `CDEMO-FROM-PROGRAM` | X(08) | **21** | 70 | Programs check this to decide return-navigation logic. E.g., `COACTUPC` checks `IF CDEMO-FROM-PROGRAM = LIT-MENUPGM` to decide whether PF3 goes to menu or to a sub-detail. |
| `CDEMO-TO-PROGRAM` | X(08) | **20** | 82 | The target for `EXEC CICS XCTL PROGRAM(CDEMO-TO-PROGRAM)`. Removing this field means no program can dynamically navigate to another. |
| `CDEMO-TO-TRANID` | X(04) | **6** | 12 | Used by complex screens (COACTUPC, COACTVWC, COCRDSLC, COCRDUPC, COTRTLIC, COTRTUPC) to set the RETURN TRANSID dynamically. |
| `CDEMO-PGM-CONTEXT` | 9(01) | **14** | 17 | The first-entry vs re-entry flag. Every CICS program checks `IF NOT CDEMO-PGM-REENTER` on entry. Without it, programs cannot distinguish between initial display and user interaction — the entire pseudo-conversational pattern breaks. |
| `CDEMO-LAST-MAP` | X(7) | **7** | 29 | Screen state tracking. Programs like COCRDLIC, COACTUPC use it to detect which BMS map was last displayed, enabling proper screen refresh. |
| `CDEMO-LAST-MAPSET` | X(7) | **7** | 27 | Paired with LAST-MAP. COCRDUPC checks `CDEMO-LAST-MAPSET EQUAL LIT-CCLISTMAPSET` to decide whether to show the card list or the update form. |

### Category B: Authentication & Authorization (breaks login and access control)

| Field | PIC | Programs | Total Refs | Impact |
|-------|-----|----------|-----------|--------|
| `CDEMO-USER-ID` | X(08) | **3** (COSGN00C writes, COUSR01C references commented) | 3 | The authenticated user's identity. Written by COSGN00C after successful login. Without it, the session has no user identity. |
| `CDEMO-USER-TYPE` | X(01) | **8** (COSGN00C, COMEN01C, COACTUPC, COACTVWC, COCRDLIC, COCRDSLC, COCRDUPC, COUSR01C) | 10 | Role-based access control flag with 88-level conditions `CDEMO-USRTYP-ADMIN` (='A') and `CDEMO-USRTYP-USER` (='U'). COMEN01C uses it to enforce "No access - Admin Only option..." COCRDLIC, COCRDSLC, COACTUPC, COACTVWC all `SET CDEMO-USRTYP-USER TO TRUE` to restrict sub-operations. |

### Category C: Business Entity Context (breaks drill-down and cross-screen data)

| Field | PIC | Programs | Total Refs | Impact |
|-------|-----|----------|-----------|--------|
| `CDEMO-CUST-ID` | 9(09) | **4** (COPAUS0C, COPAUS1C, COACTUPC, COACTVWC) | 8 | Customer ID passed from account screens to detail screens. E.g., `COACTUPC` moves it to `WS-CARD-RID-CUST-ID` to look up all cards for that customer. |
| `CDEMO-CUST-FNAME/MNAME/LNAME` | X(25) each | Programs that set them | — | Customer name fields for display. Typically read-only after initial population. |
| `CDEMO-ACCT-ID` | 9(11) | **8** (COPAUS0C, COPAUS1C, COTRTUPC, COACTUPC, COACTVWC, COCRDLIC, COCRDSLC, COCRDUPC) | 37 | Account ID is the primary entity key. COCRDLIC uses it to browse all cards for an account. COCRDSLC reads it to display card details. Without it, no cross-screen entity context exists. |
| `CDEMO-ACCT-STATUS` | X(01) | **3** (COTRTUPC, COACTUPC, COCRDUPC) | 3 | Account status flag used to gate update operations. |
| `CDEMO-CARD-NUM` | 9(16) | **7** (COPAUS0C, COTRTUPC, COACTUPC, COACTVWC, COCRDLIC, COCRDSLC, COCRDUPC) | 26 | Card number passed between list → view → update screens. COCRDSLC moves it to `CC-CARD-NUM-N` for VSAM read. |

---

## 4. Implicit (Invisible) Connections

The deep analysis found **67 implicit connections** where COCOM01Y fields have
matching PIC and byte size to fields in other copybooks. These are invisible
coupling points that would also break:

| COCOM01Y Field | Matching Copybook Field | Coupling |
|----------------|------------------------|----------|
| `CDEMO-USER-TYPE` (X(01)) | `CVACT01Y.ACCT-ACTIVE-STATUS` | Same PIC X(01) — byte-offset aliasing if COMMAREA is reinterpreted |
| `CDEMO-ACCT-STATUS` (X(01)) | `CVACT01Y.ACCT-ACTIVE-STATUS` | Semantic match — both are single-char status flags |
| `CDEMO-CUST-ID` (9(09)) | `CVACT03Y.XREF-CUST-ID` | Same PIC 9(09) — customer ID shared between COMMAREA and XREF |
| `CDEMO-ACCT-ID` (9(11)) | `CVACT01Y.ACCT-ID` | Same PIC 9(11) — account ID shared between COMMAREA and account master |
| `CDEMO-ACCT-ID` (9(11)) | `CVACT03Y.XREF-ACCT-ID` | Same PIC 9(11) — account ID shared between COMMAREA and card XREF |
| `CDEMO-FROM-PROGRAM` (X(08)) | `CIPAUDTY.PA-FRAUD-RPT-DATE` | Same 8-byte PIC — pending authorization audit trail overlaps |
| `CDEMO-FROM-TRANID` (X(04)) | `CIPAUDTY.PA-AUTH-TYPE` | Same 4-byte PIC — authorization fields overlap |
| `CDEMO-FROM-TRANID` (X(04)) | `CIPAUDTY.PA-CARD-EXPIRY-DATE` | Same 4-byte PIC |

---

## 5. COMMAREA Data Flows (XCTL graph)

The analysis traced **27 COMMAREA flows** through the application. Every flow
passes through `CARDDEMO-COMMAREA`:

```
COSGN00C ──XCTL──> COADM01C ──XCTL──> COUSR00C/01C/02C/03C
                                       COTRTLIC/COTRTUPC
COSGN00C ──XCTL──> COMEN01C ──XCTL──> COACTVWC/COACTUPC
                                       COCRDLIC ──XCTL──> COCRDSLC/COCRDUPC
                                       COTRN00C ──XCTL──> COTRN01C
                                       COTRN02C
                                       COBIL00C
                                       CORPT00C
                                       COPAUS0C ──LINK──> COPAUS1C
```

Every arrow in this graph carries the full `CARDDEMO-COMMAREA`. Removing
COCOM01Y severs every connection.

---

## 6. Blast Radius Summary

| Impact Category | Fields | Programs Affected | Severity |
|-----------------|--------|-------------------|----------|
| **Navigation** | FROM-TRANID, FROM-PROGRAM, TO-PROGRAM, TO-TRANID, PGM-CONTEXT, LAST-MAP, LAST-MAPSET | All 17 | CRITICAL — app cannot navigate |
| **Authentication** | USER-ID, USER-TYPE | 8 programs | CRITICAL — no login, no RBAC |
| **Entity Context** | CUST-ID, ACCT-ID, ACCT-STATUS, CARD-NUM | 8 programs | HIGH — no drill-down, no cross-screen data |
| **Customer Display** | CUST-FNAME, CUST-MNAME, CUST-LNAME | ~2 programs | MEDIUM — display-only fields |

**Total blast radius: 17 programs, 14 fields, 100% of CICS online functionality.**

---

## 7. Migration Path

If COCOM01Y must be retired (e.g., during modernization to microservices), the
COMMAREA maps to standard web-application session concepts:

| COBOL Field | Modern Equivalent |
|-------------|-------------------|
| `CDEMO-USER-ID` + `CDEMO-USER-TYPE` | **JWT claims** (`sub`, `role`) |
| `CDEMO-FROM-PROGRAM` / `CDEMO-TO-PROGRAM` | **URL routing / browser history** (`Referer` header, React Router) |
| `CDEMO-FROM-TRANID` / `CDEMO-TO-TRANID` | **API route prefixes** (e.g., `/api/v1/transactions/...`) |
| `CDEMO-CUST-ID` / `CDEMO-ACCT-ID` / `CDEMO-CARD-NUM` | **Request parameters** or **session store** (path params, query params, Redis) |
| `CDEMO-PGM-CONTEXT` | **HTTP method** (GET = first entry / CDEMO-PGM-ENTER, POST = re-entry / CDEMO-PGM-REENTER) |
| `CDEMO-LAST-MAP` / `CDEMO-LAST-MAPSET` | **Client-side route state** (which component/page is currently displayed) |
| `CDEMO-ACCT-STATUS` | **Domain object property** loaded per-request from database |

The migration would decompose the monolithic COMMAREA into:
1. A **stateless JWT** for identity and role
2. **URL parameters** for entity context (account, card, customer IDs)
3. **HTTP semantics** (GET/POST/PUT) replacing the PGM-CONTEXT flag
4. **Database queries** replacing the passed-by-value entity fields
