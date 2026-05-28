package com.carddemo.model;

/**
 * Maps: COCOM01Y.cpy — CDEMO-USER-TYPE 88-level conditions.
 *
 * COBOL:
 *   10 CDEMO-USER-TYPE  PIC X(01).
 *      88 CDEMO-USRTYP-ADMIN  VALUE 'A'.
 *      88 CDEMO-USRTYP-USER   VALUE 'U'.
 */
public enum UserType {

    /** 88 CDEMO-USRTYP-ADMIN VALUE 'A'. */
    ADMIN("A"),

    /** 88 CDEMO-USRTYP-USER VALUE 'U'. */
    USER("U");

    private final String code;

    UserType(String code) {
        this.code = code;
    }

    public String getCode() {
        return code;
    }

    public static UserType fromCode(String code) {
        for (UserType type : values()) {
            if (type.code.equals(code)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown user type code: " + code);
    }
}
