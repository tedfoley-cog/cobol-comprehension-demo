# CardDemo Business Rules — Sign-On Through Transaction Screens

Extracted by reading the COBOL PROCEDURE DIVISIONs of the sign-on flow and
tracing logic through the menu screens to the transaction processing programs.

---

## Application Architecture

```
COSGN00C (Sign-on — TXN CC00)
  ├── [admin: SEC-USR-TYPE = 'A'] ──XCTL──> COADM01C (Admin Menu — TXN CA00)
  │                                           ├── Opt 1: COUSR00C  User List
  │                                           ├── Opt 2: COUSR01C  User Add
  │                                           ├── Opt 3: COUSR02C  User Update
  │                                           ├── Opt 4: COUSR03C  User Delete
  │                                           ├── Opt 5: COTRTLIC  Txn Type List (Db2)
  │                                           └── Opt 6: COTRTUPC  Txn Type Maint (Db2)
  └── [user: SEC-USR-TYPE ≠ 'A'] ──XCTL──> COMEN01C (Main Menu — TXN CM00)
                                              ├── Opt 1:  COACTVWC  Account View
                                              ├── Opt 2:  COACTUPC  Account Update
                                              ├── Opt 3:  COCRDLIC  Credit Card List
                                              ├── Opt 4:  COCRDSLC  Credit Card View
                                              ├── Opt 5:  COCRDUPC  Credit Card Update
                                              ├── Opt 6:  COTRN00C  Transaction List
                                              ├── Opt 7:  COTRN01C  Transaction View
                                              ├── Opt 8:  COTRN02C  Transaction Add
                                              ├── Opt 9:  CORPT00C  Transaction Reports
                                              ├── Opt 10: COBIL00C  Bill Payment
                                              └── Opt 11: COPAUS0C  Pending Auth View
```

---

## 1. COSGN00C — Sign-On Screen

**Purpose:** Authenticate users and route to the correct menu based on role.

**Entry conditions:** Transaction ID `CC00`; first invocation has `EIBCALEN = 0`.

**Data inputs:** VSAM file `USRSEC` (keyed read by user ID via `SEC-USER-DATA` from `CSUSR01Y.cpy`).

**Data outputs:** Populates `CARDDEMO-COMMAREA` (from `COCOM01Y.cpy`) with session context.

### Business Rules

| # | Rule | COBOL Source (COSGN00C.cbl) |
|---|------|---------------------------|
| 1 | **First entry → blank screen.** When `EIBCALEN = 0`, display empty sign-on form with cursor on User ID field. | Line 80: `IF EIBCALEN = 0` → `MOVE LOW-VALUES TO COSGN0AO` → `MOVE -1 TO USERIDL OF COSGN0AI` → `PERFORM SEND-SIGNON-SCREEN` |
| 2 | **PF3 = graceful exit.** Display "Thank you for using CardDemo application..." and return to CICS with no COMMAREA. | Lines 88–90: `WHEN DFHPF3` → `MOVE CCDA-MSG-THANK-YOU TO WS-MESSAGE` → `PERFORM SEND-PLAIN-TEXT` (which does `EXEC CICS RETURN` with no TRANSID) |
| 3 | **Invalid key → error.** Any key except ENTER or PF3 sets error flag and shows "Invalid key pressed." | Lines 91–94: `WHEN OTHER` → `MOVE 'Y' TO WS-ERR-FLG` → `MOVE CCDA-MSG-INVALID-KEY TO WS-MESSAGE` |
| 4 | **User ID required.** Empty User ID field triggers "Please enter User ID ..." and cursor repositions to User ID. | Lines 118–122: `WHEN USERIDI OF COSGN0AI = SPACES OR LOW-VALUES` → error message |
| 5 | **Password required.** Empty password field triggers "Please enter Password ..." and cursor repositions to Password. | Lines 123–127: `WHEN PASSWDI OF COSGN0AI = SPACES OR LOW-VALUES` → error message |
| 6 | **Input uppercased.** Both User ID and Password are converted to uppercase before processing. | Lines 132–136: `MOVE FUNCTION UPPER-CASE(USERIDI OF COSGN0AI) TO WS-USER-ID CDEMO-USER-ID`; same for password |
| 7 | **User lookup by ID.** Reads `USRSEC` VSAM file with `WS-USER-ID` as key (8-byte RIDFLD). | Lines 211–219: `EXEC CICS READ DATASET(WS-USRSEC-FILE) INTO(SEC-USER-DATA) RIDFLD(WS-USER-ID)` |
| 8 | **Password match → set session context.** When `WS-RESP-CD = 0` and `SEC-USR-PWD = WS-USER-PWD`, populate COMMAREA with: `CDEMO-FROM-TRANID`, `CDEMO-FROM-PROGRAM`, `CDEMO-USER-ID`, `CDEMO-USER-TYPE`, `CDEMO-PGM-CONTEXT = 0`. | Lines 222–228: `WHEN 0` → `IF SEC-USR-PWD = WS-USER-PWD` → MOVE fields |
| 9 | **Admin routing.** If 88-level `CDEMO-USRTYP-ADMIN` is true (value 'A'), XCTL to `COADM01C` with COMMAREA. | Lines 230–234: `IF CDEMO-USRTYP-ADMIN` → `EXEC CICS XCTL PROGRAM('COADM01C') COMMAREA(CARDDEMO-COMMAREA)` |
| 10 | **Regular user routing.** Otherwise, XCTL to `COMEN01C` with COMMAREA. | Lines 235–239: `ELSE` → `EXEC CICS XCTL PROGRAM('COMEN01C') COMMAREA(CARDDEMO-COMMAREA)` |
| 11 | **Wrong password.** When RESP=0 but password mismatch, show "Wrong Password. Try again ..." with cursor on Password. | Lines 241–245: `ELSE` → `MOVE 'Wrong Password. Try again ...' TO WS-MESSAGE` |
| 12 | **User not found.** When `WS-RESP-CD = 13` (NOTFND), show "User not found. Try again ..." with cursor on User ID. | Lines 247–251: `WHEN 13` → error message |
| 13 | **Other CICS error.** Any other RESP code shows "Unable to verify the User ..." with cursor on User ID. | Lines 252–256: `WHEN OTHER` → error message |
| 14 | **Pseudo-conversational return.** After every interaction, return to CICS with `TRANSID(CC00)` and full COMMAREA to maintain session state. | Lines 98–102: `EXEC CICS RETURN TRANSID(WS-TRANID) COMMAREA(CARDDEMO-COMMAREA)` |

### COMMAREA Fields Written

| Field | Value | Purpose |
|-------|-------|---------|
| `CDEMO-FROM-TRANID` | `'CC00'` (WS-TRANID) | Breadcrumb — where user came from |
| `CDEMO-FROM-PROGRAM` | `'COSGN00C'` (WS-PGMNAME) | Breadcrumb — program name |
| `CDEMO-USER-ID` | Uppercased user input | Session identity |
| `CDEMO-USER-TYPE` | `SEC-USR-TYPE` from USRSEC | 'A' = admin, 'U' = regular |
| `CDEMO-PGM-CONTEXT` | `0` (ZEROS) | Signals first entry to target program |

---

## 2. COMEN01C — Main Menu (Regular Users)

**Purpose:** Display 11 menu options and route to the selected program.

**Entry conditions:** XCTL from `COSGN00C` with `CDEMO-PGM-CONTEXT = 0`; transaction ID `CM00`.

**Data inputs:** COMMAREA (session state); COMEN02Y copybook (11 menu option definitions).

**Data outputs:** Updated COMMAREA breadcrumbs before XCTL to target program.

### Business Rules

| # | Rule | COBOL Source (COMEN01C.cbl) |
|---|------|---------------------------|
| 1 | **No COMMAREA → back to sign-on.** If `EIBCALEN = 0`, XCTL back to `COSGN00C`. | Lines 82–84: `IF EIBCALEN = 0` → `MOVE 'COSGN00C' TO CDEMO-FROM-PROGRAM` → `PERFORM RETURN-TO-SIGNON-SCREEN` |
| 2 | **First entry detection.** `CDEMO-PGM-CONTEXT = 0` (CDEMO-PGM-ENTER) means first time — set reenter flag and show menu. | Lines 87–90: `IF NOT CDEMO-PGM-REENTER` → `SET CDEMO-PGM-REENTER TO TRUE` → `PERFORM SEND-MENU-SCREEN` |
| 3 | **PF3 = return to sign-on.** Sets `CDEMO-TO-PROGRAM = 'COSGN00C'` and XCTLs. | Lines 96–98: `WHEN DFHPF3` → `MOVE 'COSGN00C' TO CDEMO-TO-PROGRAM` → `PERFORM RETURN-TO-SIGNON-SCREEN` |
| 4 | **Option validation.** Input trimmed, space-padded to '0', checked for numeric, range `> 0` and `<= CDEMO-MENU-OPT-COUNT` (11). | Lines 117–134: Trailing space strip, `INSPECT WS-OPTION-X REPLACING ALL ' ' BY '0'`, `IF WS-OPTION IS NOT NUMERIC OR WS-OPTION > CDEMO-MENU-OPT-COUNT OR WS-OPTION = ZEROS` → error |
| 5 | **Role-based access control.** If user type is 'U' and the menu option's `CDEMO-MENU-OPT-USRTYPE` = 'A', deny access with "No access - Admin Only option...". | Lines 136–143: `IF CDEMO-USRTYP-USER AND CDEMO-MENU-OPT-USRTYPE(WS-OPTION) = 'A'` → error |
| 6 | **Program availability check.** For `COPAUS0C` specifically, uses `EXEC CICS INQUIRE PROGRAM` to verify installation. Shows red "not installed" message if EIBRESP ≠ NORMAL. | Lines 147–168: `WHEN CDEMO-MENU-OPT-PGMNAME(WS-OPTION) = 'COPAUS0C'` → `EXEC CICS INQUIRE PROGRAM(...)` |
| 7 | **Dummy program detection.** If target program name starts with 'DUMMY', shows green "is coming soon ..." message instead of navigation. | Lines 169–176: `WHEN CDEMO-MENU-OPT-PGMNAME(WS-OPTION)(1:5) = 'DUMMY'` |
| 8 | **Navigation via XCTL.** For all valid programs, sets `CDEMO-FROM-TRANID`, `CDEMO-FROM-PROGRAM`, `CDEMO-PGM-CONTEXT = 0`, then XCTLs with COMMAREA. | Lines 177–187: `MOVE WS-TRANID TO CDEMO-FROM-TRANID` ... `EXEC CICS XCTL PROGRAM(...)` |
| 9 | **Dynamic menu construction.** Menu options built by iterating `CDEMO-MENU-OPT` array from `COMEN02Y`, writing each option number + name to screen output fields. | Lines 262–303: `BUILD-MENU-OPTIONS` paragraph |

### Menu Options (from COMEN02Y.cpy)

| Opt | Name | Program | Access |
|-----|------|---------|--------|
| 1 | Account View | COACTVWC | U |
| 2 | Account Update | COACTUPC | U |
| 3 | Credit Card List | COCRDLIC | U |
| 4 | Credit Card View | COCRDSLC | U |
| 5 | Credit Card Update | COCRDUPC | U |
| 6 | Transaction List | COTRN00C | U |
| 7 | Transaction View | COTRN01C | U |
| 8 | Transaction Add | COTRN02C | U |
| 9 | Transaction Reports | CORPT00C | U |
| 10 | Bill Payment | COBIL00C | U |
| 11 | Pending Auth View | COPAUS0C | U |

---

## 3. COADM01C — Admin Menu

**Purpose:** Display 6 admin-specific options (user management + DB2 transaction type maintenance).

**Entry conditions:** XCTL from `COSGN00C` with `CDEMO-USRTYP-ADMIN` = true; transaction ID `CA00`.

**Data inputs:** COMMAREA; `COADM02Y` copybook (6 admin option definitions).

**Data outputs:** Updated COMMAREA breadcrumbs before XCTL to target program.

### Business Rules

| # | Rule | COBOL Source (COADM01C.cbl) |
|---|------|---------------------------|
| 1 | **No COMMAREA → sign-on.** Same pattern as COMEN01C — `EIBCALEN = 0` routes back to COSGN00C. | Lines 86–88 |
| 2 | **First entry / reenter pattern.** Identical to COMEN01C — `CDEMO-PGM-CONTEXT` drives first-display vs interaction handling. | Lines 91–94 |
| 3 | **PF3 = sign-on.** `CDEMO-TO-PROGRAM = 'COSGN00C'` → XCTL. | Lines 100–102 |
| 4 | **PGMIDERR handling.** Sets `HANDLE CONDITION PGMIDERR` to catch non-installed programs. | Lines 77–79: `EXEC CICS HANDLE CONDITION PGMIDERR(PGMIDERR-ERR-PARA)` |
| 5 | **Option range check.** Options validated against `CDEMO-ADMIN-OPT-COUNT` (6). | Lines 131–138: `IF WS-OPTION IS NOT NUMERIC OR WS-OPTION > CDEMO-ADMIN-OPT-COUNT OR WS-OPTION = ZEROS` |
| 6 | **No role filter on admin menu.** Unlike COMEN01C, admin menu does NOT check `CDEMO-MENU-OPT-USRTYPE` — all options accessible. | Lines 140–158: only checks for 'DUMMY' prefix, no user-type guard |
| 7 | **Dummy program detection.** Same pattern — shows "is not installed ..." for programs starting with 'DUMMY'. | Lines 141–157 |

### Admin Menu Options (from COADM02Y.cpy)

| Opt | Name | Program |
|-----|------|---------|
| 1 | User List (Security) | COUSR00C |
| 2 | User Add (Security) | COUSR01C |
| 3 | User Update (Security) | COUSR02C |
| 4 | User Delete (Security) | COUSR03C |
| 5 | Transaction Type List/Update (Db2) | COTRTLIC |
| 6 | Transaction Type Maintenance (Db2) | COTRTUPC |

---

## 4. COTRN00C — Transaction List

**Purpose:** Browse transactions from the TRANSACT VSAM file with paginated display (10 per page).

**Entry conditions:** XCTL from menu with transaction ID `CT00`.

**Data inputs:** VSAM file `TRANSACT` (keyed by `TRAN-ID`, 350-byte records via `CVTRA05Y.cpy`).

**Data outputs:** Selected transaction ID stored in `CDEMO-CT00-TRN-SELECTED` for drill-down.

### Business Rules

| # | Rule | COBOL Source (COTRN00C.cbl) |
|---|------|---------------------------|
| 1 | **No COMMAREA → sign-on.** Same redirect-to-COSGN00C pattern. | Lines 107–109 |
| 2 | **First-entry auto-load.** On first entry (`CDEMO-PGM-CONTEXT = 0`), automatically performs `PROCESS-ENTER-KEY` to load first page of transactions. | Lines 112–116 |
| 3 | **Transaction ID filter.** If user enters a starting Transaction ID, it must be numeric; otherwise error "Tran ID must be Numeric ...". | Lines 209–218: `IF TRNIDINI OF COTRN0AI IS NUMERIC ... ELSE ... 'Tran ID must be Numeric ...'` |
| 4 | **Page forward (PF8).** Reads next 10 records via `READNEXT` CICS browse. Tracks first/last TRN-ID per page. Checks `NEXT-PAGE-YES` flag. | Lines 257–328: `PROCESS-PF8-KEY` → `PROCESS-PAGE-FORWARD` |
| 5 | **Page backward (PF7).** Reads previous 10 records via `READPREV` CICS browse. Prevents going below page 1: "You are already at the top of the page...". | Lines 234–252: `PROCESS-PF7-KEY` → checks `CDEMO-CT00-PAGE-NUM > 1` |
| 6 | **Bottom-of-data detection.** After reading 10 records, reads one more — if EOF, sets `NEXT-PAGE-NO`; otherwise `NEXT-PAGE-YES` enables PF8. | Lines 305–320 |
| 7 | **Transaction selection.** User types 'S' or 's' next to a row. Selection flag and TRN-ID stored in COMMAREA (`CDEMO-CT00-TRN-SEL-FLG`, `CDEMO-CT00-TRN-SELECTED`), then XCTL to `COTRN01C` (Transaction View). | Lines 148–195: EVALUATE scans all 10 selection fields; `WHEN 'S'` or `'s'` → XCTL to `COTRN01C` |
| 8 | **Invalid selection.** Any selection character other than 'S'/'s' shows "Invalid selection. Valid value is S". | Lines 196–201 |
| 9 | **PF3 = return to menu.** Sets `CDEMO-TO-PROGRAM = 'COMEN01C'` and XCTLs back. | Lines 122–124 |
| 10 | **Page number tracking.** `CDEMO-CT00-PAGE-NUM` incremented on forward, decremented on backward, displayed on screen. | Lines 306–307, 364 |

### COMMAREA Extension

COTRN00C extends `CARDDEMO-COMMAREA` with a program-specific section (`CDEMO-CT00-INFO`) appended after the copybook:
- `CDEMO-CT00-TRNID-FIRST` / `CDEMO-CT00-TRNID-LAST` — page boundary markers
- `CDEMO-CT00-PAGE-NUM` — current page number
- `CDEMO-CT00-NEXT-PAGE-FLG` — 'Y'/'N' for PF8 availability
- `CDEMO-CT00-TRN-SEL-FLG` / `CDEMO-CT00-TRN-SELECTED` — drill-down context

---

## 5. COTRN02C — Transaction Add (Online)

**Purpose:** Add new transactions to the TRANSACT VSAM file with full input validation.

**Entry conditions:** XCTL from menu (option 8) with transaction ID `CT02`.

**Data inputs:** VSAM files `TRANSACT`, `ACCTDAT`, `CCXREF`, `CXACAIX` (account-to-card cross-reference alternate index). Copybooks `CVTRA05Y`, `CVACT01Y`, `CVACT03Y`.

**Data outputs:** New transaction record written to `TRANSACT` file.

### Business Rules

| # | Rule | COBOL Source (COTRN02C.cbl) |
|---|------|---------------------------|
| 1 | **Key field entry — account or card.** User must provide either Account ID or Card Number. If Account ID given, system looks up card via `CXACAIX` alternate index. If Card Number given, system looks up account via `CCXREF`. Neither = error. | Lines 195–230: `VALIDATE-INPUT-KEY-FIELDS` — `WHEN ACTIDINI ... PERFORM READ-CXACAIX-FILE` / `WHEN CARDNINI ... PERFORM READ-CCXREF-FILE` / `WHEN OTHER` → "Account or Card Number must be entered..." |
| 2 | **Account ID must be numeric.** | Lines 197–203: `IF ACTIDINI ... IS NOT NUMERIC` → "Account ID must be Numeric..." |
| 3 | **Card Number must be numeric.** | Lines 211–217: `IF CARDNINI ... IS NOT NUMERIC` → "Card Number must be Numeric..." |
| 4 | **11 mandatory data fields.** All of these must be non-empty: Type CD, Category CD, Source, Description, Amount, Orig Date, Proc Date, Merchant ID, Merchant Name, Merchant City, Merchant Zip. Each has its own error message. | Lines 251–320: `VALIDATE-INPUT-DATA-FIELDS` — cascading `EVALUATE TRUE` for each field |
| 5 | **Type CD and Category CD must be numeric.** | Lines 322–337 |
| 6 | **Amount format validation.** Must match pattern `±99999999.99` — sign character in position 1, 8 numeric digits, decimal point, 2 decimal digits. | Lines 339–351: `WHEN TRNAMTI(1:1) NOT EQUAL '-' AND '+'` / `WHEN TRNAMTI(2:8) NOT NUMERIC` / `WHEN TRNAMTI(10:1) NOT = '.'` / `WHEN TRNAMTI(11:2) IS NOT NUMERIC` |
| 7 | **Date format validation.** Both origination and processing dates must match `YYYY-MM-DD` — numeric year, dash, numeric month, dash, numeric day. | Lines 353–381 |
| 8 | **Calendar date validation.** Calls utility `CSUTLDTC` to validate actual calendar dates (e.g., rejects Feb 30). Ignores msg `2513` (info-only). | Lines 389–427: `CALL 'CSUTLDTC' USING ...` → `IF CSUTLDTC-RESULT-SEV-CD = '0000'` |
| 9 | **Merchant ID must be numeric.** | Lines 430–436 |
| 10 | **Confirmation required.** User must enter 'Y'/'y' in CONFIRM field to proceed. 'N'/'n'/blank prompts "Confirm to add this transaction...". Any other value = "Invalid value. Valid values are (Y/N)...". | Lines 169–188 |
| 11 | **Transaction ID auto-generation.** Reads last record (READPREV from HIGH-VALUES), extracts numeric TRN-ID, increments by 1. | Lines 444–451: `MOVE HIGH-VALUES TO TRAN-ID` → `READPREV` → `ADD 1 TO WS-TRAN-ID-N` |
| 12 | **PF4 = clear screen.** Resets all input fields. | Lines 144–145: `WHEN DFHPF4` → `PERFORM CLEAR-CURRENT-SCREEN` |
| 13 | **PF5 = copy last transaction.** Reads last transaction and pre-fills all data fields. Still requires validation and confirmation. | Lines 471–495: `COPY-LAST-TRAN-DATA` — reads last record, copies fields to screen, then calls `PROCESS-ENTER-KEY` |
| 14 | **Back navigation.** PF3 returns to the program stored in `CDEMO-FROM-PROGRAM`; if blank, defaults to `COMEN01C`. | Lines 137–143 |

---

## 6. CBTRN02C — Daily Transaction Posting (Batch)

**Purpose:** Batch program that reads daily transaction input file, validates each record, posts valid transactions to the master file, and rejects invalid ones.

**Entry conditions:** Batch execution via JCL. Reads sequential `DALYTRAN` file.

**Data inputs:** `DALYTRAN` (sequential daily input), `XREF-FILE` (card-to-account cross-ref), `ACCOUNT-FILE` (account master), `TCATBAL-FILE` (transaction category balances).

**Data outputs:** `TRANSACT` (master transaction file), `DALYREJS` (rejected transactions with reason codes).

### Business Rules

| # | Rule | COBOL Source (CBTRN02C.cbl) |
|---|------|---------------------------|
| 1 | **Sequential processing.** Reads daily transactions one by one until EOF. Counts processed and rejected. | Lines 202–219: `PERFORM UNTIL END-OF-FILE = 'Y'` → `ADD 1 TO WS-TRANSACTION-COUNT` |
| 2 | **Card number cross-reference lookup (reason 100).** Looks up `DALYTRAN-CARD-NUM` in XREF file. `INVALID KEY` → reason code 100 "INVALID CARD NUMBER FOUND". | Lines 380–392: `1500-A-LOOKUP-XREF` — `READ XREF-FILE ... INVALID KEY MOVE 100 TO WS-VALIDATION-FAIL-REASON` |
| 3 | **Account lookup (reason 101).** If card found, looks up `XREF-ACCT-ID` in ACCOUNT file. `INVALID KEY` → reason code 101 "ACCOUNT RECORD NOT FOUND". | Lines 393–399: `1500-B-LOOKUP-ACCT` |
| 4 | **Credit limit check (reason 102).** Computes projected balance: `ACCT-CURR-CYC-CREDIT - ACCT-CURR-CYC-DEBIT + DALYTRAN-AMT`. If this exceeds `ACCT-CREDIT-LIMIT`, rejects with reason 102 "OVERLIMIT TRANSACTION". | Lines 403–413: `COMPUTE WS-TEMP-BAL = ACCT-CURR-CYC-CREDIT - ACCT-CURR-CYC-DEBIT + DALYTRAN-AMT` → `IF ACCT-CREDIT-LIMIT >= WS-TEMP-BAL` |
| 5 | **Account expiration check (reason 103).** If `ACCT-EXPIRAION-DATE < DALYTRAN-ORIG-TS(1:10)`, rejects with reason 103 "TRANSACTION RECEIVED AFTER ACCT EXPIRATION". | Lines 414–420 |
| 6 | **Valid transaction posting.** Copies all fields from daily record to TRAN-RECORD, generates DB2-format timestamp for `TRAN-PROC-TS`, then updates category balances, account record, and writes transaction. | Lines 424–443: `2000-POST-TRANSACTION` → `PERFORM 2700-UPDATE-TCATBAL` → `PERFORM 2800-UPDATE-ACCOUNT-REC` → `PERFORM 2900-WRITE-TRANSACTION-FILE` |
| 7 | **Category balance tracking.** Updates `TCATBAL` file keyed by account + type + category. Creates new records if key not found (`WS-CREATE-TRANCAT-REC = 'Y'`). | Lines 467–479 |
| 8 | **Reject file with trailer.** Rejected records written with the original 350-byte transaction data plus an 80-byte validation trailer containing reason code (4 digits) and description (76 chars). | Lines 176–182, 446–465: `REJECT-RECORD` structure |
| 9 | **Return code signaling.** Sets `RETURN-CODE = 4` if any rejects occurred, enabling JCL condition-code processing. | Lines 229–231: `IF WS-REJECT-COUNT > 0 MOVE 4 TO RETURN-CODE` |
| 10 | **Abend on file errors.** Any file open/read/write failure causes program ABEND via `CEE3ABD` (LE ABEND). | Pattern across all `99nn-` paragraphs |

---

## Key Copybooks Referenced

| Copybook | Purpose | Record Length |
|----------|---------|--------------|
| **COCOM01Y** | CARDDEMO-COMMAREA — session state passed between all CICS programs | ~157 bytes |
| **CSUSR01Y** | SEC-USER-DATA — user security record (ID, name, password, type) | 80 bytes |
| **COMEN02Y** | Menu option table — 11 entries with program name + access type | 46 bytes × 12 |
| **COADM02Y** | Admin menu option table — 6 entries | 45 bytes × 9 |
| **CVTRA05Y** | TRAN-RECORD — transaction data structure | 350 bytes |
| **CVACT01Y** | ACCOUNT-RECORD — account master data | 300 bytes |
| **CVACT03Y** | CARD-XREF-RECORD — card-to-account cross-reference | 50 bytes |
| **COTTL01Y** | Screen titles and thank-you message | 120 bytes |
| **CSMSG01Y** | Common messages (invalid key, thank you) | 100 bytes |
| **CSDAT01Y** | Date/time formatting working storage | — |
