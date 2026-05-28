package com.carddemo.service;

import com.carddemo.dto.LoginRequest;
import com.carddemo.dto.LoginResponse;
import com.carddemo.model.User;
import com.carddemo.model.UserType;
import com.carddemo.repository.UserRepository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.NoOpPasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

/**
 * Tests the four business logic paths from COSGN00C.cbl PROCEDURE DIVISION.
 *
 * Each test maps to a specific path through the EVALUATE/IF logic in
 * PROCESS-ENTER-KEY and READ-USER-SEC-FILE.
 */
@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;

    private AuthService authService;

    @BeforeEach
    void setUp() {
        @SuppressWarnings("deprecation")
        var encoder = NoOpPasswordEncoder.getInstance();
        authService = new AuthService(userRepository, encoder);
    }

    /**
     * Path 1: COSGN00C.cbl lines 118-122
     * WHEN USERIDI OF COSGN0AI = SPACES OR LOW-VALUES
     *   MOVE 'Please enter User ID ...' TO WS-MESSAGE
     */
    @Test
    @DisplayName("Empty User ID → 'Please enter User ID ...'")
    void emptyUserId() {
        LoginResponse response = authService.authenticate(
                new LoginRequest("", "password"));
        assertFalse(response.isSuccess());
        assertEquals("Please enter User ID ...", response.getMessage());
    }

    /**
     * Path 2: COSGN00C.cbl lines 123-127
     * WHEN PASSWDI OF COSGN0AI = SPACES OR LOW-VALUES
     *   MOVE 'Please enter Password ...' TO WS-MESSAGE
     */
    @Test
    @DisplayName("Empty Password → 'Please enter Password ...'")
    void emptyPassword() {
        LoginResponse response = authService.authenticate(
                new LoginRequest("USER0001", ""));
        assertFalse(response.isSuccess());
        assertEquals("Please enter Password ...", response.getMessage());
    }

    /**
     * Path 3: COSGN00C.cbl lines 247-251
     * EVALUATE WS-RESP-CD WHEN 13
     *   MOVE 'User not found. Try again ...' TO WS-MESSAGE
     */
    @Test
    @DisplayName("User not found (RESP=13) → 'User not found. Try again ...'")
    void userNotFound() {
        when(userRepository.findById("UNKNOWN1")).thenReturn(Optional.empty());

        LoginResponse response = authService.authenticate(
                new LoginRequest("unknown1", "password"));
        assertFalse(response.isSuccess());
        assertEquals("User not found. Try again ...", response.getMessage());
    }

    /**
     * Path 4a: COSGN00C.cbl lines 241-245
     * WHEN 0 → IF SEC-USR-PWD = WS-USER-PWD (false)
     *   MOVE 'Wrong Password. Try again ...' TO WS-MESSAGE
     */
    @Test
    @DisplayName("Wrong password → 'Wrong Password. Try again ...'")
    void wrongPassword() {
        User user = new User("USER0001", "JOHN", "DOE", "USER0001", UserType.USER);
        when(userRepository.findById("USER0001")).thenReturn(Optional.of(user));

        LoginResponse response = authService.authenticate(
                new LoginRequest("user0001", "WRONGPWD"));
        assertFalse(response.isSuccess());
        assertEquals("Wrong Password. Try again ...", response.getMessage());
    }

    /**
     * Path 4b: COSGN00C.cbl lines 230-234
     * IF CDEMO-USRTYP-ADMIN
     *   EXEC CICS XCTL PROGRAM('COADM01C') COMMAREA(...)
     */
    @Test
    @DisplayName("Admin login → redirect to /admin/menu")
    void adminLogin() {
        User admin = new User("ADMIN001", "ADMIN", "USER", "ADMIN001", UserType.ADMIN);
        when(userRepository.findById("ADMIN001")).thenReturn(Optional.of(admin));

        LoginResponse response = authService.authenticate(
                new LoginRequest("admin001", "admin001"));
        assertTrue(response.isSuccess());
        assertEquals(UserType.ADMIN, response.getUserType());
        assertEquals("/admin/menu", response.getRedirectUrl());
    }

    /**
     * Path 4c: COSGN00C.cbl lines 235-239
     * ELSE (not admin)
     *   EXEC CICS XCTL PROGRAM('COMEN01C') COMMAREA(...)
     */
    @Test
    @DisplayName("Regular user login → redirect to /menu")
    void regularUserLogin() {
        User user = new User("USER0001", "JOHN", "DOE", "USER0001", UserType.USER);
        when(userRepository.findById("USER0001")).thenReturn(Optional.of(user));

        LoginResponse response = authService.authenticate(
                new LoginRequest("user0001", "user0001"));
        assertTrue(response.isSuccess());
        assertEquals(UserType.USER, response.getUserType());
        assertEquals("/menu", response.getRedirectUrl());
    }
}
