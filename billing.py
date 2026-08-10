from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qs

import httpx
from sqlalchemy.orm import Session

from .db import User

STRIPE_API = "https://api.stripe.com/v1"


def configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY") and os.environ.get("STRIPE_PRICE_ID"))


def require_subscription() -> bool:
    return os.environ.get("REQUIRE_SUBSCRIPTION", "false").lower() in {"1", "true", "yes"}


def has_access(user: User) -> bool:
    if not require_subscription():
        return True
    return user.subscription_status in {"active", "trialing"}


def _headers() -> dict[str, str]:
    secret = os.environ.get("STRIPE_SECRET_KEY")
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    import base64
    auth = base64.b64encode((secret + ":").encode()).decode()
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}


def create_checkout(user: User, base_url: str) -> str:
    if not configured():
        raise RuntimeError("Stripe billing is not configured")
    data: list[tuple[str, str]] = [
        ("mode", "subscription"),
        ("line_items[0][price]", os.environ["STRIPE_PRICE_ID"]),
        ("line_items[0][quantity]", "1"),
        ("success_url", f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"),
        ("cancel_url", f"{base_url}/subscribe"),
        ("client_reference_id", str(user.id)),
        ("metadata[user_id]", str(user.id)),
        ("subscription_data[metadata][user_id]", str(user.id)),
        ("allow_promotion_codes", "true"),
    ]
    if user.stripe_customer_id:
        data.append(("customer", user.stripe_customer_id))
    else:
        data.append(("customer_email", user.email))
    r = httpx.post(f"{STRIPE_API}/checkout/sessions", headers=_headers(), data=data, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"Stripe Checkout failed: {r.text}")
    return r.json()["url"]


def create_portal(user: User, base_url: str) -> str:
    if not user.stripe_customer_id:
        raise RuntimeError("No Stripe customer is linked to this account")
    r = httpx.post(
        f"{STRIPE_API}/billing_portal/sessions",
        headers=_headers(),
        data={"customer": user.stripe_customer_id, "return_url": f"{base_url}/account"},
        timeout=30.0,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Stripe customer portal failed: {r.text}")
    return r.json()["url"]


def fetch_checkout_session(session_id: str) -> dict:
    r = httpx.get(f"{STRIPE_API}/checkout/sessions/{session_id}", headers=_headers(), params={"expand[]": "subscription"}, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError("Could not verify Checkout session")
    return r.json()


def verify_webhook(raw_body: bytes, signature_header: str) -> bool:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        return False
    values = {}
    for piece in signature_header.split(","):
        if "=" in piece:
            k, v = piece.split("=", 1)
            values.setdefault(k, []).append(v)
    try:
        timestamp = int(values["t"][0])
    except Exception:
        return False
    if abs(time.time() - timestamp) > 300:
        return False
    signed = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in values.get("v1", []))


def apply_event(db: Session, event: dict) -> None:
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    user_id = None
    metadata = obj.get("metadata") or {}
    if metadata.get("user_id"):
        user_id = int(metadata["user_id"])
    if etype == "checkout.session.completed":
        if obj.get("client_reference_id"):
            user_id = int(obj["client_reference_id"])
        user = db.get(User, user_id) if user_id else None
        if user:
            user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
            user.stripe_subscription_id = obj.get("subscription") or user.stripe_subscription_id
            user.subscription_status = "active" if obj.get("payment_status") in {"paid", "no_payment_required"} else "pending"
            db.commit()
        return
    if etype.startswith("customer.subscription."):
        if not user_id and obj.get("id"):
            from sqlalchemy import select
            user = db.scalar(select(User).where(User.stripe_subscription_id == obj.get("id")))
        else:
            user = db.get(User, user_id) if user_id else None
        if user:
            user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
            user.stripe_subscription_id = obj.get("id") or user.stripe_subscription_id
            user.subscription_status = obj.get("status", "unknown")
            db.commit()
