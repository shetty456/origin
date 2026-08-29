import phonenumbers
from rest_framework import serializers


class PhoneNumberField(serializers.CharField):
    """Validates and normalizes a phone number to E.164 format."""

    def to_internal_value(self, value):
        value = super().to_internal_value(value)
        try:
            parsed = phonenumbers.parse(value)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(
                "Invalid phone number. Include country code, e.g. +919876543210"
            )
        if not phonenumbers.is_valid_number(parsed):
            raise serializers.ValidationError("Invalid phone number.")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class OTPField(serializers.CharField):
    """Exactly 6 digits — rejects non-numeric values at the serializer layer."""

    def __init__(self, **kwargs):
        kwargs.setdefault("min_length", 4)
        kwargs.setdefault("max_length", 4)
        super().__init__(**kwargs)

    def to_internal_value(self, value):
        value = super().to_internal_value(value)
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be a 4-digit number.")
        return value


# ---------------------------------------------------------------------------
# Request serializers
# ---------------------------------------------------------------------------

class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = OTPField()


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = PhoneNumberField()


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone = PhoneNumberField()
    otp = OTPField()


class LinkEmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LinkEmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = OTPField()


class LinkPhoneRequestSerializer(serializers.Serializer):
    phone = PhoneNumberField()


class LinkPhoneVerifySerializer(serializers.Serializer):
    phone = PhoneNumberField()
    otp = OTPField()


# ---------------------------------------------------------------------------
# Response serializers (used in extend_schema for Swagger documentation)
# ---------------------------------------------------------------------------

class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
