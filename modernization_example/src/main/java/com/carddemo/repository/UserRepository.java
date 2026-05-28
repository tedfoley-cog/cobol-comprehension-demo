package com.carddemo.repository;

import com.carddemo.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Maps: EXEC CICS READ DATASET('USRSEC') INTO(SEC-USER-DATA)
 *       RIDFLD(WS-USER-ID) KEYLENGTH(LENGTH OF WS-USER-ID)
 *       RESP(WS-RESP-CD) RESP2(WS-REAS-CD)
 *
 * COBOL paragraph: READ-USER-SEC-FILE (COSGN00C.cbl lines 209-257)
 *
 * The original code performs a keyed VSAM read using the 8-byte user ID
 * as the record key. RESP code 0 = found, 13 = not found, other = error.
 *
 * In Spring Data JPA, findById() returns Optional.empty() for RESP=13,
 * and the entity for RESP=0. DataAccessException covers other RESP codes.
 */
@Repository
public interface UserRepository extends JpaRepository<User, String> {
}
