package com.carddemo.model;

/**
 * Maps: COCOM01Y.cpy — CARDDEMO-COMMAREA (session state).
 *
 * In the original COBOL, this 160-byte structure is passed between every
 * CICS program via EXEC CICS XCTL COMMAREA(...). In the modernized app,
 * this becomes the JWT payload or server-side session — the fields that
 * COSGN00C writes on successful login.
 *
 * COBOL layout (relevant fields written by COSGN00C):
 *   10 CDEMO-FROM-TRANID    PIC X(04)  → fromTransactionId
 *   10 CDEMO-FROM-PROGRAM   PIC X(08)  → fromProgram
 *   10 CDEMO-USER-ID        PIC X(08)  → userId
 *   10 CDEMO-USER-TYPE      PIC X(01)  → userType
 *   10 CDEMO-PGM-CONTEXT    PIC 9(01)  → programContext (0=enter, 1=reenter)
 */
public class SessionContext {

    private String fromTransactionId;
    private String fromProgram;
    private String userId;
    private UserType userType;
    private int programContext;

    public SessionContext() {
    }

    public String getFromTransactionId() {
        return fromTransactionId;
    }

    public void setFromTransactionId(String fromTransactionId) {
        this.fromTransactionId = fromTransactionId;
    }

    public String getFromProgram() {
        return fromProgram;
    }

    public void setFromProgram(String fromProgram) {
        this.fromProgram = fromProgram;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public UserType getUserType() {
        return userType;
    }

    public void setUserType(UserType userType) {
        this.userType = userType;
    }

    public int getProgramContext() {
        return programContext;
    }

    public void setProgramContext(int programContext) {
        this.programContext = programContext;
    }
}
