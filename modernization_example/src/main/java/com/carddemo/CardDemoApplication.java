package com.carddemo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Entry point for the modernized CardDemo authentication service.
 *
 * Replaces: CICS transaction CC00 (COSGN00C program startup).
 * In the original COBOL, the CICS region loads COSGN00C when a terminal
 * sends transaction CC00. Here, Spring Boot serves the same role as the
 * CICS region — the application container.
 */
@SpringBootApplication
public class CardDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(CardDemoApplication.class, args);
    }
}
