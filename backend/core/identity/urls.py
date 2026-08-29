from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    OTPRequestView,
    OTPVerifyView,
    PhoneOTPRequestView,
    PhoneOTPVerifyView,
)

urlpatterns = [
    # Email OTP
    path("otp/email/request/", OTPRequestView.as_view(), name="otp-email-request"),
    path("otp/email/verify/", OTPVerifyView.as_view(), name="otp-email-verify"),

    # Phone OTP
    path("otp/phone/request/", PhoneOTPRequestView.as_view(), name="otp-phone-request"),
    path("otp/phone/verify/", PhoneOTPVerifyView.as_view(), name="otp-phone-verify"),

    # Token refresh (shared)
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
