# -*- coding:utf-8 -*-

from odoo import models
from phonenumbers import parse as parse_phone_number, format_number, is_valid_number
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException


def get_valid_phone_number(phone_number):
    error_message = _('Invalid phone (mobile) number - %s') % phone_number
    try:
        parsed_number = parse_phone_number(phone_number)
        format_type = PhoneNumberFormat.INTERNATIONAL  # keep region code
    except NumberParseException as err:
        if err.error_type == NumberParseException.INVALID_COUNTRY_CODE:
            # the phone number without prefix region code -> default VieNam's phone number
            parsed_number = parse_phone_number(phone_number, 'VN')
            format_type = PhoneNumberFormat.NATIONAL
        else:
            raise ValidationError(error_message)
    if not is_valid_number(parsed_number):
        raise ValidationError(error_message)
    return format_number(parsed_number, format_type)


def is_valid_phone_number(phone_number):
    try:
        parsed_number = parse_phone_number(phone_number)
    except NumberParseException as err:
        if err.error_type == NumberParseException.INVALID_COUNTRY_CODE:
            # the phone number without prefix region code -> default VieNam's phone number
            parsed_number = parse_phone_number(phone_number, 'VN')
        else:
            return False
    if not is_valid_number(parsed_number):
        return False
    return True


class ResUtility(models.AbstractModel):
    _name = 'res.utility'
    _description = 'Utility'
