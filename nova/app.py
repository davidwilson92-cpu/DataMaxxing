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
from zoneinfo import ZoneInfo

import httpx
import jwt
import tweepy
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai, billing
from .db import (
    Activity, AuthIdentity, AuthState, Creator, CreatorPreferences, Draft, MediaAsset, OAuth2Connection, OAuthState,
    PostLog, ScheduledPost, SessionLocal, SocialConnection, User, get_db, get_preferences, utcnow,
)
from .scheduler import loop as scheduler_loop, process_due
from .security import current_user, decrypt, encrypt, hash_api_key, hash_password, make_state, make_user_session, verify_password
from .social import (
    META_SCOPES, TIKTOK_SCOPES, X_SCOPES, analytics_for_user, meta_authorize_url, meta_exchange,
    publish_platform, tiktok_authorize_url, tiktok_exchange, upsert_connection, x_authorize_url, x_exchange,
)
from .storage import UPLOAD_DIR, save_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nova")

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def base_url() -> str:
    value = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return value or "http://localhost:8000"


def subscription_guard(user: User) -> None:
    if not billing.has_access(user):
        raise HTTPException(status_code=402, detail="An active Zova subscription is required")


def template_context(request: Request, user: User | None = None, **kwargs: Any) -> dict[str, Any]:
    return {"request": request, "user": user, **kwargs}


def set_user_cookie(response: RedirectResponse | JSONResponse, user: User) -> None:
    response.set_cookie(
        "nova_session", make_user_session(user.id), max_age=30 * 86400, httponly=True,
        secure=base_url().startswith("https://"), samesite="lax", path="/",
    )


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
    db.add(OAuthState(user_id=user_id, platform=platform, state_hash=hash_api_key(state), encrypted_code_verifier=encrypt(verifier) if verifier else None))
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
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


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

@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    try: user = current_user(request)
    except HTTPException: user = None
    return templates.TemplateResponse("landing.html", template_context(request, user))

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("auth.html", template_context(request, heading="Create your account", subheading="Start with Apple or use your email. You’ll connect socials next.", action="/signup", button="Create account", error=error, apple_ready=apple_configured()))

@app.post("/signup")
def signup(request: Request, email: Annotated[str, Form()], password: Annotated[str, Form()], password_confirmation: Annotated[str, Form()], db: Session=Depends(get_db)):
    email=email.strip().lower()
    if password != password_confirmation: return RedirectResponse("/signup?error=Passwords+do+not+match",303)
    if len(password)<10: return RedirectResponse("/signup?error=Use+a+password+of+at+least+10+characters",303)
    if db.scalar(select(User).where(User.email==email)): return RedirectResponse("/signup?error=An+account+with+that+email+already+exists",303)
    user=User(email=email,password_hash=hash_password(password)); db.add(user); db.commit(); db.refresh(user); get_preferences(db,user.id)
    resp=RedirectResponse("/onboarding/socials",303); set_user_cookie(resp,user); return resp

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("auth.html", template_context(request, heading="Welcome back", subheading="Sign in to your Zova workspace.", action="/login", button="Log in", error=error, apple_ready=apple_configured()))


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
def apple_callback(code: Annotated[str | None, Form()] = None, id_token: Annotated[str | None, Form()] = None, state: Annotated[str | None, Form()] = None, error: Annotated[str | None, Form()] = None, db: Session = Depends(get_db)):
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
    identity = db.scalar(select(AuthIdentity).where(AuthIdentity.provider == "apple", AuthIdentity.subject == subject))
    user = db.get(User, identity.user_id) if identity else (db.scalar(select(User).where(User.email == email)) if email else None)
    created = user is None
    if created:
        user = User(email=email or f"apple-{hash_api_key(subject)[:20]}@private.zova.invalid", password_hash=hash_password(secrets.token_urlsafe(48))); db.add(user); db.commit(); db.refresh(user); get_preferences(db, user.id)
    if not identity: db.add(AuthIdentity(user_id=user.id, provider="apple", subject=subject)); db.commit()
    resp = RedirectResponse("/onboarding/socials" if created else "/studio", 303); set_user_cookie(resp, user); return resp

@app.post("/login")
def login(request: Request,email:Annotated[str,Form()],password:Annotated[str,Form()],db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==email.strip().lower()))
    if not user or not verify_password(password,user.password_hash): return RedirectResponse("/login?error=Incorrect+email+or+password",303)
    resp=RedirectResponse("/studio",303); set_user_cookie(resp,user); return resp

@app.post("/logout")
def logout():
    resp=RedirectResponse("/",303); resp.delete_cookie("nova_session",path="/"); return resp

@app.get("/subscribe", response_class=HTMLResponse)
def subscribe(request:Request):
    user=current_user(request)
    return templates.TemplateResponse("subscribe.html", template_context(request,user,billing_ready=billing.configured(),subscription_required=billing.require_subscription(),price_label=os.environ.get("ZOVA_PRICE_LABEL",os.environ.get("NOVA_PRICE_LABEL","Subscription")),price_note=os.environ.get("ZOVA_PRICE_NOTE",os.environ.get("NOVA_PRICE_NOTE","Cancel from your account at any time."))))

@app.get("/billing/checkout")
def billing_checkout(request:Request):
    user=current_user(request)
    try:url=billing.create_checkout(user,base_url())
    except RuntimeError as exc: raise HTTPException(503,str(exc))
    return RedirectResponse(url,303)

@app.get("/billing/success")
def billing_success(request:Request,session_id:str=Query(...),db:Session=Depends(get_db)):
    user=current_user(request)
    try:data=billing.fetch_checkout_session(session_id)
    except RuntimeError as exc: raise HTTPException(502,str(exc))
    if str(data.get("client_reference_id"))!=str(user.id): raise HTTPException(403,"Checkout session does not belong to this user")
    user.stripe_customer_id=data.get("customer") or user.stripe_customer_id; user.stripe_subscription_id=data.get("subscription") if isinstance(data.get("subscription"),str) else ((data.get("subscription") or {}).get("id")); user.subscription_status="active" if data.get("payment_status") in {"paid","no_payment_required"} else user.subscription_status; db.commit()
    return RedirectResponse("/studio",303)

@app.get("/billing/portal")
def billing_portal(request:Request):
    user=current_user(request)
    try:url=billing.create_portal(user,base_url())
    except RuntimeError as exc: raise HTTPException(503,str(exc))
    return RedirectResponse(url,303)

@app.post("/billing/webhook")
async def billing_webhook(request:Request,db:Session=Depends(get_db)):
    raw=await request.body(); sig=request.headers.get("stripe-signature","")
    if not billing.verify_webhook(raw,sig): raise HTTPException(400,"Invalid Stripe signature")
    event=json.loads(raw); billing.apply_event(db,event); return {"received":True}

@app.get("/security",response_class=HTMLResponse)
def security_page(request:Request):
    try:user=current_user(request)
    except HTTPException:user=None
    return templates.TemplateResponse("security.html",template_context(request,user,contact_email=os.environ.get("PRIVACY_CONTACT_EMAIL","privacy@example.com")))

@app.get("/privacy",response_class=HTMLResponse)
def privacy_alias(request:Request): return security_page(request)

@app.get("/studio",response_class=HTMLResponse)
def studio(request:Request):
    user=current_user(request)
    return templates.TemplateResponse("studio.html",template_context(request,user,subscription_blocked=not billing.has_access(user)))

@app.get("/onboarding/socials", response_class=HTMLResponse)
def onboarding_socials(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    rows = db.scalars(select(SocialConnection).where(SocialConnection.user_id == user.id, SocialConnection.active.is_(True))).all()
    by = {}
    for row in rows: by.setdefault(row.platform, []).append(row)
    response = templates.TemplateResponse("onboarding_socials.html", template_context(request, user, by_platform=by))
    response.set_cookie("zova_onboarding", "1", max_age=1800, httponly=True, secure=base_url().startswith("https://"), samesite="lax", path="/")
    return response

@app.get("/onboarding/writing-style", response_class=HTMLResponse)
def onboarding_writing_style(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    return templates.TemplateResponse("onboarding_writing.html", template_context(request, user, prefs=get_preferences(db, user.id)))

@app.get("/onboarding/complete")
def onboarding_complete(request: Request):
    current_user(request)
    response = RedirectResponse("/studio", 303); response.delete_cookie("zova_onboarding", path="/"); return response

@app.get("/account",response_class=HTMLResponse)
def account(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); prefs=get_preferences(db,user.id); rows=db.scalars(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc())).all(); by={}
    for r in rows: by.setdefault(r.platform,[]).append(r)
    return templates.TemplateResponse("account.html",template_context(request,user,prefs=prefs,by_platform=by,billing_ready=billing.configured()))

@app.post("/account/preferences")
def save_preferences(request:Request,writing_tone:Annotated[str,Form()]="",audience:Annotated[str,Form()]="",topics:Annotated[str,Form()]="",things_to_avoid:Annotated[str,Form()]="",example_posts:Annotated[str,Form()]="",preferred_post_length:Annotated[int,Form()]=220,timezone_name:Annotated[str,Form(alias="timezone")]="Europe/London",next_url:Annotated[str,Form(alias="next")]="",db:Session=Depends(get_db)):
    user=current_user(request); prefs=get_preferences(db,user.id)
    try:ZoneInfo(timezone_name)
    except Exception:timezone_name="Europe/London"
    prefs.writing_tone=writing_tone[:5000]; prefs.audience=audience[:5000]; prefs.topics=topics[:5000]; prefs.things_to_avoid=things_to_avoid[:5000]; prefs.example_posts=example_posts[:12000]; prefs.preferred_post_length=max(30,min(preferred_post_length,4000)); prefs.timezone=timezone_name; db.commit(); return RedirectResponse("/onboarding/complete" if next_url == "/onboarding/complete" else "/account",303)

@app.post("/account/connections/{connection_id}/unlink")
def unlink(connection_id:int,request:Request,db:Session=Depends(get_db)):
    user=current_user(request); conn=db.get(SocialConnection,connection_id)
    if not conn or conn.user_id!=user.id: raise HTTPException(404,"Connection not found")
    conn.active=False; db.commit(); return RedirectResponse("/account",303)


# ---------- OAuth connections ----------
@app.get("/oauth/x/start")
def oauth_x_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); verifier=secrets.token_urlsafe(64); state=_new_state(db,user.id,"x",verifier); return RedirectResponse(x_authorize_url(state,verifier),302)

@app.get("/callback/x")
@app.get("/oauth/x/callback")
def oauth_x_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    if error:return RedirectResponse("/account?error=x_connection_cancelled",303)
    if not code or not state:raise HTTPException(400,"Missing OAuth code or state")
    row=_state_row(db,state,"x"); verifier=decrypt(row.encrypted_code_verifier) if row.encrypted_code_verifier else ""
    try:token,user_info=x_exchange(code,verifier)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    upsert_connection(db,user_id=row.user_id,platform="x",account_id=str(user_info["id"]),username=user_info.get("username","") or "",display_name=user_info.get("name","") or "",access=token["access_token"],refresh=token.get("refresh_token"),expires_in=token.get("expires_in"),scope=token.get("scope",X_SCOPES),metadata={"profile_image_url":user_info.get("profile_image_url")})
    return RedirectResponse("/onboarding/socials?connected=x" if request.cookies.get("zova_onboarding") else "/account?connected=x",303)

@app.get("/oauth/meta/start")
def oauth_meta_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); state=_new_state(db,user.id,"meta"); return RedirectResponse(meta_authorize_url(state),302)

@app.get("/oauth/meta/callback")
def oauth_meta_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    if error:return RedirectResponse("/account?error=meta_connection_cancelled",303)
    if not code or not state:raise HTTPException(400,"Missing Meta OAuth code or state")
    row=_state_row(db,state,"meta")
    try:pages=meta_exchange(code)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    for page in pages:
        page_token=page.get("access_token"); page_id=str(page.get("id")); name=page.get("name","")
        if not page_token or not page_id:continue
        upsert_connection(db,user_id=row.user_id,platform="facebook",account_id=page_id,username=name,display_name=name,access=page_token,scope=META_SCOPES,metadata={"tasks":page.get("tasks",[])})
        ig=page.get("instagram_business_account") or {}
        if ig.get("id"):
            upsert_connection(db,user_id=row.user_id,platform="instagram",account_id=str(ig["id"]),username=ig.get("username","") or "",display_name=ig.get("name","") or ig.get("username","") or "",access=page_token,scope=META_SCOPES,metadata={"facebook_page_id":page_id,"profile_picture_url":ig.get("profile_picture_url")})
    return RedirectResponse("/onboarding/socials?connected=meta" if request.cookies.get("zova_onboarding") else "/account?connected=meta",303)

@app.get("/oauth/tiktok/start")
def oauth_tiktok_start(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); state=_new_state(db,user.id,"tiktok"); return RedirectResponse(tiktok_authorize_url(state),302)

@app.get("/oauth/tiktok/callback")
def oauth_tiktok_callback(request:Request,code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    if error:return RedirectResponse("/account?error=tiktok_connection_cancelled",303)
    if not code or not state:raise HTTPException(400,"Missing TikTok OAuth code or state")
    row=_state_row(db,state,"tiktok")
    try:token,info=tiktok_exchange(code)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    upsert_connection(db,user_id=row.user_id,platform="tiktok",account_id=str(info.get("open_id")),username=info.get("display_name","") or "",display_name=info.get("display_name","") or "",access=token["access_token"],refresh=token.get("refresh_token"),expires_in=token.get("expires_in"),scope=token.get("scope",TIKTOK_SCOPES),metadata={"avatar_url":info.get("avatar_url")})
    return RedirectResponse("/onboarding/socials?connected=tiktok" if request.cookies.get("zova_onboarding") else "/account?connected=tiktok",303)


# ---------- API models ----------
class GenerateRequest(BaseModel):
    brief:str=Field(min_length=1,max_length=12000); instruction:str=Field(default="",max_length=5000); platforms:list[str]; thread_length:int=1; link_url:str=""
    @field_validator("thread_length")
    @classmethod
    def valid_thread(cls,v:int): return v if v in {1,3,5} else 1
class RewriteRequest(BaseModel): platform:str; posts:list[str]; action:str
class ScheduleSuggestRequest(BaseModel): platforms:list[str]; context:str=""
class VoiceLearnRequest(BaseModel): content:str=Field(min_length=80,max_length=30000)
class PreviewRequest(BaseModel): platforms:list[str]; variants:dict[str,Any]
class PublishRequest(BaseModel): draft_id:int|None=None; platforms:list[str]; variants:dict[str,Any]; media_asset_ids:list[int]=[]; link_url:str=""
class ScheduleRequest(PublishRequest): scheduled_local:str
class LegacyPostRequest(BaseModel):
    text:str=Field(min_length=1,max_length=280); approved:bool=False


@app.post("/api/voice/learn")
def learn_voice(payload: VoiceLearnRequest, request: Request, db: Session = Depends(get_db)):
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

@app.post("/api/media")
async def upload_media(request:Request,files:list[UploadFile]=File(...),db:Session=Depends(get_db)):
    user=current_user(request); subscription_guard(user); result=[]
    for f in files[:10]:
        data=await f.read();
        if len(data)>15*1024*1024:raise HTTPException(413,"Each image must be 15 MB or smaller")
        if not (f.content_type or "").startswith("image/"):raise HTTPException(400,"This build accepts image uploads only")
        stored=save_bytes(data,f.filename or "image",f.content_type or "application/octet-stream",base_url())
        row=MediaAsset(user_id=user.id,filename=f.filename or "image",mime_type=f.content_type or "application/octet-stream",storage_key=stored.storage_key,public_url=stored.public_url,size_bytes=len(data));db.add(row);db.commit();db.refresh(row);result.append({"id":row.id,"filename":row.filename})
    return {"assets":result}

@app.get("/media/raw/{filename}")
def local_media(filename:str):
    safe=Path(filename).name; path=UPLOAD_DIR/safe
    if not path.exists():raise HTTPException(404,"Media not found")
    return FileResponse(path)

@app.post("/api/ai/generate")
def api_generate(body:GenerateRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request); subscription_guard(user); platforms=_validate_platforms(body.platforms); prefs=get_preferences(db,user.id)
    try:variants=ai.generate_variants(brief=body.brief,instruction=body.instruction,platforms=platforms,thread_length=body.thread_length,preferences=prefs,link_url=body.link_url)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    row=Draft(user_id=user.id,brief=body.brief,instruction=body.instruction,platforms_json=json.dumps(platforms),variants_json=json.dumps(variants,ensure_ascii=False),thread_length=body.thread_length,status="draft");db.add(row);db.commit();db.refresh(row)
    return {"draft_id":row.id,"variants":variants}

@app.post("/api/ai/rewrite")
def api_rewrite(body:RewriteRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);subscription_guard(user);prefs=get_preferences(db,user.id)
    try:posts=ai.rewrite_variant(platform=body.platform,posts=body.posts,action=body.action,preferences=prefs)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    return {"posts":posts}

@app.post("/api/ai/schedule")
def api_schedule_suggest(body:ScheduleSuggestRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);subscription_guard(user);prefs=get_preferences(db,user.id);platforms=_validate_platforms(body.platforms)
    try:s=ai.propose_schedule(platforms=platforms,timezone_name=prefs.timezone,context=body.context)
    except RuntimeError as exc:raise HTTPException(502,str(exc))
    return {"timezone":prefs.timezone,"suggestions":s}

@app.post("/api/preview")
def api_preview(body:PreviewRequest,request:Request):
    user=current_user(request); subscription_guard(user); platforms=_validate_platforms(body.platforms); problems=[]
    for p in platforms:
        posts=((body.variants.get(p) or {}).get("posts") or [])
        if not posts:problems.append(f"{p}: no draft")
        if p=="x" and any(len(str(x))>280 for x in posts):problems.append("X: one or more posts exceed 280 characters")
    if problems:raise HTTPException(400,"; ".join(problems))
    return {"valid":True,"summary":f"Ready for {', '.join(platforms)}. Nothing has been published."}

@app.post("/api/publish")
def api_publish(body:PublishRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);subscription_guard(user);platforms=_validate_platforms(body.platforms);assets=_user_assets(db,user.id,body.media_asset_ids);results={};successes=0
    for p in platforms:
        posts=((body.variants.get(p) or {}).get("posts") or [])
        if not posts:results[p]={"status":"failed","error":"No draft supplied"};continue
        try:
            r=publish_platform(db,user_id=user.id,platform=p,posts=posts,assets=assets,link_url=body.link_url); st="pending" if r.get("pending") else "published"; results[p]={"status":st,**r}; db.add(Activity(user_id=user.id,draft_id=body.draft_id,platform=p,action="publish",status=st,text="\n\n".join(posts),platform_post_id=r.get("post_id"),url=r.get("url")));successes+=1
        except Exception as exc:
            results[p]={"status":"failed","error":str(exc)};db.add(Activity(user_id=user.id,draft_id=body.draft_id,platform=p,action="publish",status="failed",text="\n\n".join(posts),error=str(exc)))
        db.commit()
    if body.draft_id:
        d=db.get(Draft,body.draft_id)
        if d and d.user_id==user.id:d.variants_json=json.dumps(body.variants,ensure_ascii=False);d.status="published" if successes==len(platforms) else ("partial" if successes else "failed");db.commit()
    failed=len(platforms)-successes;summary=f"Published to {successes} platform{'s' if successes!=1 else ''}."+(f" {failed} failed. Check the details below." if failed else "")
    return {"summary":summary,"results":results}

@app.post("/api/schedule")
def api_schedule(body:ScheduleRequest,request:Request,db:Session=Depends(get_db)):
    user=current_user(request);subscription_guard(user);platforms=_validate_platforms(body.platforms);prefs=get_preferences(db,user.id)
    try:
        local=datetime.fromisoformat(body.scheduled_local); local=local.replace(tzinfo=ZoneInfo(prefs.timezone)) if local.tzinfo is None else local; scheduled=local.astimezone(timezone.utc)
    except Exception:raise HTTPException(400,"Invalid schedule time")
    if scheduled<=utcnow()+timedelta(minutes=1):raise HTTPException(400,"Schedule at least one minute in the future")
    rows=[]
    for p in platforms:
        posts=((body.variants.get(p) or {}).get("posts") or [])
        if not posts:continue
        conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.platform==p,SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc()))
        row=ScheduledPost(user_id=user.id,draft_id=body.draft_id,platform=p,connection_id=conn.id if conn else None,content_json=json.dumps({"posts":posts,"link_url":body.link_url},ensure_ascii=False),media_asset_ids_json=json.dumps(body.media_asset_ids),scheduled_at=scheduled,status="scheduled");db.add(row);rows.append(row)
    if body.draft_id:
        d=db.get(Draft,body.draft_id)
        if d and d.user_id==user.id:d.status="scheduled"
    db.commit();return {"summary":f"Scheduled {len(rows)} platform post{'s' if len(rows)!=1 else ''} for {local.strftime('%d %b %Y %H:%M')} {prefs.timezone}."}

@app.get("/api/drafts")
def api_drafts(request:Request,db:Session=Depends(get_db)):
    user=current_user(request)
    rows=db.scalars(select(Draft).where(Draft.user_id==user.id).order_by(Draft.id.desc()).limit(30)).all()
    output=[]
    for r in rows:
        acts=db.scalars(select(Activity).where(Activity.user_id==user.id,Activity.draft_id==r.id,Activity.url.is_not(None)).order_by(Activity.id.desc())).all()
        output.append({"id":r.id,"brief":r.brief,"platforms":json.loads(r.platforms_json or "[]"),"status":r.status,"created_at":r.created_at.isoformat(),"links":[{"platform":a.platform,"url":a.url} for a in acts if a.url]})
    return output

@app.get("/api/activity")
def api_activity(request:Request,db:Session=Depends(get_db)):
    user=current_user(request); rows=db.scalars(select(Activity).where(Activity.user_id==user.id).order_by(Activity.id.desc()).limit(20)).all();return [{"platform":r.platform,"action":r.action,"status":r.status,"text":r.text,"url":r.url,"created_at":r.created_at.isoformat()} for r in rows]

@app.get("/api/analytics")
def api_analytics(request:Request,db:Session=Depends(get_db)):
    user=current_user(request);return analytics_for_user(db,user.id)

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
