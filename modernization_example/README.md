# Modernization Example

This directory is intentionally empty in the initial state.

During the live demo, Devin converts the sign-on program (`COSGN00C.cbl`) to a
Spring Boot REST application. This is the third phase of the comprehension demo,
after business logic extraction and impact analysis.

## Why COSGN00C?

The sign-on program is the ideal conversion target because:

- **Small enough to finish live** (~260 lines of COBOL)
- **Clear business logic** (authenticate user, route by role)
- **Touches 3 data sources** (USRSEC file, COMMAREA, BMS screen)
- **Demonstrates real mapping decisions** (CICS pseudo-conversational → REST,
  COMMAREA → session, BMS → request/response DTOs)

## Expected Output Structure

After Devin runs the modernization phase, this directory will contain:

```
modernization_example/
├── src/main/java/com/carddemo/
│   ├── CardDemoApplication.java
│   ├── controller/
│   │   └── AuthController.java         # Maps COSGN00C PROCEDURE DIVISION
│   ├── model/
│   │   ├── User.java                   # Maps CSUSR01Y (SEC-USER-DATA)
│   │   └── SessionContext.java         # Maps COCOM01Y (CARDDEMO-COMMAREA)
│   ├── repository/
│   │   └── UserRepository.java         # Maps EXEC CICS READ DATASET('USRSEC')
│   ├── service/
│   │   └── AuthService.java            # Business logic from PROCESS-ENTER-KEY
│   └── dto/
│       ├── LoginRequest.java           # Maps BMS input map COSGN0AI
│       └── LoginResponse.java          # Maps BMS output map COSGN0AO
├── src/main/resources/
│   └── application.properties
├── src/test/java/com/carddemo/service/
│   └── AuthServiceTest.java
├── pom.xml
└── CONVERSION_NOTES.md                 # Field-by-field mapping with byte offsets
```

## Key Mappings

| COBOL (COSGN00C.cbl) | Spring Boot |
|---|---|
| `EXEC CICS READ DATASET('USRSEC') RIDFLD(WS-USER-ID)` | `userRepository.findById(userId)` |
| `IF SEC-USR-PWD = WS-USER-PWD` | `passwordEncoder.matches(pwd, user.getPassword())` |
| `IF CDEMO-USRTYP-ADMIN` (88-level VALUE 'A') | `if (user.getType() == UserType.ADMIN)` |
| `EXEC CICS XCTL PROGRAM('COADM01C') COMMAREA(...)` | `return LoginResponse(redirectUrl="/admin/menu")` |
| `EXEC CICS XCTL PROGRAM('COMEN01C') COMMAREA(...)` | `return LoginResponse(redirectUrl="/menu")` |
| `EVALUATE WS-RESP-CD WHEN 13` (record not found) | `Optional.empty()` → 401 Unauthorized |
| `MOVE WS-USER-ID TO CDEMO-USER-ID` | `sessionContext.setUserId(userId)` |
| `MOVE 0 TO CDEMO-PGM-CONTEXT` | `sessionContext.setProgramContext(ProgramContext.ENTER)` |
