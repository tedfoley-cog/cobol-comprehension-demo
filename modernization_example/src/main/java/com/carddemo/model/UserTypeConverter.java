package com.carddemo.model;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

/**
 * JPA converter preserving the COBOL single-character codes in the database.
 *
 * COBOL:
 *   10 CDEMO-USER-TYPE  PIC X(01).
 *      88 CDEMO-USRTYP-ADMIN  VALUE 'A'.
 *      88 CDEMO-USRTYP-USER   VALUE 'U'.
 *
 * Converts between UserType enum and the single-char database values
 * 'A' and 'U', matching the original VSAM USRSEC record layout.
 */
@Converter(autoApply = true)
public class UserTypeConverter implements AttributeConverter<UserType, String> {

    @Override
    public String convertToDatabaseColumn(UserType userType) {
        if (userType == null) {
            return null;
        }
        return userType.getCode();
    }

    @Override
    public UserType convertToEntityAttribute(String code) {
        if (code == null) {
            return null;
        }
        return UserType.fromCode(code);
    }
}
