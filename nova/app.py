from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import httpx
import jwt
import tweepy
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import Response, FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from . import ai, billing, brands, allowances, customer_service, readiness
from .connections import connection_options, safe_login_next
from .db import (
    Activity, AuthIdentity, AuthState, Creator, CreatorPreferences, Draft, MediaAsset, OAuth2Connection, OAuthState,
    PostLog, ScheduledPost, SessionLocal, SocialConnection, User, DeletionRequest, get_db, get_preferences, utcnow,
)
from .scheduler import loop as scheduler_loop, process_due
from .security import revoke_session, current_user, decrypt, encrypt, hash_api_key, hash_password, make_state, make_user_session, verify_password
from .user_data import normalize_country, normalize_email, normalize_name
from .social import (
    INSTAGRAM_SCOPES, INSTAGRAM_FACEBOOK_SCOPES, META_SCOPES, TIKTOK_SCOPES, X_SCOPES, analytics_for_user, instagram_authorize_url, instagram_exchange, meta_authorize_url, meta_exchange,
    publish_platform, publishing_context, recent_content_for_user, recent_posts_for_user, resolve_tiktok_post, tiktok_authorize_url, tiktok_exchange, upsert_connection, x_authorize_url, x_exchange,
)
from .storage import UPLOAD_DIR, save_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nova")
# OAuth exchanges put secrets and short-lived codes in query parameters. Never
# allow the HTTP client to print those request URLs into provider logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def base_url() -> str:
    value = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return value or "http://localhost:8000"


def subscription_guard(user: User) -> None:
    if not billing.has_access(user):
        raise HTTPException(status_code=402, detail="An active Zova subscription is required")


def template_context(request: Request, user: User | None = None, **kwargs: Any) -> dict[str, Any]:
    if user and not hasattr(request.state,'brand_id'):
        with SessionLocal() as context_db:brands.bind_request(context_db,request)
    brand = brands.context(user, getattr(request.state, 'brand_id', 0)) if user else None
    return {"request": request, "user": user, "brand": brand, "connections": connection_options(), **customer_service.context(), **kwargs}


def set_user_cookie(response: RedirectResponse | JSONResponse, user: User) -> None:
    response.set_cookie(
        "nova_session", make_user_session(user.id), max_age=30 * 86400, httponly=True,
        secure=base_url().startswith("https://"), samesite="lax", path="/",
    )


def learn_voice_from_socials(db: Session, user_id: int) -> dict[str, Any] | None:
    posts = recent_content_for_user(db, user_id)
    if not posts:
        return None
    with allowances.ai_action(db, user_id):
        profile = ai.infer_voice_profile("\n\n--- POST ---\n\n".join(posts))
        prefs = get_preferences(db, user_id)
        prefs.writing_tone = profile["writing_tone"][:5000]
        prefs.audience = profile["audience"][:5000]
        prefs.topics = profile["topics"][:5000]
        prefs.things_to_avoid = profile["things_to_avoid"][:5000]
        prefs.example_posts = "\n\n".join(posts)[:12000]
        prefs.preferred_post_length = profile["preferred_post_length"]
        db.commit()
        return {**profile, "posts_scanned": len(posts)}


def _state_row(db: Session, raw_state: str, platform: str) -> OAuthState:
    row = db.scalar(select(OAuthState).where(OAuthState.state_hash == hash_api_key(raw_state), OAuthState.platform == platform, OAuthState.used.is_(False)))
    if not row:
        raise HTTPException(400, "Invalid or already-used OAuth state")
    created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
    if created < utcnow() - timedelta(minutes=20):
        raise HTTPException(400, "OAuth connection request expired. Please try again.")
    row.used = True; db.commit()
    return row


def _new_state(db: Session, user_id: int, platform: str, verifier: str | None = None) -> str:
    state = make_state()
    db.add(OAuthState(user_id=user_id, brand_id=db.info.get('brand_id',0), platform=platform, state_hash=hash_api_key(state), encrypted_code_verifier=encrypt(verifier) if verifier else None))
    db.commit()
    return state


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid or missing API key", headers={"WWW-Authenticate": "Bearer"})
    return token


def require_legacy_creator(authorization: Annotated[str | None, Header()] = None, db: Session = Depends(get_db)) -> Creator:
    token = bearer_token(authorization)
    creator = db.scalar(select(Creator).where(Creator.api_key_hash == hash_api_key(token), Creator.active.is_(True)))
    if not creator:
        raise HTTPException(401, "Invalid or inactive creator API key")
    return creator


def _legacy_x_token(connection: OAuth2Connection, db: Session) -> str:
    expires = connection.expires_at
    if expires and expires.tzinfo is None: expires = expires.replace(tzinfo=timezone.utc)
    if expires and expires <= utcnow() + timedelta(minutes=2):
        if not connection.encrypted_refresh_token: raise RuntimeError("X connection expired")
        client_id = os.environ.get("X_OAUTH2_CLIENT_ID", ""); client_secret = os.environ.get("X_OAUTH2_CLIENT_SECRET", "")
        data = {"grant_type": "refresh_token", "refresh_token": decrypt(connection.encrypted_refresh_token)}
        auth = (client_id, client_secret) if client_secret else None
        if not client_secret: data["client_id"] = client_id
        r = httpx.post("https://api.x.com/2/oauth2/token", data=data, auth=auth, timeout=30.0)
        if r.status_code >= 400: raise RuntimeError("X token refresh failed")
        payload = r.json(); connection.encrypted_access_token = encrypt(payload["access_token"])
        if payload.get("refresh_token"): connection.encrypted_refresh_token = encrypt(payload["refresh_token"])
        connection.expires_at = utcnow() + timedelta(seconds=max(int(payload.get("expires_in", 7200))-60,60)); db.commit()
        return payload["access_token"]
    return decrypt(connection.encrypted_access_token)


def publish_legacy_creator(text: str, creator: Creator, db: Session) -> dict[str, str]:
    row = PostLog(creator_id=creator.id, text=text, status="attempted"); db.add(row); db.commit(); db.refresh(row)
    try:
        oauth = db.scalar(select(OAuth2Connection).where(OAuth2Connection.creator_id == creator.id))
        if oauth:
            token = _legacy_x_token(oauth, db)
            r = httpx.post("https://api.x.com/2/tweets", headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}, json={"text": text}, timeout=30.0)
            if r.status_code >= 400: raise RuntimeError(r.text)
            pid = str(r.json()["data"]["id"])
        else:
            client = tweepy.Client(consumer_key=decrypt(creator.encrypted_x_api_key), consumer_secret=decrypt(creator.encrypted_x_api_secret), access_token=decrypt(creator.encrypted_x_access_token), access_token_secret=decrypt(creator.encrypted_x_access_token_secret))
            resp = client.create_tweet(text=text); pid = str(resp.data["id"])
        row.status="published"; row.x_post_id=pid; db.commit()
        return {"post_id": pid, "url": f"https://x.com/{creator.x_username}/status/{pid}"}
    except Exception as exc:
        row.status="failed"; row.error=str(exc); db.commit(); raise HTTPException(502, f"X API error: {exc}") from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_legacy_account()
    task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass


app = FastAPI(title="Zova Social Publishing", version="5.1.0", lifespan=lifespan)
from .request_security import SecurityMiddleware, allowed_request
from .recovery import router as recovery_router
from .body_limit import BodyLimitMiddleware
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(SecurityMiddleware)
app.include_router(recovery_router)
from .schedule_routes import router as schedule_router
app.include_router(schedule_router)
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


@app.exception_handler(HTTPException)
async def authentication_error(request: Request, exc: HTTPException):
    # Only browser pages redirect. APIs and OAuth callbacks retain their errors.
    private_pages = {"/studio", "/account", "/analytics", "/drafts", "/subscribe",
                     "/onboarding/socials", "/onboarding/writing-style", "/onboarding/complete"}
    connection_path = request.url.path
    oauth_starts = {value["start"]: f"/connect/{key}" for key, value in connection_options().items()}
    oauth_starts["/oauth/instagram/facebook/start"] = "/connect/instagram"
    if exc.status_code == 401 and request.method == "GET" and (connection_path.startswith("/connect/") or connection_path in oauth_starts):
        destination = safe_login_next(oauth_starts.get(connection_path, connection_path))
        return RedirectResponse("/login?next=" + quote_plus(destination), status_code=303)
    if exc.status_code == 401 and request.method == "GET" and request.url.path in private_pages:
        return RedirectResponse("/login", status_code=303)
    return await http_exception_handler(request, exc)


def bootstrap_legacy_account() -> None:
    needed = ["BOOTSTRAP_CREATOR_API_KEY","X_API_KEY","X_API_SECRET","X_ACCESS_TOKEN","X_ACCESS_TOKEN_SECRET","X_USERNAME"]
    if not all(os.environ.get(x) for x in needed): return
    username = os.environ["X_USERNAME"].lstrip("@")
    with SessionLocal() as db:
        if db.scalar(select(Creator).where(Creator.x_username == username)): return
        db.add(Creator(name=os.environ.get("BOOTSTRAP_CREATOR_NAME") or username, x_username=username, api_key_hash=hash_api_key(os.environ["BOOTSTRAP_CREATOR_API_KEY"]), encrypted_x_api_key=encrypt(os.environ["X_API_KEY"]), encrypted_x_api_secret=encrypt(os.environ["X_API_SECRET"]), encrypted_x_access_token=encrypt(os.environ["X_ACCESS_TOKEN"]), encrypted_x_access_token_secret=encrypt(os.environ["X_ACCESS_TOKEN_SECRET"])))
        db.commit(); log.info("Bootstrapped legacy X creator @%s", username)


# ---------- Pages + auth ----------
@app.get("/health")
def health() -> dict[str, str]: return {"status":"ok","version":"5.1.0","brand":"Zova"}

@app.get("/tiktokH8OfSOj6UphrBG5ccohezZ2qB7ZV5Oig.txt", response_class=HTMLResponse)
def tiktok_site_verification():
    return HTMLResponse("tiktok-developers-site-verification=H8OfSOj6UphrBG5ccohezZ2qB7ZV5Oig", media_type="text/plain")

@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    try: user = current_user(request)
    except HTTPException: user = None
    return templates.TemplateResponse(request, "landing.html", template_context(request, user))

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, error: str | None = None):
    import pycountry
    saved = {}
    try:
        saved=json.loads(decrypt(request.cookies.get("zova_signup_input","")))
        if saved.get("expires",0)<utcnow().timestamp(): saved={}
    except Exception: saved={}
    return templates.TemplateResponse(request, "auth.html", template_context(request, heading="Create your Zova account", subheading="Use your email to create a workspace. Connect your social accounts afterwards, or skip that step.", action="/signup", button="Create Zova account", saved=saved, countries=sorted(pycountry.countries,key=lambda c:c.name), error=error, apple_ready=apple_configured()))

@app.post("/signup")
def signup(request: Request, name: Annotated[str, Form()], email: Annotated[str, Form()], country: Annotated[str, Form()], password: Annotated[str, Form()], password_confirmation: Annotated[str, Form()], accept_terms: Annotated[str | None, Form()] = None, marketing_consent: Annotated[str | None, Form()] = None, db: Session=Depends(get_db)):
    def retry(location, status=303):
        response=RedirectResponse(location,status)
        response.set_cookie('zova_signup_input',encrypt(json.dumps({'name':name[:160],'email':email[:320],'country':country[:2],'expires':utcnow().timestamp()+600})),max_age=600,httponly=True,secure=base_url().startswith('https://'),samesite='lax',path='/signup')
        return response
    try:
        email, name, country = normalize_email(email), normalize_name(name), normalize_country(country)
    except ValueError as exc:
        return retry(f"/signup?error={quote_plus(str(exc))}", 303)
    if accept_terms != "yes": return retry("/signup?error=Please+accept+the+Terms+and+Privacy+Policy",303)
    if password != password_confirmation: return retry("/signup?error=Passwords+do+not+match",303)
    if not 10 <= len(password) <= 256: return retry("/signup?error=Use+a+password+of+at+least+10+characters",303)
    if db.scalar(select(User).where(User.email==email)): return retry("/signup?error=An+account+with+that+email+already+exists",303)
    now = utcnow()
    consent = marketing_consent == "yes"
    user=User(email=email,display_name=name,country_code=country,password_hash=hash_password(password),terms_accepted_at=now,marketing_consent=consent,marketing_consent_at=now if consent else None); db.add(user); db.commit(); db.refresh(user)
    db.info.update(brand_id=0,brand_user_id=user.id);request.state.brand_id=0
    get_preferences(db,user.id)
    readiness.event(user.id,'signup',user.id)
    resp=RedirectResponse("/onboarding/socials",303); set_user_cookie(resp,user); resp.delete_cookie("zova_brand",path="/"); resp.delete_cookie("zova_onboarding",path="/"); resp.delete_cookie("zova_signup_input",path="/signup"); return resp

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(request, "auth.html", template_context(request, heading="Welcome back", subheading="Sign in with your Zova email and password, not your social account password.", action="/login", button="Log in to Zova", error=error, login_next=safe_login_next(request.query_params.get("next")), apple_ready=apple_configured()))


def apple_configured() -> bool:
    return all(os.environ.get(k) for k in ("APPLE_CLIENT_ID", "APPLE_TEAM_ID", "APPLE_KEY_ID", "APPLE_PRIVATE_KEY"))


def apple_client_secret() -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    key = os.environ["APPLE_PRIVATE_KEY"].replace("\\n", "\n")
    return jwt.encode({"iss": os.environ["APPLE_TEAM_ID"], "iat": now, "exp": now + 300, "aud": "https://appleid.apple.com", "sub": os.environ["APPLE_CLIENT_ID"]}, key, algorithm="ES256", headers={"kid": os.environ["APPLE_KEY_ID"]})


@app.get("/auth/apple/start")
def apple_start(intent: str = "login", db: Session = Depends(get_db)):
    if not apple_configured(): raise HTTPException(503, "Sign in with Apple is not configured")
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(AuthState(provider="apple", state_hash=hash_api_key(state), nonce_hash=hash_api_key(nonce), intent="signup" if intent == "signup" else "login")); db.commit()
    params = httpx.QueryParams({"client_id": os.environ["APPLE_CLIENT_ID"], "redirect_uri": os.environ.get("APPLE_REDIRECT_URI", f"{base_url()}/auth/apple/callback"), "response_type": "code id_token", "response_mode": "form_post", "scope": "name email", "state": state, "nonce": nonce})
    return RedirectResponse(f"https://appleid.apple.com/auth/authorize?{params}", 302)


@app.post("/auth/apple/callback")
def apple_callback(code: Annotated[str | None, Form()] = None, id_token: Annotated[str | None, Form()] = None, state: Annotated[str | None, Form()] = None, error: Annotated[str | None, Form()] = None, user: Annotated[str | None, Form()] = None, db: Session = Depends(get_db)):
    if error or not code or not id_token or not state: return RedirectResponse("/login?error=Apple+sign-in+was+cancelled", 303)
    row = db.scalar(select(AuthState).where(AuthState.state_hash == hash_api_key(state), AuthState.provider == "apple", AuthState.used.is_(False)))
    if not row or row.created_at.replace(tzinfo=row.created_at.tzinfo or timezone.utc) < utcnow() - timedelta(minutes=10): raise HTTPException(400, "Invalid or expired Apple sign-in state")
    row.used = True; db.commit()
    token_response = httpx.post("https://appleid.apple.com/auth/token", data={"client_id": os.environ["APPLE_CLIENT_ID"], "client_secret": apple_client_secret(), "code": code, "grant_type": "authorization_code", "redirect_uri": os.environ.get("APPLE_REDIRECT_URI", f"{base_url()}/auth/apple/callback")}, timeout=30.0)
    if token_response.status_code >= 400: raise HTTPException(502, "Apple token exchange failed")
    jwks = jwt.PyJWKClient("https://appleid.apple.com/auth/keys")
    claims = jwt.decode(id_token, jwks.get_signing_key_from_jwt(id_token).key, algorithms=["RS256"], audience=os.environ["APPLE_CLIENT_ID"], issuer="https://appleid.apple.com")
    if hash_api_key(str(claims.get("nonce", ""))) != row.nonce_hash: raise HTTPException(400, "Invalid Apple sign-in nonce")
    subject, email = str(claims["sub"]), str(claims.get("email") or "").strip().lower()
    display_name = ""
    if user:
        try:
            apple_user = json.loads(user)
            apple_name = apple_user.get("name") or {}
            display_name = normalize_name(" ".join(filter(None, (apple_name.get("firstName"), apple_name.get("lastName")))))
        except (json.JSONDecodeError, TypeError, ValueError):
            display_name = ""
    identity = db.scalar(select(AuthIdentity).where(AuthIdentity.provider == "apple", AuthIdentity.subject == subject))
    user = db.get(User, identity.user_id) if identity else (db.scalar(select(User).where(User.email == email)) if email else None)
    created = user is None
    if created:
        now = utcnow()
        user = User(email=email or f"apple-{hash_api_key(subject)[:20]}@private.zova.invalid", display_name=display_name, password_hash=hash_password(secrets.token_urlsafe(48)), email_verified_at=now if claims.get("email_verified") in {True, "true"} else None, last_login_at=now, terms_accepted_at=now); db.add(user); db.commit(); db.refresh(user)
        db.info.update(brand_id=0,brand_user_id=user.id);request.state.brand_id=0
        get_preferences(db,user.id)
    else:
        if display_name and not user.display_name:
            user.display_name = display_name
        user.last_login_at = utcnow()
        db.commit()
    if not identity: db.add(AuthIdentity(user_id=user.id, provider="apple", subject=subject)); db.commit()
    if created:readiness.event(user.id,'signup',user.id)
    resp = RedirectResponse("/onboarding/socials" if created else "/studio", 303); set_user_cookie(resp, user); resp.delete_cookie("zova_brand",path="/"); resp.delete_cookie("zova_onboarding",path="/"); return resp

@app.post("/login")
def login(request: Request,email:Annotated[str,Form()],password:Annotated[str,Form()],next:Annotated[str,Form()]="/studio",db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==email.strip().lower()))
    destination=safe_login_next(next)
    if not user or not user.active or not verify_password(password,user.password_hash): return RedirectResponse("/login?error=Incorrect+email+or+password&next="+quote_plus(destination),303)
    user.last_login_at=utcnow(); db.commit()
    resp=RedirectResponse(destination,303); set_user_cookie(resp,user); resp.delete_cookie("zova_brand",path="/"); resp.delete_cookie("zova_onboarding",path="/"); return resp

@app.post("/logout")
def logout(request: Request):
    revoke_session(request.cookies.get("nova_session"))
    resp=RedirectResponse("/",303); resp.delete_cookie("nova_session",path="/"); resp.delete_cookie("zova_brand",path="/"); return resp

@app.get("/subscribe", response_class=HTMLResponse)
def subscribe(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    info=billing.summary(db,user)
    return templates.TemplateResponse(request,"membership.html",template_context(request,user,billing_info=info,usage=allowances.summary(db,user.id),catalog=allowances.PLANS,subscription_required=billing.require_subscription()))

@app.get('/brands', response_class=HTMLResponse)
def brand_settings(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    return templates.TemplateResponse(request,'brands.html',template_context(request,user))

@app.post('/brands')
def create_brand(request:Request,name:Annotated[str,Form()],db:Session=Depends(get_db)):
    from .db import Brand
    user=current_user(request)
    name=name.strip()
    if not name or len(name)>100:raise HTTPException(400,'Use a brand name between 1 and 100 characters.')
    allowances.brand_slot(db,user.id)
    row=Brand(user_id=user.id,name=name);db.add(row);db.commit();db.refresh(row)
    response=RedirectResponse('/studio',303)
    response.set_cookie('zova_brand',str(row.id),httponly=True,secure=base_url().startswith('https://'),samesite='lax',max_age=30*86400)
    return response

@app.post('/brands/switch')
def switch_brand(request:Request,brand_id:Annotated[int,Form()],db:Session=Depends(get_db)):
    from .db import Brand
    user=current_user(request)
    row=db.get(Brand,brand_id) if brand_id else None
    if brand_id and (not row or row.user_id!=user.id):raise HTTPException(404,'Brand workspace not found')
    response=RedirectResponse('/studio',303)
    response.set_cookie('zova_brand',str(brand_id),httponly=True,secure=base_url().startswith('https://'),samesite='lax',max_age=30*86400)
    return response

@app.post('/brands/{brand_id}/name')
def rename_brand(brand_id:int,request:Request,name:Annotated[str,Form()],db:Session=Depends(get_db)):
    from .db import Brand
    user=current_user(request);name=name.strip()
    if not name or len(name)>100:raise HTTPException(400,'Use a brand name between 1 and 100 characters.')
    if brand_id:
        row=db.get(Brand,brand_id)
        if not row or row.user_id!=user.id:raise HTTPException(404,'Brand workspace not found')
        row.name=name
    else:db.get(User,user.id).default_brand_name=name
    db.commit();return RedirectResponse('/brands',303)

@app.get("/billing/checkout")
def checkout_link(request:Request):
    current_user(request)
    if not billing.checkout_enabled():raise HTTPException(409,"Paid checkout is disabled during testing.")
    return RedirectResponse('/subscribe',303)

@app.post("/billing/checkout")
def billing_checkout(request:Request,plan:str=Form('monthly'),db:Session=Depends(get_db)):
    user=db.get(User,current_user(request).id)
    if not billing.checkout_enabled():raise HTTPException(409,"Checkout is disabled. Your current access is unchanged.")
    try:url=billing.create_checkout(db,user,base_url(),plan)
    except (RuntimeError,ValueError) as exc:
        db.rollback();return RedirectResponse('/subscribe?error='+quote_plus(str(exc)),303)
    return RedirectResponse(url,303)

@app.get("/billing/success")
def billing_success(request:Request,session_id:str=Query(...),db:Session=Depends(get_db)):
    user=db.get(User,current_user(request).id)
    if not allowed_request(f"billing-return:{user.id}",20,300):raise HTTPException(429,"Please wait before refreshing billing again.")
    try:billing.verify_return(db,user,session_id)
    except PermissionError:raise HTTPException(403,"Checkout session does not belong to this account")
    except ValueError:raise HTTPException(400,"Invalid checkout session")
    except RuntimeError:
        db.rollback();return RedirectResponse('/subscribe?pending=1',303)
    return RedirectResponse('/subscribe?returned=1',303)

@app.get("/billing/portal")
def portal_link(request:Request):
    current_user(request)
    return RedirectResponse('/subscribe',303)

@app.post("/billing/portal")
def billing_portal(request:Request,db:Session=Depends(get_db)):
    user=db.get(User,current_user(request).id)
    try:url=billing.create_portal(db,user,base_url())
    except (RuntimeError,ValueError) as exc:
        db.rollback();return RedirectResponse('/subscribe?error='+quote_plus(str(exc)),303)
    return RedirectResponse(url,303)

@app.post("/billing/refresh")
def billing_refresh(request:Request,db:Session=Depends(get_db)):
    user=db.get(User,current_user(request).id)
    try:billing.refresh(db,user)
    except RuntimeError:
        db.rollback();return RedirectResponse('/subscribe?pending=1',303)
    return RedirectResponse('/subscribe',303)

@app.post("/billing/webhook")
async def billing_webhook(request:Request,db:Session=Depends(get_db)):
    raw=await request.body()
    if not billing.verify_webhook(raw,request.headers.get('stripe-signature','')):raise HTTPException(400,"Invalid Stripe signature")
    try:
        event=json.loads(raw)
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(billing.apply_event,db,event)
    except (ValueError,TypeError):
        db.rollback();raise HTTPException(400,"Invalid Stripe event")
    except RuntimeError:
        db.rollback();raise HTTPException(503,"Billing sync unavailable; retry this event")
    return {'received':True}

@app.get("/security",response_class=HTMLResponse)
def security_page(request:Request):
    try:user=current_user(request)
    except HTTPException:user=None
    return templates.TemplateResponse(request, "security.html",template_context(request,user,contact_email=os.environ.get("PRIVACY_CONTACT_EMAIL","privacy@zova-social.com")))

@app.get("/privacy",response_class=HTMLResponse)
@app.get("/privacy-policy",response_class=HTMLResponse)
def privacy_policy(request:Request):
    try:user=current_user(request)
    except HTTPException:user=None
    return templates.TemplateResponse(request, "privacy.html",template_context(request,user,contact_email=os.environ.get("PRIVACY_CONTACT_EMAIL","privacy@zova-social.com"),legal_name=os.environ.get("LEGAL_ENTITY_NAME","Zova Social Limited")))

@app.get("/terms",response_class=HTMLResponse)
@app.get("/terms-of-service",response_class=HTMLResponse)
def terms_of_service(request:Request):
    try:user=current_user(request)
    except HTTPException:user=None
    return templates.TemplateResponse(request, "terms.html",template_context(request,user,contact_email=os.environ.get("LEGAL_CONTACT_EMAIL") or os.environ.get("PRIVACY_CONTACT_EMAIL","legal@zova-social.com"),legal_name=os.environ.get("LEGAL_ENTITY_NAME","Zova Social Limited")))

@app.get("/refunds",response_class=HTMLResponse)
@app.get("/refund-policy",response_class=HTMLResponse)
def refund_policy(request:Request):
    try:user=current_user(request)
    except HTTPException:user=None
    return templates.TemplateResponse(request, "refunds.html",template_context(request,user,contact_email=os.environ.get("REFUND_CONTACT_EMAIL") or os.environ.get("BILLING_CONTACT_EMAIL","billing@zova-social.com"),legal_name=os.environ.get("LEGAL_ENTITY_NAME","Zova Social Limited")))

@app.get("/data-deletion",response_class=HTMLResponse)
def data_deletion_instructions(request:Request):
    try:user=current_user(request)
    except HTTPException:user=None
    return templates.TemplateResponse(request, "data_deletion.html",template_context(request,user,contact_email=os.environ.get("PRIVACY_CONTACT_EMAIL","privacy@zova-social.com")))

@app.post("/data-deletion/callback")
async def meta_data_deletion_callback(request:Request,db:Session=Depends(get_db)):
    form=await request.form(); signed=str(form.get("signed_request") or "")
    try:
        encoded_sig,encoded_payload=signed.split(".",1)
        decode=lambda value:base64.urlsafe_b64decode(value+"="*(-len(value)%4))
        payload=json.loads(decode(encoded_payload))
        secrets_to_try=[value.encode() for value in (os.environ.get("INSTAGRAM_APP_SECRET"),os.environ.get("META_APP_SECRET")) if value]
        supplied=decode(encoded_sig)
        if not secrets_to_try or not any(hmac.compare_digest(supplied,hmac.new(secret,encoded_payload.encode(),hashlib.sha256).digest()) for secret in secrets_to_try):raise ValueError("signature")
        external_id=str(payload.get("user_id") or "")
        if not external_id:raise ValueError("user")
    except Exception:raise HTTPException(400,"Invalid deletion request")
    rows=db.scalars(select(SocialConnection).where(SocialConnection.account_id==external_id,SocialConnection.platform.in_(("instagram","facebook")))).all()
    for row in rows:
        row.active=False;row.encrypted_access_token="";row.encrypted_refresh_token=None
    confirmation=secrets.token_urlsafe(24)
    db.add(DeletionRequest(code=confirmation,subject_hash=hash_api_key(external_id),status="connection_removed"))
    db.commit()
    return {"url":f"{base_url()}/data-deletion/status/{confirmation}","confirmation_code":confirmation}

@app.get("/data-deletion/status/{confirmation_code}",response_class=HTMLResponse)
def data_deletion_status(request:Request,confirmation_code:str,db:Session=Depends(get_db)):
    row=db.get(DeletionRequest,confirmation_code)
    if not row: raise HTTPException(404,"Deletion request not found")
    return templates.TemplateResponse(request, "data_deletion_status.html",template_context(request,None,confirmation_code=row.code,deletion=row))

@app.get("/studio",response_class=HTMLResponse)
def studio(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    readiness.event(user.id,'visit',utcnow().strftime('%Y-%m-%d'))
    connections={}
    for row in db.scalars(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.active.is_(True))).all():
        connections.setdefault(row.platform,[]).append(row.username or row.account_id or "Connected account")
    return templates.TemplateResponse(request, "studio.html",template_context(request,user,subscription_blocked=not billing.has_access(user),studio_connections=connections,studio_prefs=get_preferences(db,user.id)))

@app.get("/drafts",response_class=HTMLResponse)
def drafts_page(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    query=request.query_params.get("q","").strip()[:200]
    statement=select(Draft).where(Draft.user_id==user.id)
    if query:statement=statement.where(or_(Draft.brief.icontains(query,autoescape=True),Draft.variants_json.icontains(query,autoescape=True),Draft.workspace_json.icontains(query,autoescape=True)))
    try:page=max(1,min(10000,int(request.query_params.get('page','1'))))
    except ValueError:page=1
    rows=db.scalars(statement.order_by(Draft.updated_at.desc(),Draft.id.desc()).offset((page-1)*30).limit(31)).all()
    has_more=len(rows)>30
    rows=rows[:30]
    drafts=[]
    for row in rows:
        try:platforms=json.loads(row.platforms_json or "[]")
        except (TypeError,json.JSONDecodeError):platforms=[]
        drafts.append({"id":row.id,"brief":row.brief,"platforms":platforms,"status":row.status,"created_at":row.created_at,"updated_at":row.updated_at})
    return templates.TemplateResponse(request, "drafts.html",template_context(request,user,drafts=drafts,page=page,has_more=has_more))

@app.get("/analytics",response_class=HTMLResponse)
def analytics_page(request:Request):
    user=current_user(request)
    return templates.TemplateResponse(request, "analytics.html",template_context(request,user))

@app.get("/onboarding/socials", response_class=HTMLResponse)
def onboarding_socials(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    rows = db.scalars(select(SocialConnection).where(SocialConnection.user_id == user.id, SocialConnection.active.is_(True))).all()
    by = {}
    for row in rows: by.setdefault(row.platform, []).append(row)
    response = templates.TemplateResponse(request, "onboarding_socials.html", template_context(request, user, by_platform=by))
    response.set_cookie("zova_onboarding", str(user.id), max_age=1800, httponly=True, secure=base_url().startswith("https://"), samesite="lax", path="/")
    return response

@app.get("/onboarding/writing-style", response_class=HTMLResponse)
def onboarding_writing_style(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    connected = db.scalar(select(SocialConnection.id).where(SocialConnection.user_id == user.id, SocialConnection.active.is_(True)).limit(1)) is not None
    return templates.TemplateResponse(request, "onboarding_writing.html", template_context(request, user, prefs=get_preferences(db, user.id), connected=connected))

@app.get("/onboarding/complete")
def onboarding_complete(request: Request):
    current_user(request)
    response = RedirectResponse("/studio", 303); response.delete_cookie("zova_onboarding", path="/"); return response

@app.get("/account",response_class=HTMLResponse)
def account(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); prefs=get_preferences(db,user.id); rows=db.scalars(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc())).all(); by={}
    for r in rows: by.setdefault(r.platform,[]).append(r)
    response=templates.TemplateResponse(request, "account.html",template_context(request,user,prefs=prefs,by_platform=by,billing_ready=billing.configured()))
    response.delete_cookie("zova_onboarding",path="/")
    return response


def require_admin(request: Request) -> User:
    """Return the signed-in administrator without revealing this page to other users."""
    try:
        user = current_user(request)
    except HTTPException:
        raise HTTPException(404, "Not found")
    allowed = {email.strip().lower() for email in os.environ.get("ADMIN_EMAILS", "").split(",") if email.strip()}
    if user.email.lower() not in allowed:
        raise HTTPException(404, "Not found")
    return user


@app.get("/admin/users", response_class=HTMLResponse, include_in_schema=False)
def admin_users(request: Request, q: str = "", subscription: str = "", country: str = "", page: int = 1, db: Session = Depends(get_db)):
    admin = require_admin(request)
    page, page_size = max(page, 1), 50
    query = select(User)
    search = q.strip()[:160]
    if search:
        like = f"%{search}%"
        query = query.where(or_(User.email.ilike(like), User.display_name.ilike(like)))
    if subscription:
        query = query.where(User.subscription_status == subscription[:40])
    country_code = country.strip().upper()[:2]
    if country_code:
        query = query.where(User.country_code == country_code)
    filtered = query.subquery()
    total = db.scalar(select(func.count()).select_from(filtered)) or 0
    users = db.scalars(query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    summary = {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "active": db.scalar(select(func.count(User.id)).where(User.active.is_(True))) or 0,
        "subscribers": db.scalar(select(func.count(User.id)).where(User.subscription_status.in_(("active", "trialing")))) or 0,
        "marketing": db.scalar(select(func.count(User.id)).where(User.marketing_consent.is_(True))) or 0,
    }
    statuses = db.scalars(select(User.subscription_status).distinct().order_by(User.subscription_status)).all()
    countries = db.scalars(select(User.country_code).where(User.country_code != "").distinct().order_by(User.country_code)).all()
    return templates.TemplateResponse(request, "admin_users.html", template_context(request, admin, users=users, summary=summary, statuses=statuses, countries=countries, total=total, page=page, page_size=page_size, q=search, subscription=subscription, country=country_code))

@app.post("/account/preferences")
def save_preferences(request:Request,writing_tone:Annotated[str,Form()]="",audience:Annotated[str,Form()]="",topics:Annotated[str,Form()]="",things_to_avoid:Annotated[str,Form()]="",example_posts:Annotated[str,Form()]="",preferred_post_length:Annotated[int,Form()]=220,timezone_name:Annotated[str,Form(alias="timezone")]="Europe/London",next_url:Annotated[str,Form(alias="next")]="",db:Session=Depends(get_db)):
    user=current_user(request); prefs=get_preferences(db,user.id)
    try:ZoneInfo(timezone_name)
    except Exception:timezone_name="Europe/London"
    prefs.writing_tone=writing_tone[:5000]; prefs.audience=audience[:5000]; prefs.topics=topics[:5000]; prefs.things_to_avoid=things_to_avoid[:5000]; prefs.example_posts=example_posts[:12000]; prefs.preferred_post_length=max(30,min(preferred_post_length,4000)); prefs.timezone=timezone_name; db.commit(); return RedirectResponse("/onboarding/complete" if next_url == "/onboarding/complete" else "/account",303)

@app.post("/account/profile")
async def update_profile(request: Request, display_name: Annotated[str, Form()] = "", guidance: Annotated[str | None, Form()] = None, next_url: Annotated[str, Form(alias="next")] = "", db: Session = Depends(get_db)):
    user = db.get(User, current_user(request).id); prefs = get_preferences(db, user.id)
    try: user.display_name = normalize_name(display_name)
    except ValueError: return RedirectResponse("/account?error=profile", 303)
    profile_form=await request.form()
    if 'guidance' in profile_form: prefs.things_to_avoid = str(profile_form['guidance']).strip()[:5000]
    db.commit(); return RedirectResponse("/onboarding/complete" if next_url == "/onboarding/complete" else "/account?saved=profile", 303)

@app.post("/account/password")
def change_password(request: Request, current_password: Annotated[str, Form()], new_password: Annotated[str, Form()], new_password_confirmation: Annotated[str, Form()], db: Session = Depends(get_db)):
    user = db.get(User, current_user(request).id)
    if not verify_password(current_password, user.password_hash): return RedirectResponse("/account?error=current_password", 303)
    if not 10 <= len(new_password) <= 256: return RedirectResponse("/account?error=password_length", 303)
    if new_password != new_password_confirmation: return RedirectResponse("/account?error=password_match", 303)
    user.password_hash = hash_password(new_password)
    user.auth_version += 1
    db.commit()
    response = RedirectResponse("/account?saved=password", 303)
    set_user_cookie(response, user)
    return response

@app.post("/api/voice/scan-socials")
def scan_social_voice(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    try: profile = learn_voice_from_socials(db, user.id)
    except Exception as exc: log.exception("Social voice scan failed"); raise HTTPException(502, f"Zova could not scan recent posts: {exc}") from exc
    if not profile: return {"status": "waiting", "message": "Connect a social account so Zova can learn from recent posts."}
    return {"status": "learned", **profile}

@app.post("/account/connections/{connection_id}/unlink")
def unlink(connection_id:int,request:Request,db:Session=Depends(get_db)):
    user=current_user(request); conn=db.get(SocialConnection,connection_id)
    if not conn or conn.user_id!=user.id: raise HTTPException(404,"Connection not found")
    conn.active=False; conn.encrypted_access_token=""; conn.encrypted_refresh_token=None; db.commit(); return RedirectResponse("/account",303)


# ---------- OAuth connections ----------
@app.get("/connect/{platform}", response_class=HTMLResponse)
def connect_platform(platform: str, request: Request):
    user = current_user(request)
    options = connection_options()
    if platform not in options:
        raise HTTPException(404, "Unknown social platform")
    return templates.TemplateResponse(request, "connect.html", template_context(request, user, platform=platform, connection=options[platform]))


def connection_return(request: Request, platform: str, outcome: str = "connected"):
    destination = "/onboarding/socials" if request.cookies.get("zova_onboarding")==str(current_user(request).id) else "/account"
    return RedirectResponse(f"{destination}?{outcome}={platform}", 303)


def connection_state(db: Session, request: Request, state: str, platform: str):
    # Bind authorisation to the same signed-in Zova workspace that started it.
    user = current_user(request)
    owner = db.scalar(select(OAuthState.user_id).where(OAuthState.state_hash == hash_api_key(state), OAuthState.platform == platform))
    if owner != user.id:
        raise HTTPException(400, "Return to the Zova workspace where you started connecting and try again.")
    row=_state_row(db,state,platform)
    db.info.update(brand_id=row.brand_id,brand_user_id=user.id)
    request.state.brand_id=row.brand_id
    return row


def ensure_connection_ready(request: Request, platform: str):
    if not connection_options()[platform]["ready"]:
        return RedirectResponse(f"/connect/{platform}?error=unavailable", 303)
    return None


@app.get("/oauth/x/start")
def oauth_x_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    if unavailable := ensure_connection_ready(request,"x"): return unavailable
    verifier=secrets.token_urlsafe(64); state=_new_state(db,user.id,"x",verifier); return RedirectResponse(x_authorize_url(state,verifier),302)

@app.get("/callback/x")
@app.get("/oauth/x/callback")
def oauth_x_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    if error:return connection_return(request,"x","cancelled")
    if not code or not state:raise HTTPException(400,"Missing OAuth code or state")
    row=connection_state(db,request,state,"x"); verifier=decrypt(row.encrypted_code_verifier) if row.encrypted_code_verifier else ""
    try:token,user_info=x_exchange(code,verifier)
    except (RuntimeError, httpx.HTTPError):return connection_return(request,"x","connection_failed")
    from .connection_review import stage
    return stage(db,request,row,'x',[dict(platform="x",account_id=str(user_info["id"]),username=user_info.get("username","") or "",display_name=user_info.get("name","") or "",access=token["access_token"],refresh=token.get("refresh_token"),expires_in=token.get("expires_in"),scope=token.get("scope",X_SCOPES),metadata={"profile_image_url":user_info.get("profile_image_url")})])

@app.get("/oauth/meta/start")
def oauth_meta_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    if unavailable := ensure_connection_ready(request,"facebook"): return unavailable
    state=_new_state(db,user.id,"meta"); return RedirectResponse(meta_authorize_url(state),302)

@app.get("/oauth/instagram/facebook/start")
def oauth_instagram_facebook_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    if not connection_options()["instagram"]["facebook_ready"]:
        return RedirectResponse("/connect/instagram?error=facebook_unavailable",303)
    state=_new_state(db,user.id,"instagram_facebook")
    return RedirectResponse(meta_authorize_url(state,include_instagram=True),302)

@app.get("/oauth/meta/callback")
def oauth_meta_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    # The stored, unguessable state chooses the intent, never an arbitrary query parameter.
    state_platform=db.scalar(select(OAuthState.platform).where(OAuthState.state_hash==hash_api_key(state))) if state else None
    instagram_intent=state_platform=="instagram_facebook"
    target="instagram" if instagram_intent else "facebook"
    if error:return connection_return(request,target,"cancelled")
    if not code or not state:raise HTTPException(400,"Missing Meta OAuth code or state")
    row=connection_state(db,request,state,"instagram_facebook" if instagram_intent else "meta")
    try:pages=meta_exchange(code,include_instagram=True) if instagram_intent else meta_exchange(code)
    except (RuntimeError, httpx.HTTPError):return connection_return(request,target,"connection_failed")
    pages=[page for page in pages if page.get("id") and page.get("access_token")]
    if instagram_intent:
        pages=[page for page in pages if (page.get("instagram_business_account") or {}).get("id")]
    if not pages:return connection_return(request,target,"no_pages")
    candidates=[]
    for page in pages:
        if not page.get('access_token') or not page.get('id'):continue
        if instagram_intent:
            ig=page['instagram_business_account']
            candidates.append(dict(platform='instagram',account_id=str(ig['id']),username=ig.get('username','') or '',display_name=ig.get('name','') or ig.get('username','') or '',access=page['access_token'],scope=INSTAGRAM_FACEBOOK_SCOPES,metadata={'auth_provider':'facebook_login','facebook_page_id':str(page['id']),'profile_picture_url':ig.get('profile_picture_url')}))
        else:
            candidates.append(dict(platform='facebook',account_id=str(page['id']),username='',display_name=page.get('name',''),access=page['access_token'],scope=META_SCOPES,metadata={'tasks':page.get('tasks',[])}))
    from .connection_review import stage
    if not candidates:return connection_return(request,target,'no_pages')
    return stage(db,request,row,target,candidates)

@app.get("/oauth/instagram/start")
def oauth_instagram_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    if not connection_options()["instagram"]["direct_ready"]:
        return RedirectResponse("/connect/instagram?error=unavailable",303)
    try:url=instagram_authorize_url(_new_state(db,user.id,"instagram"))
    except RuntimeError: return RedirectResponse("/connect/instagram?error=unavailable",303)
    return RedirectResponse(url,302)

@app.get("/oauth/instagram/callback")
def oauth_instagram_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,error_description:str|None=None,db:Session=Depends(get_db)):
    if error:return connection_return(request,"instagram","cancelled")
    if not code or not state:raise HTTPException(400,"Missing Instagram OAuth code or state")
    row=connection_state(db,request,state,"instagram")
    try:result=instagram_exchange(code)
    except (RuntimeError, httpx.HTTPError):
        log.warning("Direct Instagram connection failed")
        return connection_return(request,"instagram","connection_failed")
    profile=result["profile"]
    from .connection_review import stage
    return stage(db,request,row,'instagram',[dict(platform="instagram",account_id=str(profile["id"]),username=profile.get("username","") or "",display_name=profile.get("name","") or profile.get("username","") or "",access=result["access_token"],expires_in=result.get("expires_in"),scope=os.environ.get("INSTAGRAM_SCOPES",INSTAGRAM_SCOPES),metadata={"auth_provider":"instagram_login","profile_picture_url":profile.get("profile_picture_url")})])
@app.get("/oauth/tiktok/start")
def oauth_tiktok_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    if unavailable := ensure_connection_ready(request,"tiktok"): return unavailable
    state=_new_state(db,user.id,"tiktok"); return RedirectResponse(tiktok_authorize_url(state),302)

@app.get("/oauth/tiktok/callback")
def oauth_tiktok_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    if error:return connection_return(request,"tiktok","cancelled")
    if not code or not state:raise HTTPException(400,"Missing TikTok OAuth code or state")
    row=connection_state(db,request,state,"tiktok")
    try:token,info=tiktok_exchange(code)
    except (RuntimeError, httpx.HTTPError):return connection_return(request,"tiktok","connection_failed")
    from .connection_review import stage
    return stage(db,request,row,'tiktok',[dict(platform="tiktok",account_id=str(info.get("open_id")),username="",display_name=info.get("display_name","") or "",access=token["access_token"],refresh=token.get("refresh_token"),expires_in=token.get("expires_in"),scope=token.get("scope",TIKTOK_SCOPES),metadata={"avatar_url":info.get("avatar_url")})])


# ---------- API models ----------
class GenerateRequest(BaseModel):
    media_asset_ids:list[int]=Field(default_factory=list,max_length=10)
    brief:str=Field(min_length=1,max_length=12000); instruction:str=Field(default="",max_length=5000); platforms:list[str]; thread_length:int=1; link_url:str=""; draft_id:int|None=None
    @field_validator("thread_length")
    @classmethod
    def valid_thread(cls,v:int): return v if v in {1,3,5} else 1
class RewriteRequest(BaseModel):
    media_asset_ids:list[int]=Field(default_factory=list,max_length=10)
    platform:str; posts:list[str]; action:str=""; instruction:str=Field(default="",max_length=1000)
class ScheduleSuggestRequest(BaseModel): platforms:list[str]; context:str=""
class InsightRequest(BaseModel): question:str=Field(min_length=1,max_length=2000)
class ConversationRequest(BaseModel):
    media_asset_ids:list[int]=Field(default_factory=list,max_length=10)
    message:str=Field(min_length=1,max_length=12000)
    draft_id:int|None=None
    selected_platforms:list[str]=Field(default_factory=list,max_length=4)
    active_platform:str='x'
    recent_messages:list[dict[str,str]]=Field(default_factory=list,max_length=12)

@app.post('/api/conversation/plan')
def conversation_plan(body:ConversationRequest,request:Request,db:Session=Depends(get_db)):
    from .conversation import plan_message
    from .workspace import EDITABLE
    user=current_user(request);subscription_guard(user)
    context={'selected_platforms':body.selected_platforms,'active_platform':body.active_platform,'conversation':body.recent_messages}
    if body.draft_id:
        row=db.get(Draft,body.draft_id)
        if not row or row.user_id!=user.id:raise HTTPException(404,'Draft not found')
        context.update(brief=row.brief,variants=json.loads(row.variants_json),status=row.status)
        if row.status not in EDITABLE:
            return {'action':'answer','platforms':[],'reply':'This item is already submitted. Start a new chat for another post.'}
    from .media_inspection import inspect_assets
    from .readiness import ai_user
    ai_context=ai_user.set(user.id)
    try:
        inspected=inspect_assets(db,user.id,body.media_asset_ids)
        db.commit()
        context['attachment_observations']=inspected
        try:
            result=plan_message(body.message,context).model_dump()
            result['media_inspection']=inspected
            return result
        except Exception:raise HTTPException(502,'I could not interpret that request. Your draft is unchanged; please try again.')
    finally:
        ai_user.reset(ai_context)

class VoiceLearnRequest(BaseModel): content:str=Field(min_length=80,max_length=30000)
class PreviewRequest(BaseModel): platforms:list[str]; variants:dict[str,Any]
class PublishRequest(BaseModel):
    draft_id:int|None=None
    platforms:list[str]
    variants:dict[str,Any]
    media_asset_ids:list[int]=[]
    link_url:str=""
    publish_options:dict[str,Any]={}
    review_token:str|None=None
    connection_ids:dict[str,int]={}
class ReviewRequest(PublishRequest): scheduled_local:str|None=None
class ScheduleRequest(PublishRequest): scheduled_local:str
class DraftSaveRequest(BaseModel):
    brief:str=Field(default="",max_length=12000)
    instruction:str=Field(default="",max_length=5000)
    platforms:list[str]=[]
    variants:dict[str,Any]={}
    thread_length:int=1
    workspace:dict[str,Any]|None=None
    revision:int|None=None
class LegacyPostRequest(BaseModel):
    text:str=Field(min_length=1,max_length=280); approved:bool=False


@app.post("/api/voice/learn")
def learn_voice(payload: VoiceLearnRequest, request: Request, db: Session = Depends(get_db)):
    with allowances.ai_action(db,current_user(request).id):
        user = current_user(request)
        try:
            profile = ai.infer_voice_profile(payload.content)
        except Exception as exc:
            log.exception("Voice learning failed")
            raise HTTPException(502, f"Zova could not analyse that sample: {exc}") from exc
        prefs = get_preferences(db, user.id)
        prefs.writing_tone = profile["writing_tone"][:5000]
        prefs.audience = profile["audience"][:5000]
        prefs.topics = profile["topics"][:5000]
        prefs.things_to_avoid = profile["things_to_avoid"][:5000]
        prefs.example_posts = payload.content[:12000]
        prefs.preferred_post_length = profile["preferred_post_length"]
        db.commit()
        return profile


def _validate_platforms(values:list[str])->list[str]:
    allowed=[p for p in values if p in {"x","instagram","facebook","tiktok"}]
    if not allowed:raise HTTPException(400,"Choose at least one supported platform")
    return list(dict.fromkeys(allowed))

def _user_assets(db:Session,user_id:int,ids:list[int])->list[MediaAsset]:
    assets=[]
    for value in ids[:10]:
        row=db.get(MediaAsset,int(value))
        if row and row.user_id==user_id:assets.append(row)
    return assets

def _validate_media_targets(platforms:list[str],assets:list[MediaAsset])->None:
    videos=[asset for asset in assets if asset.mime_type.startswith("video/")]
    if not videos:return
    if len(videos)>1 or len(assets)>1:
        raise HTTPException(400,"Add one video per post and do not mix video with images")
    unsupported=[p for p in platforms if p not in {"instagram","tiktok"}]
    if unsupported:
        names=["X" if p=="x" else p.title() for p in unsupported]
        raise HTTPException(400,f"Videos can only be published to Instagram and TikTok. Remove {', '.join(names)}.")


@app.post("/api/media")
async def upload_media(request:Request,files:list[UploadFile]=File(...),db:Session=Depends(get_db)):
    from .media_safety import validated_upload, VIDEO_TYPES
    user=current_user(request); subscription_guard(user)
    if not 1 <= len(files) <= 10: raise HTTPException(400,"Choose between one and ten files.")
    if any((f.content_type or '').startswith('video/') for f in files) and len(files)!=1:
        raise HTTPException(400,"Add one video per post and do not mix video with images")
    validated=[await validated_upload(file) for file in files]
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    used=db.scalar(select(func.coalesce(func.sum(MediaAsset.size_bytes),0)).where(MediaAsset.user_id==user.id))
    if used+sum(len(data) for data,mime in validated)>500*1024*1024:
        raise HTTPException(413,"Your media storage limit has been reached. Contact support to manage older uploads.")
    result=[]
    for file,(data,mime) in zip(files,validated):
        stored=save_bytes(data,file.filename or 'media',mime,base_url())
        row=MediaAsset(user_id=user.id,filename=(file.filename or 'media')[:260],mime_type=mime,storage_key=stored.storage_key,public_url=stored.public_url,size_bytes=len(data))
        db.add(row); db.flush()
        result.append({'id':row.id,'filename':row.filename,'kind':'video' if mime in VIDEO_TYPES else 'image','mime_type':mime,'url':stored.public_url or f'/media/preview/{row.id}'})
    db.commit()
    return {'assets':result}

@app.get("/media/raw/{filename}")
def local_media(filename:str):
    safe=Path(filename).name; path=UPLOAD_DIR/safe
    if not path.exists():raise HTTPException(404,"Media not found")
    return FileResponse(path, headers={"X-Content-Type-Options":"nosniff","Content-Security-Policy":"sandbox; default-src 'none'"})

@app.post("/api/ai/generate")
def api_generate(body:GenerateRequest,request:Request,db:Session=Depends(get_db)):
    with allowances.ai_action(db,current_user(request).id):
        from .workspace import EDITABLE
        user=current_user(request); subscription_guard(user); platforms=_validate_platforms(body.platforms); prefs=get_preferences(db,user.id)
        row=db.get(Draft,body.draft_id) if body.draft_id else None
        if body.draft_id and (not row or row.user_id!=user.id):raise HTTPException(404,'Draft not found')
        if row and row.status not in EDITABLE:raise HTTPException(409,'This draft is already submitted.')
        revision=row.revision if row else 0
        from .media_inspection import inspect_assets, context as media_context
        inspected=inspect_assets(db,user.id,body.media_asset_ids)
        try:variants=ai.generate_variants(brief=body.brief,instruction=body.instruction+media_context(inspected),platforms=platforms,thread_length=body.thread_length,preferences=prefs,link_url=body.link_url)
        except Exception:raise HTTPException(502,'Content generation failed. Your previous draft is unchanged; try again.')
        if row:
            existing=json.loads(row.variants_json or '{}');existing.update(variants);variants=existing
            all_platforms=list(dict.fromkeys(json.loads(row.platforms_json or '[]')+platforms))
            claimed=db.execute(update(Draft).where(Draft.id==row.id,Draft.revision==revision,Draft.status.in_(EDITABLE)).values(brief=body.brief,instruction=body.instruction,platforms_json=json.dumps(all_platforms),variants_json=json.dumps(variants,ensure_ascii=False),thread_length=body.thread_length,revision=Draft.revision+1,updated_at=utcnow()).execution_options(synchronize_session=False))
            if claimed.rowcount!=1:db.rollback();raise HTTPException(409,'This draft changed while generating. Open the latest saved version.')
            db.commit();db.refresh(row)
        else:
            row=Draft(user_id=user.id,brief=body.brief,instruction=body.instruction,platforms_json=json.dumps(platforms),variants_json=json.dumps(variants,ensure_ascii=False),thread_length=body.thread_length)
            db.add(row);db.commit();db.refresh(row)
        readiness.event(user.id,'generated',row.id)
        return {'draft_id':row.id,'variants':variants,'saved':True,'revision':row.revision}


@app.post("/api/ai/rewrite")
def api_rewrite(body:RewriteRequest,request:Request,db:Session=Depends(get_db)):
    with allowances.ai_action(db,current_user(request).id):
        user=current_user(request);subscription_guard(user);prefs=get_preferences(db,user.id)
        from .media_inspection import inspect_assets, context as media_context
        inspected=inspect_assets(db,user.id,body.media_asset_ids)
        try:posts=ai.rewrite_variant(platform=body.platform,posts=body.posts,action=body.action,instruction=body.instruction+media_context(inspected),preferences=prefs)
        except RuntimeError as exc:raise HTTPException(502,str(exc))
        db.commit()
        return {"posts":posts}


@app.post("/api/ai/schedule")
def api_schedule_suggest(body:ScheduleSuggestRequest,request:Request,db:Session=Depends(get_db)):
    with allowances.ai_action(db,current_user(request).id):
        user=current_user(request);subscription_guard(user);prefs=get_preferences(db,user.id);platforms=_validate_platforms(body.platforms)
        try:s=ai.propose_schedule(platforms=platforms,timezone_name=prefs.timezone,context=body.context)
        except RuntimeError as exc:raise HTTPException(502,str(exc))
        return {"timezone":prefs.timezone,"suggestions":s,"note":"Suggested starting points, not recommendations based on your account performance."}


@app.post("/api/preview")
def api_preview(body:PreviewRequest,request:Request):
    user=current_user(request); subscription_guard(user); platforms=_validate_platforms(body.platforms); problems=[]
    for p in platforms:
        posts=((body.variants.get(p) or {}).get("posts") or [])
        if not posts:problems.append(f"{p}: no draft")
        if p=="x" and any(len(str(x))>280 for x in posts):problems.append("X: one or more posts exceed 280 characters")
    if problems:raise HTTPException(400,"; ".join(problems))
    return {"valid":True,"summary":f"Ready for {', '.join(platforms)}. Nothing has been published."}

@app.post("/api/publish-context")
def api_publish_context(body:PreviewRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);subscription_guard(user);platforms=_validate_platforms(body.platforms);contexts={}
    for platform in platforms:
        try:
            contexts[platform]=publishing_context(db,user.id,platform)
            contexts[platform]['accounts']=[{'id':c.id,'account_id':c.account_id,'name':c.display_name or c.username or c.account_id} for c in db.scalars(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.platform==platform,SocialConnection.active.is_(True))).all()]
        except RuntimeError as exc:contexts[platform]={"platform":platform,"error":"Account publishing settings are unavailable. Check the connection and try again."}
    return {"platforms":contexts}

@app.post('/api/publish-review')
def api_publish_review(body:ReviewRequest,request:Request,db:Session=Depends(get_db)):
    from .publishing_workflow import prepare_review
    user=current_user(request);subscription_guard(user)
    return prepare_review(db,user.id,body)

@app.post('/api/publish')
def api_publish(body:PublishRequest,request:Request,db:Session=Depends(get_db)):
    from .publishing_workflow import confirm_review
    user=current_user(request);subscription_guard(user)
    return confirm_review(db,user.id,body,'publish',publish_platform)

@app.post('/api/schedule')
def api_schedule(body:ScheduleRequest,request:Request,db:Session=Depends(get_db)):
    from .publishing_workflow import confirm_review
    user=current_user(request);subscription_guard(user)
    return confirm_review(db,user.id,body,'schedule',publish_platform)

@app.post("/api/drafts")
def api_create_draft(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); subscription_guard(user)
    row=Draft(user_id=user.id)
    db.add(row);db.commit();db.refresh(row)
    return {"id":row.id,"revision":row.revision}

@app.get("/api/drafts")
def api_drafts(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    query=request.query_params.get("q","").strip()[:200]
    statement=select(Draft).where(Draft.user_id==user.id)
    if query:statement=statement.where(or_(Draft.brief.icontains(query,autoescape=True),Draft.variants_json.icontains(query,autoescape=True),Draft.workspace_json.icontains(query,autoescape=True)))
    rows=db.scalars(statement.order_by(Draft.updated_at.desc(),Draft.id.desc()).limit(100)).all()
    output=[]
    for r in rows:
        acts=db.scalars(select(Activity).where(Activity.user_id==user.id,Activity.draft_id==r.id,Activity.url.is_not(None)).order_by(Activity.id.desc())).all()
        workspace=json.loads(r.workspace_json or "{}")
        title=r.brief or next((m.get("content", "") for m in workspace.get("conversation", []) if m.get("role")=="user"), "") or workspace.get("composer", "") or "Untitled conversation"
        output.append({"id":r.id,"title":title[:100],"brief":r.brief,"platforms":json.loads(r.platforms_json or "[]"),"status":r.status,"created_at":r.created_at.isoformat(),"updated_at":r.updated_at.isoformat(),"links":[{"platform":a.platform,"url":a.url} for a in acts if a.url]})
    return output

@app.get("/api/drafts/{draft_id}")
def api_draft(draft_id:int,request:Request,db:Session=Depends(get_db)):
    user=current_user(request); row=db.get(Draft,draft_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,"Draft not found")
    return {"id":row.id,"brief":row.brief,"instruction":row.instruction,"revision":row.revision,"workspace":json.loads(row.workspace_json or "{}"),"platforms":json.loads(row.platforms_json or "[]"),"variants":json.loads(row.variants_json or "{}"),"thread_length":row.thread_length,"status":row.status,"created_at":row.created_at.isoformat(),"updated_at":row.updated_at.isoformat()}

@app.patch("/api/drafts/{draft_id}")
def api_save_draft(draft_id:int,body:DraftSaveRequest,request:Request,db:Session=Depends(get_db)):
    from .workspace import save_workspace
    user=current_user(request)
    result=save_workspace(db,db.get(Draft,draft_id),body,user.id)
    readiness.event(user.id,'revised',f"{draft_id}:{result.get('revision',0)}")
    return result

@app.delete("/api/drafts/{draft_id}",status_code=204)
def api_delete_draft(draft_id:int,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);row=db.get(Draft,draft_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,"Draft not found")
    if row.status not in {"draft","failed","cancelled"}:raise HTTPException(409,"Published or scheduled drafts are retained in your history")
    from .workspace import delete_unsubmitted_draft
    delete_unsubmitted_draft(db,row);return Response(status_code=204)

@app.post("/drafts/{draft_id}/delete")
def delete_draft_page(draft_id:int,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);row=db.get(Draft,draft_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,"Draft not found")
    if row.status not in {"draft","failed","cancelled"}:return RedirectResponse("/drafts?error=Published+and+scheduled+items+remain+in+your+history",303)
    from .workspace import delete_unsubmitted_draft
    try:delete_unsubmitted_draft(db,row)
    except HTTPException:return RedirectResponse("/drafts?error=This+draft+has+delivery+records+and+is+retained",303)
    return RedirectResponse("/drafts?deleted=1",303)

@app.get("/api/activity")
def api_activity(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); rows=db.scalars(select(Activity).where(Activity.user_id==user.id).order_by(Activity.id.desc()).limit(20)).all()
    conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.platform=="tiktok",SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc()))
    if conn:
        for row in rows:
            if row.platform=="tiktok" and row.status in {"pending","processing"} and row.platform_post_id:
                try:
                    state=resolve_tiktok_post(db,conn,row.platform_post_id); remote=str(state.get("status") or "").upper()
                    if remote=="PUBLISH_COMPLETE":row.status="published"
                    elif remote in {"FAILED","PUBLISH_FAILED"}:row.status="failed";row.error=state.get("fail_reason") or "TikTok processing failed"
                    else:row.status="processing"
                except Exception:pass
        db.commit()
    return [{"platform":r.platform,"action":r.action,"status":r.status,"text":r.text,"url":r.url,"error":r.error,"created_at":r.created_at.isoformat()} for r in rows]

@app.get("/api/analytics")
def api_analytics(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); view=_analytics_dashboard(analytics_for_user(db,user.id),recent_posts_for_user(db,user.id,limit=30)); return {**view["platforms"],"_summary":view["summary"],"_note":view["note"]}

from .analytics_view import dashboard as _analytics_dashboard

@app.get("/api/analytics/dashboard")
def api_analytics_dashboard(request:Request,db:Session=Depends(get_db)):
    user=current_user(request);return _analytics_dashboard(analytics_for_user(db,user.id),recent_posts_for_user(db,user.id,limit=30))

@app.post("/api/insights")
def api_insights(body:InsightRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request); data=analytics_for_user(db,user.id); feed=recent_posts_for_user(db,user.id); dashboard=_analytics_dashboard(data,feed); summary=dashboard.get("summary") or {}; question=body.question.lower()
    connected=[(name,value) for name,value in dashboard["platforms"].items() if name!="_summary" and isinstance(value,dict) and value.get("connected")]
    score=lambda value:int(value.get("likes") or value.get("reactions") or 0)+int(value.get("comments") or value.get("replies") or 0)+int(value.get("shares") or value.get("reposts") or 0)
    leader=max((item for item in connected if score(item[1])>0),key=lambda item:score(item[1]),default=None)
    posts=dashboard.get("top_posts") or []
    top=max(posts,key=lambda item:int(item.get("likes") or 0)+int(item.get("comments") or 0)+int(item.get("shares") or 0),default=None)
    def number(key:str)->str:return "unavailable" if summary.get(key) is None else f"{int(summary[key]):,}"
    if not connected:
        answer="I don't have enough account data yet. Connect a social account and Zova will start reading the available performance signals."
    elif any(word in question for word in ("trend","working","best","perform","improve","strategy")):
        lead=f"{leader[0].title()} has the strongest engagement signal in the available data" if leader else "There is not yet a clear platform leader"
        detail=f" Your strongest recent post is on {str(top.get('platform') or '').title()} with {int(top.get('likes') or 0):,} likes, {int(top.get('comments') or 0):,} comments and {int(top.get('shares') or 0):,} shares." if top else " Publish a few more posts so I can compare formats and topics."
        answer=lead+"."+detail
    elif "impression" in question or "view" in question:
        answer=f"Your connected accounts recorded {number('impressions')} impressions in the available sample of posts published in the last seven days."
    elif "like" in question:
        answer=f"Your connected accounts recorded {number('likes')} likes in the available sample of posts published in the last seven days."
    elif "comment" in question or "reply" in question:
        answer=f"Your connected accounts recorded {number('comments')} comments or replies in the available sample of posts published in the last seven days."
    elif "share" in question or "repost" in question:
        answer=f"Your connected accounts recorded {number('shares')} shares or reposts in the available sample of posts published in the last seven days."
    elif "follower" in question:
        answer=f"Your connected accounts currently report {number('followers')} followers in total."
    elif "recent" in question or "last post" in question:
        answer=(f"Your latest available post was on {str(posts[0].get('platform') or '').title()}: “{str(posts[0].get('text') or 'Media post')[:180]}”" if posts else "No recent connected-account posts are available yet.")
    else:
        lead=f" {leader[0].title()} currently has the strongest engagement signal." if leader else ""
        answer=f"In the available sample of posts published in the last seven days: {number('impressions')} impressions, {number('likes')} likes, {number('comments')} comments and {number('shares')} shares or reposts.{lead}"
    answer += " " + dashboard["note"]
    if connected and os.environ.get("OPENAI_API_KEY"):
        try:
            with allowances.ai_action(db,user.id):
                answer=ai.analyse_performance(question=body.question,dashboard=dashboard,preferences=get_preferences(db,user.id))
        except HTTPException:raise
        except Exception as exc:log.warning("AI performance analysis failed; using account-data fallback: %s",exc)
    return {"answer":answer,"summary":summary,"has_signal":bool(connected),"recommendations":dashboard.get("recommendations") or []}

@app.get("/api/recent-posts")
def api_recent_posts(request:Request,db:Session=Depends(get_db)):
    user=current_user(request);return recent_posts_for_user(db,user.id)

@app.post("/internal/run-due")
def run_due(authorization:Annotated[str|None,Header()]=None):
    secret=os.environ.get("SCHEDULER_SECRET") or os.environ.get("ADMIN_API_KEY")
    token=bearer_token(authorization)
    if not secret or not hmac.compare_digest(token,secret):raise HTTPException(401,"Invalid scheduler secret")
    return process_due()


# ---------- Backward-compatible Custom GPT X Action ----------
@app.post("/x/preview")
def legacy_preview(body:LegacyPostRequest,creator:Creator=Depends(require_legacy_creator)):
    return {"text":body.text,"character_count":len(body.text),"valid":len(body.text)<=280,"account":f"@{creator.x_username}"}

@app.post("/x/post")
def legacy_publish(body:LegacyPostRequest,creator:Creator=Depends(require_legacy_creator),db:Session=Depends(get_db)):
    if body.approved is not True:raise HTTPException(400,"Publication requires approved=true after explicit user confirmation")
    result=publish_legacy_creator(body.text,creator,db);return {"success":True,"post_id":result["post_id"],"url":result["url"],"text":body.text,"account":f"@{creator.x_username}"}

@app.get("/help",response_class=HTMLResponse)
def help_page(request:Request):
    return templates.TemplateResponse(request, "help.html",template_context(request,current_user(request)))

from .operations import router as operations_router
app.include_router(operations_router)
app.include_router(readiness.router)
from .verification import router as verification_router
app.include_router(verification_router)

@app.get('/media/preview/{asset_id}')
def media_preview(asset_id:int,request:Request,db:Session=Depends(get_db)):
    from .storage import get_public_url
    row=db.get(MediaAsset,asset_id)
    if not row or row.user_id!=current_user(request).id:raise HTTPException(404,'Media not found')
    try:return RedirectResponse(get_public_url(row.storage_key,row.public_url,expires=300),307)
    except RuntimeError:raise HTTPException(404,'Media preview unavailable')

from .connection_review import router as connection_review_router
app.include_router(connection_review_router)
