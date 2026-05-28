package com.carddemo.model;

import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * Maps: CSUSR01Y.cpy — SEC-USER-DATA (80-byte VSAM record in USRSEC file).
 *
 * COBOL layout:
 *   05 SEC-USR-ID      PIC X(08).   → userId    (primary key, offset 0)
 *   05 SEC-USR-FNAME   PIC X(20).   → firstName (offset 8)
 *   05 SEC-USR-LNAME   PIC X(20).   → lastName  (offset 28)
 *   05 SEC-USR-PWD     PIC X(08).   → password  (offset 48)
 *   05 SEC-USR-TYPE    PIC X(01).   → type      (offset 56, 'A' or 'U')
 *   05 SEC-USR-FILLER  PIC X(23).   → (padding to 80 bytes)
 */
@Entity
@Table(name = "USRSEC")
public class User {

    @Id
    @Column(name = "SEC_USR_ID", length = 8)
    private String userId;

    @Column(name = "SEC_USR_FNAME", length = 20)
    private String firstName;

    @Column(name = "SEC_USR_LNAME", length = 20)
    private String lastName;

    @Column(name = "SEC_USR_PWD", length = 8)
    private String password;

    @Convert(converter = UserTypeConverter.class)
    @Column(name = "SEC_USR_TYPE", length = 1)
    private UserType type;

    public User() {
    }

    public User(String userId, String firstName, String lastName,
                String password, UserType type) {
        this.userId = userId;
        this.firstName = firstName;
        this.lastName = lastName;
        this.password = password;
        this.type = type;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public UserType getType() {
        return type;
    }

    public void setType(UserType type) {
        this.type = type;
    }
}
