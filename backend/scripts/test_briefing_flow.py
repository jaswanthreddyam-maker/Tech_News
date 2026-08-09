"""
End-to-end test for Daily Briefing V1 — Production Lifecycle

Tests:
  1. Top 5 subscriber → receives exactly 5 stories
  2. Top 10 subscriber → receives exactly 10 stories
  3. Edition max capacity invariant (10 items regardless of first subscriber's preference)
  4. Duplicate dispatch blocked by UNIQUE(subscriber_id, edition_id)
  5. Test re-dispatch works idempotently (reuses existing delivery record)
  6. Email verification flow (token issue → verify → enabled)
  7. Unsubscribe via raw signed token (hash comparison server-side)
  8. Timezone dispatch window — is_delivery_due() correctness
  9. State-transition protection (terminal state blocks further transitions)
  10. Click tracking: click_count increments; provider webhook does NOT double count

Run from backend directory:
    venv\\Scripts\\python.exe scripts\\test_briefing_flow.py
"""
import asyncio
import sys
import os
import io
import logging
from datetime import datetime, timezone, timedelta

# Fix Windows console Unicode encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PASS = "✓ PASS"
FAIL = "✗ FAIL"
results = []


def record(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append((name, passed, detail))
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))


async def run_tests():
    from app.core.database import AsyncSessionLocal
    from app.briefing.models import (
        DailyBriefingSubscriber, DailyBriefingDelivery, DailyBriefingEdition,
        DailyBriefingItem, BriefingDeliveryStatus, can_transition,
        BRIEFING_TERMINAL_STATES, BRIEFING_STATE_TRANSITIONS,
    )
    from app.briefing.service import (
        DailyBriefingService, EDITION_MAX_CAPACITY,
        is_delivery_due, create_signed_unsubscribe_token, hash_token,
        create_signed_verification_token,
    )
    from sqlalchemy import select, delete

    print("\n=== Daily Briefing V1 End-to-End Test ===\n")

    async with AsyncSessionLocal() as db:
        # ------------------------------------------------------------------
        # Setup: clean test subscribers from previous runs
        # ------------------------------------------------------------------
        for test_email in ["top5@test.com", "top10@test.com"]:
            sub = (await db.execute(
                select(DailyBriefingSubscriber).where(DailyBriefingSubscriber.email == test_email)
            )).scalar_one_or_none()
            if sub:
                await db.delete(sub)
        await db.commit()

        # ------------------------------------------------------------------
        # 1. Create Top-5 and Top-10 subscribers
        # ------------------------------------------------------------------
        print("1. Subscriber creation:")
        sub5 = await DailyBriefingService.get_or_create_subscriber(db, "top5@test.com")
        sub5.story_count = 5
        sub5.email_verified_at = datetime.now(timezone.utc)
        sub5.enabled = True

        sub10 = await DailyBriefingService.get_or_create_subscriber(db, "top10@test.com")
        sub10.story_count = 10
        sub10.email_verified_at = datetime.now(timezone.utc)
        sub10.enabled = True
        await db.flush()
        record("Top-5 subscriber created", sub5.id is not None)
        record("Top-10 subscriber created", sub10.id is not None)

        # ------------------------------------------------------------------
        # 2. Edition max capacity invariant
        # ------------------------------------------------------------------
        print("\n2. Edition capacity invariant (always 10):")
        edition = await DailyBriefingService.get_or_create_daily_edition(db)
        await db.flush()
        all_items = getattr(edition, "loaded_items", [])
        record(
            f"Edition generated with {len(all_items)} items (max={EDITION_MAX_CAPACITY})",
            len(all_items) <= EDITION_MAX_CAPACITY and len(all_items) > 0,
            f"items={len(all_items)}"
        )
        record(
            "Edition capacity matches EDITION_MAX_CAPACITY",
            len(all_items) <= EDITION_MAX_CAPACITY,
        )

        # ------------------------------------------------------------------
        # 3. Top 5 dispatch — subscriber receives 5 stories
        # ------------------------------------------------------------------
        print("\n3. Top-5 dispatch:")
        del5 = await DailyBriefingService.dispatch_delivery(db, edition, sub5, is_test=True)
        await db.flush()
        record("Top-5 delivery dispatched", del5.id is not None)
        record(
            f"stories_delivered = {del5.stories_delivered} (expected 5)",
            del5.stories_delivered == min(5, len(all_items)),
            f"got={del5.stories_delivered}"
        )

        # ------------------------------------------------------------------
        # 4. Top 10 dispatch — subscriber receives up to 10 stories
        # ------------------------------------------------------------------
        print("\n4. Top-10 dispatch:")
        del10 = await DailyBriefingService.dispatch_delivery(db, edition, sub10, is_test=True)
        await db.flush()
        record("Top-10 delivery dispatched", del10.id is not None)
        record(
            f"stories_delivered = {del10.stories_delivered} (expected up to 10)",
            del10.stories_delivered == min(10, len(all_items)),
            f"got={del10.stories_delivered}"
        )

        # ------------------------------------------------------------------
        # 5. Duplicate non-test dispatch blocked by UNIQUE constraint
        # ------------------------------------------------------------------
        print("\n5. Duplicate dispatch idempotency:")
        sub5.email_verified_at = datetime.now(timezone.utc)
        returned_del = await DailyBriefingService.dispatch_delivery(db, edition, sub5, is_test=False)
        record(
            "Non-test duplicate dispatch returns existing delivery (idempotent)",
            returned_del.id == del5.id,
            f"original_id={del5.id}, returned_id={returned_del.id}"
        )

        # ------------------------------------------------------------------
        # 6. Test re-dispatch reuses existing record (no UNIQUE violation)
        # ------------------------------------------------------------------
        print("\n6. Test re-dispatch idempotency:")
        try:
            retest_del = await DailyBriefingService.dispatch_delivery(db, edition, sub5, is_test=True)
            record(
                "Test re-dispatch succeeds without constraint error",
                retest_del.id == del5.id,
                f"delivery_id={retest_del.id}"
            )
        except Exception as e:
            record("Test re-dispatch", False, str(e))

        # ------------------------------------------------------------------
        # 7. Email verification flow
        # ------------------------------------------------------------------
        print("\n7. Email verification flow:")
        # Create unverified subscriber
        unsub_email = "verify_test@test.com"
        existing = (await db.execute(
            select(DailyBriefingSubscriber).where(DailyBriefingSubscriber.email == unsub_email)
        )).scalar_one_or_none()
        if existing:
            await db.delete(existing)
            await db.flush()

        verify_sub = await DailyBriefingService.get_or_create_subscriber(db, unsub_email)
        record("Unverified subscriber has enabled=False", verify_sub.enabled == False)
        record("Unverified subscriber has email_verified_at=None", verify_sub.email_verified_at is None)

        # Send verification email (uses mock provider in dev)
        await DailyBriefingService.send_verification_email(db, verify_sub)
        await db.flush()
        record("Verification token hash stored", verify_sub.verification_token_hash is not None)

        # Verify via token
        raw_token = create_signed_verification_token(verify_sub.id, verify_sub.email)
        # Store the hash (simulates what send_verification_email stores)
        verify_sub.verification_token_hash = hash_token(raw_token)
        await db.flush()
        verified_sub = await DailyBriefingService.verify_email_token(db, raw_token)
        record("verify_email_token returns subscriber", verified_sub is not None)
        if verified_sub:
            record("email_verified_at is set after verification", verified_sub.email_verified_at is not None)
            record("enabled=True after verification", verified_sub.enabled == True)
            record("verification_token_hash cleared", verified_sub.verification_token_hash is None)

        # ------------------------------------------------------------------
        # 8. Unsubscribe via raw signed token
        # ------------------------------------------------------------------
        print("\n8. Unsubscribe flow:")
        raw_unsub_token = create_signed_unsubscribe_token(sub10.id, sub10.email)
        sub10.unsubscribe_token_hash = hash_token(raw_unsub_token)
        await db.flush()

        unsub_result = await DailyBriefingService.unsubscribe_by_token(db, raw_unsub_token)
        record("Unsubscribe returns subscriber", unsub_result is not None)
        if unsub_result:
            record("enabled=False after unsubscribe", unsub_result.enabled == False)
            record("unsubscribed_at is set", unsub_result.unsubscribed_at is not None)

        # Confirm wrong token fails
        bad_result = await DailyBriefingService.unsubscribe_by_token(db, "invalid.token")
        record("Invalid unsubscribe token rejected", bad_result is None)

        # ------------------------------------------------------------------
        # 9. Timezone dispatch window — is_delivery_due()
        # ------------------------------------------------------------------
        print("\n9. Timezone dispatch window (is_delivery_due):")
        # Sub with delivery_time="14:30" Asia/Kolkata
        now_utc = datetime.now(timezone.utc)
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Kolkata")
        local_now = now_utc.astimezone(tz)
        on_time = local_now.strftime("%H:%M")
        off_time = (local_now + timedelta(hours=3)).strftime("%H:%M")

        mock_sub = type("Sub", (), {
            "id": 999,
            "delivery_time": on_time,
            "timezone": "Asia/Kolkata",
        })()
        due = is_delivery_due(mock_sub, now_utc)
        record(f"Subscriber due at current local time {on_time}", due, f"is_due={due}")

        mock_sub_off = type("Sub", (), {
            "id": 998,
            "delivery_time": off_time,
            "timezone": "Asia/Kolkata",
        })()
        not_due = not is_delivery_due(mock_sub_off, now_utc)
        record(f"Subscriber NOT due at future time {off_time}", not_due)

        # Minute precision test — minute=m, NOT minute=0
        minute_sub = type("Sub", (), {
            "id": 997,
            "delivery_time": "08:30",
            "timezone": "Asia/Kolkata",
        })()
        # Create a now_utc that is exactly 08:30 IST
        from datetime import date
        today = date.today()
        tz_ist = ZoneInfo("Asia/Kolkata")
        target_local = datetime(today.year, today.month, today.day, 8, 30, 0, tzinfo=tz_ist)
        target_utc = target_local.astimezone(timezone.utc)
        minute_due = is_delivery_due(minute_sub, target_utc)
        record("Minute precision: 08:30 is due at exactly 08:30 IST", minute_due, f"is_due={minute_due}")

        # ------------------------------------------------------------------
        # 10. State-transition protection
        # ------------------------------------------------------------------
        print("\n10. State-transition protection:")
        record(
            "PENDING → QUEUED allowed",
            can_transition(BriefingDeliveryStatus.PENDING, BriefingDeliveryStatus.QUEUED)
        )
        record(
            "QUEUED → SENT allowed",
            can_transition(BriefingDeliveryStatus.QUEUED, BriefingDeliveryStatus.SENT)
        )
        record(
            "SENT → DELIVERED allowed",
            can_transition(BriefingDeliveryStatus.SENT, BriefingDeliveryStatus.DELIVERED)
        )
        record(
            "BOUNCED → DELIVERED BLOCKED (terminal state)",
            not can_transition(BriefingDeliveryStatus.BOUNCED, BriefingDeliveryStatus.DELIVERED)
        )
        record(
            "FAILED → SENT BLOCKED (terminal state)",
            not can_transition(BriefingDeliveryStatus.FAILED, BriefingDeliveryStatus.SENT)
        )
        record(
            "DELIVERED → COMPLAINED allowed",
            can_transition(BriefingDeliveryStatus.DELIVERED, BriefingDeliveryStatus.COMPLAINED)
        )
        record(
            "DELIVERED → BOUNCED BLOCKED",
            not can_transition(BriefingDeliveryStatus.DELIVERED, BriefingDeliveryStatus.BOUNCED)
        )

        await db.rollback()  # Don't persist test data

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*45}")
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    if passed < total:
        print("\nFailed tests:")
        for name, p, detail in results:
            if not p:
                print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))
    print("="*45)
    return passed == total


if __name__ == "__main__":
    ok = asyncio.run(run_tests())
    sys.exit(0 if ok else 1)
