package com.carddemo.controller;

import com.carddemo.dto.LoginRequest;
import com.carddemo.dto.LoginResponse;
import com.carddemo.service.AuthService;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Maps: COSGN00C.cbl — the entire sign-on program PROCEDURE DIVISION.
 *
 * COBOL entry point: Transaction ID CC00 triggers COSGN00C in the CICS region.
 * REST equivalent:   POST /api/auth/login handles authentication requests.
 *
 * The COBOL program uses pseudo-conversational CICS:
 *   1. First entry (EIBCALEN=0): SEND blank sign-on screen → GET /api/auth/login
 *   2. ENTER key: RECEIVE map, validate, authenticate  → POST /api/auth/login
 *   3. PF3 key: display "Thank you" and end session    → DELETE /api/auth/logout
 *
 * EVALUATE EIBAID (line 85) maps to HTTP methods:
 *   DFHENTER → POST /api/auth/login  (PROCESS-ENTER-KEY)
 *   DFHPF3   → POST /api/auth/logout (SEND-PLAIN-TEXT with thank-you)
 *   OTHER    → 400 Bad Request       (CCDA-MSG-INVALID-KEY)
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * Maps: EIBCALEN = 0 → SEND-SIGNON-SCREEN (COSGN00C.cbl lines 80-83).
     *
     * In COBOL, first entry displays a blank sign-on screen.
     * In REST, GET returns a simple status indicating the login endpoint is ready.
     */
    @GetMapping("/login")
    public ResponseEntity<LoginResponse> loginForm() {
        return ResponseEntity.ok(
                LoginResponse.failure("Please sign on to CardDemo application."));
    }

    /**
     * Maps: DFHENTER → PROCESS-ENTER-KEY (COSGN00C.cbl lines 86-87, 108-140).
     *
     * Receives user credentials, validates, authenticates against USRSEC,
     * and returns the appropriate redirect URL based on user type.
     *
     * The four business paths from COSGN00C:
     *   - Empty user ID:    returns 401 with "Please enter User ID ..."
     *   - Empty password:   returns 401 with "Please enter Password ..."
     *   - User not found:   returns 401 with "User not found. Try again ..."
     *   - Wrong password:   returns 401 with "Wrong Password. Try again ..."
     *   - Admin success:    returns 200 with redirectUrl="/admin/menu"
     *   - Regular success:  returns 200 with redirectUrl="/menu"
     */
    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@RequestBody LoginRequest request) {
        LoginResponse response = authService.authenticate(request);
        if (response.isSuccess()) {
            return ResponseEntity.ok(response);
        }
        return ResponseEntity.status(401).body(response);
    }

    /**
     * Maps: DFHPF3 → SEND-PLAIN-TEXT (COSGN00C.cbl lines 88-90, 162-172).
     *
     * COBOL: MOVE CCDA-MSG-THANK-YOU TO WS-MESSAGE → EXEC CICS RETURN (no TRANSID).
     * REST:  POST /api/auth/logout → invalidate session, return thank-you message.
     */
    @PostMapping("/logout")
    public ResponseEntity<LoginResponse> logout() {
        return ResponseEntity.ok(
                LoginResponse.failure(
                        "Thank you for using CardDemo application..."));
    }
}
