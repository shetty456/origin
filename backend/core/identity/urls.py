from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    OTPRequestView,
    OTPVerifyView,
    PhoneOTPRequestView,
    PhoneOTPVerifyView,
    LinkEmailRequestView,
    LinkEmailVerifyView,
    LinkPhoneRequestView,
    LinkPhoneVerifyView,
)

TaggedTokenRefreshView = extend_schema_view(
    post=extend_schema(tags=["Token"])
)(TokenRefreshView)

urlpatterns = [
    # --- Signup / Login (public) ---
    path("otp/email/request/", OTPRequestView.as_view(), name="otp-email-request"),
    path("otp/email/verify/", OTPVerifyView.as_view(), name="otp-email-verify"),
    path("otp/phone/request/", PhoneOTPRequestView.as_view(), name="otp-phone-request"),
    path("otp/phone/verify/", PhoneOTPVerifyView.as_view(), name="otp-phone-verify"),

    # --- Token management (public) ---
    path("token/refresh/", TaggedTokenRefreshView.as_view(), name="token-refresh"),

    # --- Identity linking (authenticated) ---
    path("identity/link/email/request/", LinkEmailRequestView.as_view(), name="link-email-request"),
    path("identity/link/email/verify/", LinkEmailVerifyView.as_view(), name="link-email-verify"),
    path("identity/link/phone/request/", LinkPhoneRequestView.as_view(), name="link-phone-request"),
    path("identity/link/phone/verify/", LinkPhoneVerifyView.as_view(), name="link-phone-verify"),
]
