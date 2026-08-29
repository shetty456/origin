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


# Email OTP
class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)


# Phone OTP
class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = PhoneNumberField()


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone = PhoneNumberField()
    otp = serializers.CharField(min_length=6, max_length=6)


# Identity linking (authenticated)
class LinkEmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LinkEmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)


class LinkPhoneRequestSerializer(serializers.Serializer):
    phone = PhoneNumberField()


class LinkPhoneVerifySerializer(serializers.Serializer):
    phone = PhoneNumberField()
    otp = serializers.CharField(min_length=6, max_length=6)
