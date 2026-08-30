"""
Concurrency stress tests for the critical atomic guards in the OTP flow.

Each test uses threading.Barrier to fire N threads simultaneously, then
asserts that DB-level atomicity held: only the expected number of
operations succeeded.

These tests require transaction=True so that threads use real DB
transactions and can see each other's committed writes.
"""
import threading
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection

from core.identity.models import Identity, OTPRequest
from core.identity.views import _verify_otp

User = get_user_model()

WORKERS = 20


def _close_thread_db():
    """Close the DB connection for the current thread after it's done."""
    connection.close()


def _run_concurrent(fn, n=WORKERS):
    """Fire n threads through fn simultaneously via a Barrier, collect results."""
    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker():
        barrier.wait()
        try:
            result = fn()
        except Exception as exc:
            result = exc
        finally:
            _close_thread_db()
        with lock:
            results.append(result)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


# ---------------------------------------------------------------------------
# 1. OTP replay guard — concurrent correct verifies
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_concurrent_otp_verify_only_one_succeeds():
    """
    N threads simultaneously submit the correct OTP.
    The atomic verified_at guard must ensure exactly 1 succeeds.
    """
    user = User.objects.create_user()
    identity = Identity.objects.create(
        user=user, provider=Identity.PROVIDER_EMAIL, identifier="stress-replay@example.com"
    )
    otp_request, plaintext_otp = OTPRequest.objects.create_for(identity)

    def attempt():
        req, err = _verify_otp(identity, plaintext_otp)
        return req is not None  # True = succeeded, False = rejected

    results = _run_concurrent(attempt, n=WORKERS)

    successes = results.count(True)
    assert successes == 1, f"Expected 1 success, got {successes} out of {WORKERS} concurrent verifies"


# ---------------------------------------------------------------------------
# 2. Attempt counter atomicity — concurrent wrong OTPs
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_concurrent_wrong_otp_exhausts_otp_and_blocks_correct_guess():
    """
    N threads simultaneously submit wrong OTPs.

    Design: once attempts reaches MAX_ATTEMPTS, is_usable returns False and
    further threads are rejected without incrementing — this is correct. The
    security property we verify is:
      (a) the attempt counter is never UNDER-counted (no lost F() updates), and
      (b) the OTP is exhausted after concurrent wrong guesses, so the correct
          OTP is also rejected (no brute-force bypass).
    """
    user = User.objects.create_user()
    identity = Identity.objects.create(
        user=user, provider=Identity.PROVIDER_EMAIL, identifier="stress-attempts@example.com"
    )
    _, plaintext_otp = OTPRequest.objects.create_for(identity)

    def attempt():
        _verify_otp(identity, "0000")  # always wrong

    _run_concurrent(attempt, n=WORKERS)

    otp_req = OTPRequest.objects.filter(identity=identity).first()

    # The counter must reach at least MAX_ATTEMPTS — no lost F() updates.
    # (It may exceed MAX_ATTEMPTS if multiple threads slipped through is_usable
    # before any increment committed, which is safe and expected.)
    assert otp_req.attempts >= OTPRequest.MAX_ATTEMPTS, (
        f"OTP not exhausted after {WORKERS} concurrent wrong guesses — "
        f"got {otp_req.attempts} attempts (expected >= {OTPRequest.MAX_ATTEMPTS})"
    )

    # After exhaustion the correct OTP must also be rejected.
    _, err = _verify_otp(identity, plaintext_otp)
    assert err is not None, "Correct OTP accepted after concurrent exhaustion — brute-force bypass"


# ---------------------------------------------------------------------------
# 3. Identity creation race — concurrent get_or_create_for_email
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_concurrent_identity_creation_no_duplicates():
    """
    N threads call get_or_create_for_email for the same address simultaneously.
    Exactly 1 User and 1 Identity should be created despite the race.
    """
    email = "stress-create@example.com"

    def attempt():
        identity, _ = Identity.objects.get_or_create_for_email(email)
        return identity.pk

    results = _run_concurrent(attempt, n=WORKERS)

    # All threads must return the same identity PK.
    unique_pks = set(r for r in results if not isinstance(r, Exception))
    assert len(unique_pks) == 1, f"Multiple identities created: {unique_pks}"

    total_users = User.objects.count()
    total_identities = Identity.objects.filter(
        provider=Identity.PROVIDER_EMAIL, identifier=email
    ).count()
    assert total_identities == 1, f"Expected 1 identity, found {total_identities}"
    assert total_users == 1, f"Expected 1 user, found {total_users}"


# ---------------------------------------------------------------------------
# 4. Identity link race — concurrent get_or_create_for_link same identifier
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_concurrent_link_creation_no_duplicates():
    """
    N threads try to link the same identifier to the same user simultaneously.
    Only 1 Identity should be created.
    """
    user = User.objects.create_user()
    identifier = "stress-link@example.com"

    def attempt():
        try:
            identity, _ = Identity.objects.get_or_create_for_link(
                user, Identity.PROVIDER_EMAIL, identifier
            )
            return identity.pk
        except (ValueError, IntegrityError) as exc:
            return exc

    results = _run_concurrent(attempt, n=WORKERS)

    unique_pks = set(r for r in results if not isinstance(r, Exception))
    assert len(unique_pks) == 1, f"Multiple identities created: {unique_pks}"

    total = Identity.objects.filter(
        provider=Identity.PROVIDER_EMAIL, identifier=identifier
    ).count()
    assert total == 1, f"Expected 1 identity, found {total}"


# ---------------------------------------------------------------------------
# 5. Cooldown gate — concurrent OTP requests for same identity
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_concurrent_otp_requests_cooldown_creates_multiple_but_only_one_usable():
    """
    N threads request an OTP simultaneously (bypassing the HTTP cooldown check
    and hitting the manager directly). This validates that even if multiple OTPs
    are created, get_latest_usable always returns the correct newest one.
    """
    user = User.objects.create_user()
    identity = Identity.objects.create(
        user=user, provider=Identity.PROVIDER_EMAIL, identifier="stress-cooldown@example.com"
    )

    def attempt():
        otp_request, otp = OTPRequest.objects.create_for(identity)
        return (otp_request.pk, otp)

    results = _run_concurrent(attempt, n=WORKERS)

    # get_latest_usable must always return a single deterministic result.
    latest = OTPRequest.objects.get_latest_usable(identity)
    assert latest is not None

    # The latest usable must match the most recently created OTP.
    newest_pk = OTPRequest.objects.filter(identity=identity).order_by("-created_at").first().pk
    assert latest.pk == newest_pk
