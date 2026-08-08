#!/usr/bin/env python3
"""
post_tweet.py — DataMaxxing X (Twitter) posting automation

Posts a single tweet on behalf of the authenticated account using OAuth 1.0a
user-context credentials. Credentials are read ONLY from environment
variables — never hardcode them here.

Usage:
    python post_tweet.py "Your tweet text goes here"
    python post_tweet.py --file tweet.txt
    python post_tweet.py "Text with an image" --image path/to/chart.png

Required environment variables (set as GitHub Actions secrets):
    X_API_KEY
    X_API_SECRET
    X_ACCESS_TOKEN
    X_ACCESS_TOKEN_SECRET

Install deps:
    pip install tweepy --break-system-packages
"""

import os
import sys
import argparse
import logging

try:
    import tweepy
except ImportError:
    print("Missing dependency. Run: pip install tweepy --break-system-packages")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("post_tweet")

MAX_LEN = 280


def load_credentials():
    required = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        log.error("Set these as GitHub Actions secrets — never hardcode credentials.")
        sys.exit(1)
    return {
        "consumer_key": os.environ["X_API_KEY"],
        "consumer_secret": os.environ["X_API_SECRET"],
        "access_token": os.environ["X_ACCESS_TOKEN"],
        "access_token_secret": os.environ["X_ACCESS_TOKEN_SECRET"],
    }


def get_text(args) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text.strip() if args.text else ""

    if not text:
        log.error("No tweet text provided.")
        sys.exit(1)

    if len(text) > MAX_LEN:
        log.error("Tweet is %d characters, exceeds the %d limit.", len(text), MAX_LEN)
        sys.exit(1)

    return text


def post(text: str, image_path: str | None, dry_run: bool):
    creds = load_credentials()

    if dry_run:
        log.info("[DRY RUN] Would post (%d chars): %s", len(text), text)
        if image_path:
            log.info("[DRY RUN] Would attach image: %s", image_path)
        return

    client = tweepy.Client(
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )

    media_ids = None
    if image_path:
        if not os.path.exists(image_path):
            log.error("Image file not found: %s", image_path)
            sys.exit(1)
        auth = tweepy.OAuth1UserHandler(
            creds["consumer_key"],
            creds["consumer_secret"],
            creds["access_token"],
            creds["access_token_secret"],
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(image_path)
        media_ids = [media.media_id]
        log.info("Uploaded image, media_id=%s", media.media_id)

    response = client.create_tweet(text=text, media_ids=media_ids)
    tweet_id = response.data.get("id")
    log.info("Posted successfully: https://x.com/DataMaxxing/status/%s", tweet_id)


def main():
    parser = argparse.ArgumentParser(description="Post a tweet to X on behalf of the authenticated account.")
    parser.add_argument("text", nargs="?", help="Tweet text (omit if using --file)")
    parser.add_argument("--file", help="Path to a text file containing the tweet")
    parser.add_argument("--image", help="Optional path to an image to attach")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be posted without posting")
    args = parser.parse_args()

    text = get_text(args)
    post(text, args.image, args.dry_run)


if __name__ == "__main__":
    main()