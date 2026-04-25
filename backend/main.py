"""
Quantum Edge Flow — Backend API
Replaces api.fincept.in for auth, subscriptions, and Stripe payments.
"""
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import stripe
import sqlite3
import hashlib
import secrets
import os
import smtplib
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr
from email.mime.text import MIMEText
from contextlib import asynccontextmanager

# ── Config ────────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY     = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL          = os.environ.get("FRONTEND_URL", "https://quantumedge.business")
DB_PATH               = os.environ.get("DB_PATH", "qef.db")
FOUNDER_EMAIL         = "founder@quantumedge.finance"

stripe.api_key = STRIPE_SECRET_KEY

# Stripe Price IDs — set these after creating products in Stripe dashboard
# Format: price_XXXXXXXXXXXXXXXXXXXXXXXX
STRIPE_PRICES = {
    "basic":      os.environ.get("STRIPE_PRICE_BASIC",      ""),
    "standard":   os.environ.get("STRIPE_PRICE_STANDARD",   ""),
    "pro":        os.environ.get("STRIPE_PRICE_PRO",        ""),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE", ""),
}

# ── Plans (mirrors api.fincept.in/cashfree/plans) ─────────────────────────────
PLANS = [
    {
        "plan_id": "free", "name": "Free Trial",
        "description": "Get started with Quantum Edge Flow. Perfect for testing and learning.",
        "price_usd": 0.0, "currency": "USD", "credits": 350,
        "support_type": "community", "validity_days": 0,
        "features": ["350 credits", "Free tier access", "Community support"],
        "is_free": True, "display_order": 1,
    },
    {
        "plan_id": "basic", "name": "Basic Plan",
        "description": "Essential quantitative modules. Includes 1,000 credits valid for 30 days.",
        "price_usd": 10.0, "currency": "USD", "credits": 1000,
        "support_type": "email", "validity_days": 30,
        "features": ["1,000 credits (valid 30 days)", "Email support", "Core analytics modules"],
        "is_free": False, "display_order": 2,
    },
    {
        "plan_id": "standard", "name": "Standard Plan",
        "description": "Advanced analytics modules. Includes 3,000 credits valid for 30 days.",
        "price_usd": 25.0, "currency": "USD", "credits": 3000,
        "support_type": "email", "validity_days": 30,
        "features": ["3,000 credits (valid 30 days)", "Email support", "Advanced analytics", "Up to 2 concurrent requests"],
        "is_free": False, "display_order": 3,
    },
    {
        "plan_id": "pro", "name": "Professional Plan",
        "description": "Full quantitative toolkit. Includes 7,500 credits valid for 30 days.",
        "price_usd": 50.0, "currency": "USD", "credits": 7500,
        "support_type": "priority", "validity_days": 30,
        "features": ["7,500 credits (valid 30 days)", "Priority support", "Full toolkit", "Up to 3 concurrent requests"],
        "is_free": False, "display_order": 4,
    },
    {
        "plan_id": "enterprise", "name": "Enterprise Plan",
        "description": "Unlimited access to all modules. 16,000 credits valid for 30 days.",
        "price_usd": 100.0, "currency": "USD", "credits": 16000,
        "support_type": "dedicated", "validity_days": 30,
        "features": ["16,000 credits (valid 30 days)", "Dedicated support", "All modules", "Up to 5 concurrent requests", "Custom SLA"],
        "is_free": False, "display_order": 5,
    },
]

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            username      TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            account_type  TEXT NOT NULL DEFAULT 'free',
            credit_balance INTEGER NOT NULL DEFAULT 350,
            is_verified   INTEGER NOT NULL DEFAULT 0,
            mfa_enabled   INTEGER NOT NULL DEFAULT 0,
            phone         TEXT,
            country       TEXT,
            country_code  TEXT,
            created_at    TEXT NOT NULL,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id            TEXT PRIMARY KEY,
            user_id       TEXT NOT NULL,
            api_key       TEXT UNIQUE NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            device_id     TEXT,
            created_at    TEXT NOT NULL,
            expires_at    TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS otps (
            email      TEXT NOT NULL,
            otp        TEXT NOT NULL,
            purpose    TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id              TEXT PRIMARY KEY,
            user_id         TEXT UNIQUE NOT NULL,
            plan_id         TEXT NOT NULL,
            account_type    TEXT NOT NULL,
            stripe_sub_id   TEXT,
            credits         INTEGER NOT NULL DEFAULT 0,
            valid_until     TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            plan_id      TEXT NOT NULL,
            amount_usd   REAL NOT NULL,
            stripe_pi_id TEXT,
            status       TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, stored: str) -> bool:
    salt, h = stored.split(":", 1)
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == h

def now_iso() -> str:
    return datetime.utcnow().isoformat()

def get_current_user(
    x_api_key: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    if not x_api_key:
        raise HTTPException(401, "Missing X-API-Key header")
    db = get_db()
    row = db.execute(
        "SELECT s.user_id, s.expires_at FROM sessions s WHERE s.api_key = ? AND s.session_token = ?",
        (x_api_key, x_session_token or "")
    ).fetchone()
    if not row:
        row = db.execute(
            "SELECT user_id, expires_at FROM sessions WHERE api_key = ?",
            (x_api_key,)
        ).fetchone()
    if not row:
        db.close()
        raise HTTPException(401, "Invalid or expired session")
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        db.close()
        raise HTTPException(401, "Session expired")
    user = db.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
    db.close()
    if not user:
        raise HTTPException(401, "User not found")
    return dict(user)

def effective_account_type(user: dict, db) -> str:
    """Founder always gets pro. Others get their subscription type."""
    if user["email"].lower() == FOUNDER_EMAIL.lower():
        return "pro"
    sub = db.execute("SELECT account_type, valid_until FROM subscriptions WHERE user_id = ?", (user["id"],)).fetchone()
    if sub:
        if sub["valid_until"] and datetime.fromisoformat(sub["valid_until"]) < datetime.utcnow():
            return "free"
        return sub["account_type"]
    return user["account_type"]

# ── App ───────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Quantum Edge Flow API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "Quantum Edge Flow API"}

# ── Plans (unauthenticated) ───────────────────────────────────────────────────
@app.get("/cashfree/plans")
def get_plans():
    return {"success": True, "message": "Success", "data": PLANS}

# ── Auth: Register ────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    phone: str = ""
    country: str = ""
    country_code: str = ""

@app.post("/user/register")
def register(req: RegisterRequest):
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (req.email.lower(),)).fetchone()
    if existing:
        db.close()
        raise HTTPException(400, "Email already registered")

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, email, username, password_hash, account_type, credit_balance, is_verified, created_at, phone, country, country_code) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, req.email.lower(), req.username, hash_password(req.password),
         "free", 350, 0, now_iso(), req.phone, req.country, req.country_code)
    )

    # Generate OTP
    otp = str(secrets.randbelow(900000) + 100000)
    expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    db.execute("DELETE FROM otps WHERE email = ? AND purpose = 'verify'", (req.email.lower(),))
    db.execute("INSERT INTO otps (email, otp, purpose, expires_at) VALUES (?,?,?,?)",
               (req.email.lower(), otp, "verify", expires))
    db.commit()
    db.close()

    # TODO: send OTP email — for now log it
    print(f"[OTP] {req.email}: {otp}")

    return {"success": True, "message": "Registration successful. Check your email for OTP.", "data": {"user_id": user_id}}

# ── Auth: Verify OTP ──────────────────────────────────────────────────────────
class OtpRequest(BaseModel):
    email: str
    otp: str

@app.post("/user/verify-otp")
def verify_otp(req: OtpRequest):
    db = get_db()
    row = db.execute(
        "SELECT * FROM otps WHERE email = ? AND otp = ? AND purpose = 'verify'",
        (req.email.lower(), req.otp)
    ).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        db.close()
        raise HTTPException(400, "Invalid or expired OTP")
    db.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (req.email.lower(),))
    db.execute("DELETE FROM otps WHERE email = ? AND purpose = 'verify'", (req.email.lower(),))
    db.commit()
    db.close()
    return {"success": True, "message": "Email verified successfully"}

# ── Auth: Login ───────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str
    force_login: bool = False
    device_id: str = ""

@app.post("/user/login")
def login(req: LoginRequest):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (req.email.lower(),)).fetchone()

    # Founder auto-provision: if account doesn't exist yet, create it on first login
    if not user and req.email.lower() == FOUNDER_EMAIL.lower():
        founder_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO users (id, email, username, password_hash, account_type, credit_balance, is_verified, created_at, phone, country, country_code) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (founder_id, FOUNDER_EMAIL.lower(), "Founder", hash_password(req.password),
             "pro", 999999, 1, now_iso(), "", "", "")
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (FOUNDER_EMAIL.lower(),)).fetchone()

    if not user or not verify_password(req.password, user["password_hash"]):
        db.close()
        raise HTTPException(401, "Invalid email or password")

    # Founder bypasses verification check
    if user["email"].lower() != FOUNDER_EMAIL.lower() and not user["is_verified"]:
        db.close()
        raise HTTPException(403, "Email not verified. Please verify your OTP.")

    api_key     = secrets.token_hex(32)
    session_tok = secrets.token_hex(32)
    session_id  = str(uuid.uuid4())
    expires     = (datetime.utcnow() + timedelta(days=30)).isoformat()

    db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso(), user["id"]))
    db.execute(
        "INSERT INTO sessions (id, user_id, api_key, session_token, device_id, created_at, expires_at) VALUES (?,?,?,?,?,?,?)",
        (session_id, user["id"], api_key, session_tok, req.device_id, now_iso(), expires)
    )
    db.commit()

    account_type = effective_account_type(dict(user), db)
    db.close()

    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "api_key": api_key,
            "session_token": session_tok,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "account_type": account_type,
                "credit_balance": user["credit_balance"],
                "is_verified": bool(user["is_verified"]),
                "mfa_enabled": bool(user["mfa_enabled"]),
            }
        }
    }

# ── Auth: Logout ──────────────────────────────────────────────────────────────
@app.post("/user/logout")
def logout(user: dict = Depends(get_current_user), x_api_key: Optional[str] = Header(None)):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE api_key = ?", (x_api_key,))
    db.commit()
    db.close()
    return {"success": True, "message": "Logged out"}

# ── Auth: Forgot / Reset Password ─────────────────────────────────────────────
class ForgotRequest(BaseModel):
    email: str

@app.post("/user/forgot-password")
def forgot_password(req: ForgotRequest):
    db = get_db()
    user = db.execute("SELECT id FROM users WHERE email = ?", (req.email.lower(),)).fetchone()
    if not user:
        db.close()
        return {"success": True, "message": "If this email exists, an OTP has been sent."}
    otp     = str(secrets.randbelow(900000) + 100000)
    expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    db.execute("DELETE FROM otps WHERE email = ? AND purpose = 'reset'", (req.email.lower(),))
    db.execute("INSERT INTO otps (email, otp, purpose, expires_at) VALUES (?,?,?,?)",
               (req.email.lower(), otp, "reset", expires))
    db.commit()
    db.close()
    print(f"[RESET OTP] {req.email}: {otp}")
    return {"success": True, "message": "If this email exists, an OTP has been sent."}

class ResetRequest(BaseModel):
    email: str
    otp: str
    new_password: str

@app.post("/user/reset-password")
def reset_password(req: ResetRequest):
    db = get_db()
    row = db.execute(
        "SELECT * FROM otps WHERE email = ? AND otp = ? AND purpose = 'reset'",
        (req.email.lower(), req.otp)
    ).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        db.close()
        raise HTTPException(400, "Invalid or expired OTP")
    db.execute("UPDATE users SET password_hash = ? WHERE email = ?",
               (hash_password(req.new_password), req.email.lower()))
    db.execute("DELETE FROM otps WHERE email = ? AND purpose = 'reset'", (req.email.lower(),))
    db.commit()
    db.close()
    return {"success": True, "message": "Password reset successful"}

# ── User: Profile ─────────────────────────────────────────────────────────────
@app.get("/user/profile")
def get_profile(user: dict = Depends(get_current_user)):
    db = get_db()
    account_type = effective_account_type(user, db)
    db.close()
    return {
        "success": True,
        "data": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "account_type": account_type,
            "credit_balance": user["credit_balance"],
            "is_verified": bool(user["is_verified"]),
            "mfa_enabled": bool(user["mfa_enabled"]),
            "phone": user.get("phone", ""),
            "country": user.get("country", ""),
            "last_login_at": user.get("last_login_at", ""),
        }
    }

@app.put("/user/profile")
def update_profile(data: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    if "username" in data:
        db.execute("UPDATE users SET username = ? WHERE id = ?", (data["username"], user["id"]))
    db.commit()
    db.close()
    return {"success": True, "message": "Profile updated"}

# ── User: Subscriptions ───────────────────────────────────────────────────────
@app.get("/user/subscriptions")
def get_subscriptions(user: dict = Depends(get_current_user)):
    db = get_db()
    account_type = effective_account_type(user, db)
    sub = db.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user["id"],)).fetchone()
    db.close()

    credits  = 0
    valid_until = None
    if sub:
        credits     = sub["credits"]
        valid_until = sub["valid_until"]
    elif user["email"].lower() == FOUNDER_EMAIL.lower():
        credits = 999999

    return {
        "success": True,
        "data": {
            "account_type": account_type,
            "credit_balance": credits,
            "credits_expire_at": valid_until,
            "last_credit_purchase_at": sub["created_at"] if sub else None,
        }
    }

# ── Stripe: Generate Checkout Token / Session ─────────────────────────────────
class CheckoutRequest(BaseModel):
    plan_id: str

@app.post("/user/generate-checkout-token")
def generate_checkout(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    price_id = STRIPE_PRICES.get(req.plan_id)
    if not price_id:
        raise HTTPException(400, f"No Stripe price configured for plan: {req.plan_id}")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/payment-success?plan={req.plan_id}",
        cancel_url=f"{FRONTEND_URL}/pricing",
        customer_email=user["email"],
        metadata={"user_id": user["id"], "plan_id": req.plan_id},
    )
    return {
        "success": True,
        "data": {
            "token": session.id,
            "checkout_url": session.url,
        }
    }

# The Qt app opens: https://fincept.in/checkout?token=X&plan=Y
# We replicate that redirect so the existing app code works:
@app.get("/checkout")
def checkout_redirect(token: str, plan: str):
    from fastapi.responses import RedirectResponse
    session = stripe.checkout.Session.retrieve(token)
    return RedirectResponse(session.url)

# ── Stripe: Webhook ───────────────────────────────────────────────────────────
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig     = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        user_id  = session["metadata"].get("user_id")
        plan_id  = session["metadata"].get("plan_id")
        sub_id   = session.get("subscription")

        if user_id and plan_id:
            plan     = next((p for p in PLANS if p["plan_id"] == plan_id), None)
            credits  = plan["credits"] if plan else 0
            days     = plan["validity_days"] if plan else 30
            valid_until = (datetime.utcnow() + timedelta(days=days)).isoformat() if days > 0 else None

            db = get_db()
            existing = db.execute("SELECT id FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
            if existing:
                db.execute(
                    "UPDATE subscriptions SET plan_id=?, account_type=?, stripe_sub_id=?, credits=?, valid_until=?, updated_at=? WHERE user_id=?",
                    (plan_id, plan_id, sub_id, credits, valid_until, now_iso(), user_id)
                )
            else:
                db.execute(
                    "INSERT INTO subscriptions (id, user_id, plan_id, account_type, stripe_sub_id, credits, valid_until, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), user_id, plan_id, plan_id, sub_id, credits, valid_until, now_iso(), now_iso())
                )
            db.execute("UPDATE users SET account_type = ? WHERE id = ?", (plan_id, user_id))

            amount = session.get("amount_total", 0) / 100.0
            db.execute(
                "INSERT INTO transactions (id, user_id, plan_id, amount_usd, stripe_pi_id, status, created_at) VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), user_id, plan_id, amount, sub_id, "completed", now_iso())
            )
            db.commit()
            db.close()

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.updated"):
        sub = event["data"]["object"]
        if event["type"] == "customer.subscription.deleted":
            db = get_db()
            db.execute(
                "UPDATE subscriptions SET account_type='free', plan_id='free' WHERE stripe_sub_id=?",
                (sub["id"],)
            )
            db.commit()
            db.close()

    return {"received": True}

# ── Session Pulse (keep-alive) ────────────────────────────────────────────────
@app.get("/user/session-pulse")
def session_pulse(user: dict = Depends(get_current_user)):
    return {"success": True, "authenticated": True}

# ── Auth Status ───────────────────────────────────────────────────────────────
@app.get("/auth/status")
def auth_status(user: dict = Depends(get_current_user)):
    db = get_db()
    account_type = effective_account_type(user, db)
    db.close()
    return {"success": True, "authenticated": True, "account_type": account_type}

# ── Transactions ──────────────────────────────────────────────────────────────
@app.get("/user/transactions")
def get_transactions(user: dict = Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],)
    ).fetchall()
    db.close()
    return {"success": True, "data": [dict(r) for r in rows]}

@app.get("/user/credits")
def get_credits(user: dict = Depends(get_current_user)):
    db = get_db()
    sub = db.execute("SELECT credits, valid_until FROM subscriptions WHERE user_id = ?", (user["id"],)).fetchone()
    db.close()
    credits = sub["credits"] if sub else user["credit_balance"]
    if user["email"].lower() == FOUNDER_EMAIL.lower():
        credits = 999999
    return {"success": True, "data": {"credit_balance": credits, "expires_at": sub["valid_until"] if sub else None}}

# ── MFA stubs (app calls these) ───────────────────────────────────────────────
@app.post("/user/mfa/enable")
def mfa_enable(user: dict = Depends(get_current_user)):
    return {"success": True, "message": "MFA not yet supported — coming soon"}

@app.post("/user/mfa/disable")
def mfa_disable(user: dict = Depends(get_current_user)):
    return {"success": True, "message": "MFA not yet supported — coming soon"}

@app.post("/user/verify-mfa")
def verify_mfa(data: dict):
    raise HTTPException(400, "MFA not enabled")

# ── Regenerate API Key ────────────────────────────────────────────────────────
@app.post("/user/regenerate-api-key")
def regen_api_key(user: dict = Depends(get_current_user), x_api_key: Optional[str] = Header(None)):
    new_key = secrets.token_hex(32)
    db = get_db()
    db.execute("UPDATE sessions SET api_key = ? WHERE api_key = ?", (new_key, x_api_key))
    db.commit()
    db.close()
    return {"success": True, "data": {"api_key": new_key}}

# ── Login History ─────────────────────────────────────────────────────────────
@app.get("/user/login-history")
def login_history(user: dict = Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT created_at, device_id FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user["id"],)
    ).fetchall()
    db.close()
    return {"success": True, "data": [dict(r) for r in rows]}

# ── Support stubs ─────────────────────────────────────────────────────────────
@app.get("/support/tickets")
def get_tickets(user: dict = Depends(get_current_user)):
    return {"success": True, "data": []}

@app.post("/support/tickets")
def create_ticket(data: dict, user: dict = Depends(get_current_user)):
    return {"success": True, "message": "Ticket submitted. We'll respond at " + user["email"]}

@app.get("/support/categories")
def support_categories():
    return {"success": True, "data": ["General", "Billing", "Technical", "Security"]}

@app.post("/support/feedback")
def submit_feedback(data: dict, user: dict = Depends(get_current_user)):
    return {"success": True, "message": "Thank you for your feedback!"}

# ── Account deletion ──────────────────────────────────────────────────────────
@app.delete("/user/account")
def delete_account(user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user["id"],))
    db.execute("DELETE FROM transactions WHERE user_id = ?", (user["id"],))
    db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    db.commit()
    db.close()
    return {"success": True, "message": "Account deleted"}
