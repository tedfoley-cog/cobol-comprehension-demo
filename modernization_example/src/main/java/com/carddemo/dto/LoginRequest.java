package com.carddemo.dto;

/**
 * Maps: BMS input map COSGN0AI — the sign-on screen input fields.
 *
 * COBOL fields:
 *   USERIDI OF COSGN0AI  — user ID typed by the terminal operator
 *   PASSWDI OF COSGN0AI  — password typed by the terminal operator
 *
 * In the original COBOL, these are received via:
 *   EXEC CICS RECEIVE MAP('COSGN0A') MAPSET('COSGN00')
 *
 * In REST, this is the JSON request body for POST /api/auth/login.
 */
public class LoginRequest {

    private String userId;
    private String password;

    public LoginRequest() {
    }

    public LoginRequest(String userId, String password) {
        this.userId = userId;
        this.password = password;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}
