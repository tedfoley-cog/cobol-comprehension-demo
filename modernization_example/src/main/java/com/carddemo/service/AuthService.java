package com.carddemo.service;

import com.carddemo.dto.LoginRequest;
import com.carddemo.dto.LoginResponse;
import com.carddemo.model.SessionContext;
import com.carddemo.model.User;
import com.carddemo.model.UserType;
import com.carddemo.repository.UserRepository;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 * Maps: COSGN00C.cbl — PROCESS-ENTER-KEY + READ-USER-SEC-FILE paragraphs.
 *
 * This service contains the four business logic paths extracted from the
 * COBOL PROCEDURE DIVISION (lines 108-257):
 *
 *   Path 1: User ID is blank         → "Please enter User ID ..."
 *   Path 2: Password is blank        → "Please enter Password ..."
 *   Path 3: User not found (RESP=13) → "User not found. Try again ..."
 *   Path 4a: Password mismatch       → "Wrong Password. Try again ..."
 *   Path 4b: Admin login success     → redirect to /admin/menu
 *   Path 4c: Regular login success   → redirect to /menu
 *
 * The CICS pseudo-conversational pattern (RETURN TRANSID + COMMAREA) is
 * replaced by stateless REST. Each HTTP request is self-contained —
 * there is no EIBCALEN check because REST has no "first entry" concept.
 */
@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public AuthService(UserRepository userRepository,
                       PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    /**
     * Authenticate a user and return the appropriate redirect.
     *
     * Maps the COBOL logic from PROCESS-ENTER-KEY (line 108) through
     * READ-USER-SEC-FILE (line 209) in COSGN00C.cbl.
     */
    public LoginResponse authenticate(LoginRequest request) {
        // --- Validation (COSGN00C.cbl lines 117-130) ---
        // EVALUATE TRUE
        //   WHEN USERIDI OF COSGN0AI = SPACES OR LOW-VALUES
        //     MOVE 'Please enter User ID ...' TO WS-MESSAGE
        if (request.getUserId() == null || request.getUserId().isBlank()) {
            return LoginResponse.failure("Please enter User ID ...");
        }

        //   WHEN PASSWDI OF COSGN0AI = SPACES OR LOW-VALUES
        //     MOVE 'Please enter Password ...' TO WS-MESSAGE
        if (request.getPassword() == null || request.getPassword().isBlank()) {
            return LoginResponse.failure("Please enter Password ...");
        }

        // --- Uppercase conversion (COSGN00C.cbl lines 132-136) ---
        // MOVE FUNCTION UPPER-CASE(USERIDI OF COSGN0AI) TO WS-USER-ID
        // MOVE FUNCTION UPPER-CASE(PASSWDI OF COSGN0AI) TO WS-USER-PWD
        String userId = request.getUserId().toUpperCase();
        String password = request.getPassword().toUpperCase();

        // --- VSAM read (COSGN00C.cbl lines 211-219) ---
        // EXEC CICS READ DATASET(WS-USRSEC-FILE) INTO(SEC-USER-DATA)
        //   RIDFLD(WS-USER-ID) RESP(WS-RESP-CD)
        Optional<User> userOpt = userRepository.findById(userId);

        // --- EVALUATE WS-RESP-CD (line 221) ---
        if (userOpt.isEmpty()) {
            // WHEN 13  → user not found
            //   MOVE 'User not found. Try again ...' TO WS-MESSAGE
            return LoginResponse.failure("User not found. Try again ...");
        }

        User user = userOpt.get();

        // WHEN 0  → record found, check password
        // IF SEC-USR-PWD = WS-USER-PWD (line 223)
        if (!passwordEncoder.matches(password, user.getPassword())) {
            // MOVE 'Wrong Password. Try again ...' TO WS-MESSAGE
            return LoginResponse.failure("Wrong Password. Try again ...");
        }

        // --- Successful login: populate session context ---
        // This replaces the COMMAREA writes at lines 224-228:
        //   MOVE WS-TRANID   TO CDEMO-FROM-TRANID
        //   MOVE WS-PGMNAME  TO CDEMO-FROM-PROGRAM
        //   MOVE WS-USER-ID  TO CDEMO-USER-ID
        //   MOVE SEC-USR-TYPE TO CDEMO-USER-TYPE
        //   MOVE ZEROS        TO CDEMO-PGM-CONTEXT

        // --- Route by role (COSGN00C.cbl lines 230-239) ---
        // IF CDEMO-USRTYP-ADMIN
        //   EXEC CICS XCTL PROGRAM('COADM01C') COMMAREA(...)
        // ELSE
        //   EXEC CICS XCTL PROGRAM('COMEN01C') COMMAREA(...)
        if (user.getType() == UserType.ADMIN) {
            return LoginResponse.success(userId, UserType.ADMIN, "/admin/menu");
        }
        return LoginResponse.success(userId, UserType.USER, "/menu");
    }

    /**
     * Build session context from a successful login.
     *
     * Maps the COMMAREA population in COSGN00C.cbl lines 224-228.
     * In a full implementation this would create a JWT or server-side session.
     */
    public SessionContext buildSessionContext(User user) {
        SessionContext ctx = new SessionContext();
        // MOVE WS-TRANID TO CDEMO-FROM-TRANID  (WS-TRANID = 'CC00')
        ctx.setFromTransactionId("CC00");
        // MOVE WS-PGMNAME TO CDEMO-FROM-PROGRAM  (WS-PGMNAME = 'COSGN00C')
        ctx.setFromProgram("COSGN00C");
        // MOVE WS-USER-ID TO CDEMO-USER-ID
        ctx.setUserId(user.getUserId());
        // MOVE SEC-USR-TYPE TO CDEMO-USER-TYPE
        ctx.setUserType(user.getType());
        // MOVE ZEROS TO CDEMO-PGM-CONTEXT  (0 = first entry)
        ctx.setProgramContext(0);
        return ctx;
    }
}
