package com.carddemo;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.crypto.password.NoOpPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Security configuration for the modernized CardDemo auth service.
 *
 * The original COBOL program compares passwords in plaintext:
 *   IF SEC-USR-PWD = WS-USER-PWD  (COSGN00C.cbl line 223)
 *
 * We use NoOpPasswordEncoder to preserve this behavior for the demo.
 * In production, this would be replaced with BCryptPasswordEncoder and
 * the USRSEC records would store hashed passwords.
 *
 * CSRF is disabled because this is a stateless REST API — the COBOL
 * original had no CSRF concept (CICS terminal sessions are inherently
 * single-user).
 */
@Configuration
@EnableWebSecurity
@SuppressWarnings("deprecation")
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/h2-console/**").permitAll()
                .anyRequest().authenticated()
            )
            .headers(headers -> headers
                .frameOptions(frame -> frame.sameOrigin())
            );
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return NoOpPasswordEncoder.getInstance();
    }
}
