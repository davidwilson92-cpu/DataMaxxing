#!/usr/bin/env python3
"""Private HTTP API that lets a Custom GPT publish approved posts to X."""

import hmac
import logging
import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import tweepy

log = logging.getLogger("x_poster_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_LEN = 280
REQUIRED_X_VARS = (
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
)

app = FastAPI(
    title="Private X Posting API",
    version="1.0.0",
    description="Preview and publish explicitly approved posts to one authenticated X account.",
)


class PostRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_LEN, description="Exact post text")
    approved: bool = Field(
        default=False,
        description="Must be true only after the user explicitly asks to publish this exact text.",
    )

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Post text cannot be blank")
        return value


class PreviewResponse(BaseModel):
    text: str
    character_count: int
    valid: bool


class PostResponse(BaseModel):
    success: bool
    post_id: str
    url: str
    text: str


def require_api_key(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.environ.get("POSTING_API_KEY")
    if not expected:
        log.error("POSTING_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="Server authentication is not configured")

    scheme, _, token = (authorization or "").partition(" ")
    valid = scheme.lower() == "bearer" and hmac.compare_digest(token, expected)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


def load_x_credentials() -> dict[str, str]:
    missing = [name for name in REQUIRED_X_VARS if not os.environ.get(name)]
    if missing:
        log.error("Missing X credentials: %s", ", ".join(missing))
        raise HTTPException(status_code=500, detail="X credentials are not configured")

    return {
        "consumer_key": os.environ["X_API_KEY"],
        "consumer_secret": os.environ["X_API_SECRET"],
        "access_token": os.environ["X_ACCESS_TOKEN"],
        "access_token_secret": os.environ["X_ACCESS_TOKEN_SECRET"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/x/preview",
    response_model=PreviewResponse,
    dependencies=[Depends(require_api_key)],
)
def preview_post(request: PostRequest) -> PreviewResponse:
    """Validate and return the exact text without publishing it."""
    return PreviewResponse(
        text=request.text,
        character_count=len(request.text),
        valid=len(request.text) <= MAX_LEN,
    )


@app.post(
    "/x/post",
    response_model=PostResponse,
    dependencies=[Depends(require_api_key)],
)
def publish_post(request: PostRequest) -> PostResponse:
    """Publish the exact supplied text after explicit user approval."""
    if request.approved is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publication requires approved=true after explicit user confirmation",
        )

    creds = load_x_credentials()
    client = tweepy.Client(
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )

    try:
        response = client.create_tweet(text=request.text)
        post_id = str(response.data["id"])
    except tweepy.TweepyException as exc:
        log.exception("X rejected the post")
        raise HTTPException(status_code=502, detail=f"X API error: {exc}") from exc

    username = os.environ.get("X_USERNAME", "DataMaxxing").lstrip("@")
    url = f"https://x.com/{username}/status/{post_id}"
    log.info("Published X post %s", post_id)
    return PostResponse(success=True, post_id=post_id, url=url, text=request.text)
