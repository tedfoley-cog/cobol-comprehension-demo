package com.carddemo.dto;

import com.carddemo.model.UserType;

/**
 * Maps: BMS output map COSGN0AO + COMMAREA fields written on login.
 *
 * In the original COBOL, a successful login results in XCTL to either
 * COADM01C or COMEN01C with the COMMAREA populated. In REST, we return
 * a response with the redirect URL and session context instead.
 *
 * COBOL → REST mapping:
 *   EXEC CICS XCTL PROGRAM('COADM01C')  →  redirectUrl = "/admin/menu"
 *   EXEC CICS XCTL PROGRAM('COMEN01C')  →  redirectUrl = "/menu"
 *   MOVE WS-USER-ID TO CDEMO-USER-ID    →  userId field
 *   MOVE SEC-USR-TYPE TO CDEMO-USER-TYPE →  userType field
 *   ERRMSGO OF COSGN0AO                 →  message field (error text)
 */
public class LoginResponse {

    private boolean success;
    private String userId;
    private UserType userType;
    private String redirectUrl;
    private String message;

    public LoginResponse() {
    }

    public static LoginResponse success(String userId, UserType userType,
                                        String redirectUrl) {
        LoginResponse response = new LoginResponse();
        response.success = true;
        response.userId = userId;
        response.userType = userType;
        response.redirectUrl = redirectUrl;
        return response;
    }

    public static LoginResponse failure(String message) {
        LoginResponse response = new LoginResponse();
        response.success = false;
        response.message = message;
        return response;
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
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

    public String getRedirectUrl() {
        return redirectUrl;
    }

    public void setRedirectUrl(String redirectUrl) {
        this.redirectUrl = redirectUrl;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}
