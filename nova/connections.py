"""Non-secret connection presentation shared by onboarding and Account."""
import os

PLATFORMS = {
    "instagram": {"name": "Instagram", "provider": "Instagram", "detail": "Connect your Instagram professional account directly. No Facebook Page is needed.", "keys": ("INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET")},
    "facebook": {"name": "Facebook", "provider": "Facebook", "detail": "Sign in to Facebook to select the Pages you manage. This does not connect Instagram.", "keys": ("META_APP_ID", "META_APP_SECRET")},
    "tiktok": {"name": "TikTok", "provider": "TikTok", "detail": "Sign in to the TikTok account you want Zova to manage.", "keys": ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET")},
    "x": {"name": "X", "provider": "X", "detail": "Sign in to the X account you want Zova to manage.", "keys": ("X_OAUTH2_CLIENT_ID",)},
}


def connection_options():
    return {key: {**{k: v for k, v in value.items() if k != "keys"},
                  "ready": all(bool(os.environ.get(k, "").strip()) for k in value["keys"]),
                  "start": "/oauth/meta/start" if key == "facebook" else f"/oauth/{key}/start"}
            for key, value in PLATFORMS.items()}


def safe_login_next(value):
    # Never resume an authorisation endpoint automatically after signing in.
    allowed = {"/studio", "/account", "/analytics", "/drafts", "/onboarding/socials", "/onboarding/writing-style"}
    allowed.update(f"/connect/{key}" for key in PLATFORMS)
    return value if value in allowed else "/studio"
