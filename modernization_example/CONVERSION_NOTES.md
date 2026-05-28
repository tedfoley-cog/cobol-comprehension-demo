# COSGN00C → Spring Boot Conversion Notes

## Source

- **COBOL program**: `carddemo-source/app/cbl/COSGN00C.cbl` (260 lines)
- **Copybooks used**: `COCOM01Y.cpy`, `CSUSR01Y.cpy`, `COTTL01Y.cpy`, `CSDAT01Y.cpy`, `CSMSG01Y.cpy`
- **BMS maps**: `COSGN00` (COSGN0AI input, COSGN0AO output)
- **VSAM file**: `USRSEC` (keyed by 8-byte user ID)

---

## Field-by-Field Mapping

### SEC-USER-DATA (CSUSR01Y.cpy → User.java)

| COBOL Field | PIC | Offset | Bytes | Java Field | Type |
|-------------|-----|--------|-------|------------|------|
| `SEC-USR-ID` | X(08) | 0 | 8 | `User.userId` | `String` |
| `SEC-USR-FNAME` | X(20) | 8 | 20 | `User.firstName` | `String` |
| `SEC-USR-LNAME` | X(20) | 28 | 20 | `User.lastName` | `String` |
| `SEC-USR-PWD` | X(08) | 48 | 8 | `User.password` | `String` |
| `SEC-USR-TYPE` | X(01) | 56 | 1 | `User.type` | `UserType` enum |
| `SEC-USR-FILLER` | X(23) | 57 | 23 | *(not mapped — padding)* | — |

### CARDDEMO-COMMAREA (COCOM01Y.cpy → SessionContext.java)

Only fields written by COSGN00C are mapped:

| COBOL Field | PIC | Offset | Bytes | Java Field | Type |
|-------------|-----|--------|-------|------------|------|
| `CDEMO-FROM-TRANID` | X(04) | 0 | 4 | `SessionContext.fromTransactionId` | `String` |
| `CDEMO-FROM-PROGRAM` | X(08) | 4 | 8 | `SessionContext.fromProgram` | `String` |
| `CDEMO-USER-ID` | X(08) | 24 | 8 | `SessionContext.userId` | `String` |
| `CDEMO-USER-TYPE` | X(01) | 32 | 1 | `SessionContext.userType` | `UserType` |
| `CDEMO-PGM-CONTEXT` | 9(01) | 33 | 1 | `SessionContext.programContext` | `int` |

### BMS Screen (COSGN0AI/COSGN0AO → LoginRequest.java / LoginResponse.java)

| COBOL Field | Direction | Java Field |
|-------------|-----------|------------|
| `USERIDI OF COSGN0AI` | Input | `LoginRequest.userId` |
| `PASSWDI OF COSGN0AI` | Input | `LoginRequest.password` |
| `ERRMSGO OF COSGN0AO` | Output | `LoginResponse.message` |
| *(XCTL target)* | Output | `LoginResponse.redirectUrl` |
| *(CDEMO-USER-TYPE)* | Output | `LoginResponse.userType` |

---

## Paragraph-by-Paragraph Mapping

| COBOL Paragraph | Lines | Java Method | Notes |
|-----------------|-------|-------------|-------|
| `MAIN-PARA` | 73-102 | `AuthController.login()` / `.loginForm()` | EIBCALEN check → GET vs POST; EVALUATE EIBAID → HTTP method routing |
| `PROCESS-ENTER-KEY` | 108-140 | `AuthService.authenticate()` | Input validation + delegation to READ-USER-SEC-FILE |
| `SEND-SIGNON-SCREEN` | 145-157 | `AuthController.loginForm()` | EXEC CICS SEND MAP → return login page |
| `SEND-PLAIN-TEXT` | 162-172 | `AuthController.logout()` | PF3 thank-you message + EXEC CICS RETURN (no TRANSID) |
| `POPULATE-HEADER-INFO` | 177-204 | *(removed)* | Date/time/APPLID display — handled by frontend in modern app |
| `READ-USER-SEC-FILE` | 209-257 | `AuthService.authenticate()` (VSAM read + password check + routing) | EXEC CICS READ → `userRepository.findById()`; EVALUATE WS-RESP-CD → if/else chain |

---

## What Was Preserved vs. What Changed

### Preserved (functionally equivalent)

| Aspect | COBOL | Java |
|--------|-------|------|
| **Password comparison** | `IF SEC-USR-PWD = WS-USER-PWD` (plaintext) | `passwordEncoder.matches()` with NoOpPasswordEncoder |
| **Input uppercasing** | `FUNCTION UPPER-CASE(USERIDI)` | `request.getUserId().toUpperCase()` |
| **Error messages** | Exact text from WS-MESSAGE MOVEs | Same strings in `LoginResponse.failure()` |
| **Admin routing** | `IF CDEMO-USRTYP-ADMIN` → XCTL to COADM01C | `if (user.getType() == UserType.ADMIN)` → `/admin/menu` |
| **Regular routing** | ELSE → XCTL to COMEN01C | else → `/menu` |
| **4 error paths** | RESP=13, wrong password, empty ID, empty password | Mapped 1:1 to return values |
| **88-level conditions** | `CDEMO-USRTYP-ADMIN VALUE 'A'` / `CDEMO-USRTYP-USER VALUE 'U'` | `UserType.ADMIN` / `UserType.USER` enum |

### Changed (architectural differences)

| Aspect | COBOL | Java | Why |
|--------|-------|------|-----|
| **Conversation model** | Pseudo-conversational (RETURN TRANSID + COMMAREA) | Stateless REST (each request is complete) | CICS pseudo-conversational pattern has no REST equivalent — each HTTP request is self-contained |
| **Session state** | COMMAREA passed by value on every XCTL | JWT or server-side session (not implemented in demo) | COMMAREA is a CICS-specific mechanism; REST uses tokens or cookies |
| **Screen rendering** | BMS maps (COSGN0A) sent via EXEC CICS SEND MAP | JSON responses — UI is a separate concern | Modern separation of frontend/backend |
| **Navigation** | EXEC CICS XCTL PROGRAM(...) | `redirectUrl` in response body | Client-side routing replaces server-side program transfer |
| **PF key handling** | EVALUATE EIBAID (DFHENTER, DFHPF3, OTHER) | Different HTTP endpoints (POST /login, POST /logout, GET /login) | Terminal function keys map to HTTP methods/endpoints |
| **Header info** | POPULATE-HEADER-INFO (date, time, APPLID, SYSID) | Removed | Frontend handles display chrome |
| **Error cursor positioning** | `MOVE -1 TO USERIDL` (set cursor to field) | Not applicable | No terminal cursor in REST API |
| **VSAM file I/O** | `EXEC CICS READ DATASET('USRSEC')` with RESP codes | Spring Data JPA `findById()` returning `Optional` | VSAM keyed read maps directly to primary-key lookup |

### COMMAREA Fields Written by COSGN00C

| COMMAREA Field | Value Written | Modern Equivalent |
|----------------|---------------|-------------------|
| `CDEMO-FROM-TRANID` | `'CC00'` (WS-TRANID) | JWT claim: `iss` or session attribute |
| `CDEMO-FROM-PROGRAM` | `'COSGN00C'` (WS-PGMNAME) | HTTP `Referer` header or session attribute |
| `CDEMO-USER-ID` | Uppercased user input | JWT claim: `sub` |
| `CDEMO-USER-TYPE` | `SEC-USR-TYPE` from USRSEC | JWT claim: `role` |
| `CDEMO-PGM-CONTEXT` | `0` (ZEROS = first entry) | HTTP method: GET = first entry, POST = re-entry |
