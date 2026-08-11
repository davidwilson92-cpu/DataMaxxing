from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

import httpx

log = logging.getLogger("nova.ai")

PLATFORM_GUIDANCE = {
    "x": "X: concise and conversational. Maximum 280 characters per post. If thread_length is 3 or 5, return exactly that many standalone-but-connected posts, each <=280 characters.",
    "facebook": "Facebook: natural, readable, slightly more context than X. Avoid forced hashtags. A link may be included when supplied.",
    "instagram": "Instagram: strong first line, visually minded caption, selective hashtags only when useful. Do not claim the link in caption is clickable. Media is required for publishing.",
    "tiktok": "TikTok: short hook-led description/caption suited to visual content, with a few relevant hashtags when natural. Media is required for publishing.",
}

REWRITE_GUIDANCE = {
    "shorter": "Make it materially shorter while preserving the core meaning.",
    "punchier": "Increase energy and immediacy; stronger opening; remove filler.",
    "serious": "Make the tone more serious, restrained and authoritative.",
    "humorous": "Make it wittier and lighter without becoming silly or inventing facts.",
    "controversial": "Make the point more provocative and debate-provoking, but do not fabricate facts, target protected groups, harass individuals, or use inflammatory abuse.",
    "data-driven": "Make it more analytical and evidence-led using only facts or numbers already supplied. Never invent statistics.",
}


def _api_key() -> str:
    value = os.environ.get("OPENAI_API_KEY", "")
    if not value:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return value


def _model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5-mini")


def _extract_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks).strip()


def _parse_json(text: str) -> Any:
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def _responses(prompt: str, *, max_output_tokens: int = 2500) -> str:
    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
        json={"model": _model(), "input": prompt, "max_output_tokens": max_output_tokens},
        timeout=75.0,
    )
    if response.status_code >= 400:
        log.error("OpenAI request failed: %s", response.text)
        raise RuntimeError(f"OpenAI returned {response.status_code}")
    text = _extract_text(response.json())
    if not text:
        raise RuntimeError("OpenAI returned an empty response")
    return text


def infer_voice_profile(content_sample: str) -> dict[str, Any]:
    """Infer a useful creator profile from their own published writing."""
    prompt = f"""You are Zova's voice analyst. Study the creator's writing sample and infer a practical profile that another AI can use to represent them accurately.

Return ONLY valid JSON with this schema:
{{"summary":"one concise sentence", "writing_tone":"...", "audience":"...", "topics":"...", "things_to_avoid":"...", "preferred_post_length":220}}

Be specific but never invent biographical facts. Describe observed patterns, vocabulary, rhythm, point of view, likely audience and recurring subjects. 'things_to_avoid' should prevent the model from flattening or caricaturing the voice. preferred_post_length must be an integer from 30 to 4000 based on the sample.

CREATOR WRITING SAMPLE:
{content_sample[:30000]}
"""
    data = _parse_json(_responses(prompt, max_output_tokens=1200))
    if not isinstance(data, dict):
        raise RuntimeError("AI returned an invalid voice profile")
    required = ("summary", "writing_tone", "audience", "topics", "things_to_avoid")
    if any(not isinstance(data.get(key), str) for key in required):
        raise RuntimeError("AI returned an incomplete voice profile")
    try:
        length = int(data.get("preferred_post_length", 220))
    except (TypeError, ValueError):
        length = 220
    data["preferred_post_length"] = max(30, min(length, 4000))
    return data


def generate_variants(
    *,
    brief: str,
    instruction: str,
    platforms: list[str],
    thread_length: int,
    preferences: Any,
    link_url: str = "",
) -> dict[str, Any]:
    selected = [p for p in platforms if p in PLATFORM_GUIDANCE]
    guidance = "\n".join(PLATFORM_GUIDANCE[p] for p in selected)
    examples = (getattr(preferences, "example_posts", "") or "")[:7000]
    prompt = f"""You are Zova, a social publishing editor. Produce platform-native drafts from one source brief.

Return ONLY valid JSON. No markdown fences and no commentary.
Schema:
{{
  "x": {{"posts": ["..."]}},
  "facebook": {{"posts": ["..."]}},
  "instagram": {{"posts": ["..."]}},
  "tiktok": {{"posts": ["..."]}}
}}
Include only requested platforms. Every value in posts must be a finished publish-ready string.

Platform rules:
{guidance}

Creator preferences:
Writing tone: {getattr(preferences, 'writing_tone', '') or 'not specified'}
Audience: {getattr(preferences, 'audience', '') or 'not specified'}
Topics: {getattr(preferences, 'topics', '') or 'not specified'}
Things to avoid: {getattr(preferences, 'things_to_avoid', '') or 'not specified'}
Preferred post length: {getattr(preferences, 'preferred_post_length', 220)} characters where relevant
Example posts / voice references:
{examples or '(none)'}

User brief:
{brief}

Additional instruction:
{instruction or '(none)'}

Optional link to incorporate naturally when appropriate: {link_url or '(none)'}
X thread length requested: {thread_length}. For non-X platforms always return one post/caption.

Do not invent facts, figures, quotes, links, names or events not present in the brief or instructions. Preserve the user's substantive claims. Adapt format and wording to each platform rather than copying one version four times.
"""
    raw = _responses(prompt)
    data = _parse_json(raw)
    if not isinstance(data, dict):
        raise RuntimeError("AI response was not a JSON object")
    result: dict[str, Any] = {}
    for platform in selected:
        obj = data.get(platform, {})
        posts = obj.get("posts") if isinstance(obj, dict) else None
        if not isinstance(posts, list) or not posts:
            raise RuntimeError(f"AI did not return a {platform} draft")
        posts = [str(x).strip() for x in posts if str(x).strip()]
        if platform == "x":
            expected = thread_length if thread_length in {3, 5} else 1
            posts = posts[:expected]
            while len(posts) < expected:
                posts.append("")
            for text in posts:
                if len(text) > 280:
                    raise RuntimeError("AI returned an X post over 280 characters; rewrite and try again")
        else:
            posts = posts[:1]
        result[platform] = {"posts": posts}
    return result


def rewrite_variant(*, platform: str, posts: list[str], action: str, preferences: Any, instruction: str = "") -> list[str]:
    if platform not in PLATFORM_GUIDANCE:
        raise RuntimeError("Unknown platform")
    instruction = instruction.strip()
    if not instruction and action not in REWRITE_GUIDANCE:
        raise RuntimeError("Unknown rewrite action")
    rewrite_instruction = instruction or REWRITE_GUIDANCE[action]
    prompt = f"""Rewrite the following {platform} content.
Return ONLY valid JSON of the form {{"posts":["..."]}}.
{PLATFORM_GUIDANCE[platform]}
Rewrite instruction: {rewrite_instruction}
Creator tone: {getattr(preferences, 'writing_tone', '') or 'not specified'}
Audience: {getattr(preferences, 'audience', '') or 'not specified'}
Things to avoid: {getattr(preferences, 'things_to_avoid', '') or 'not specified'}

Original posts:
{json.dumps(posts, ensure_ascii=False)}

Do not introduce new factual claims. Preserve the number of posts. For X, every post must remain <=280 characters.
"""
    data = _parse_json(_responses(prompt, max_output_tokens=1200))
    new_posts = data.get("posts") if isinstance(data, dict) else None
    if not isinstance(new_posts, list) or len(new_posts) != len(posts):
        raise RuntimeError("AI returned an invalid rewrite")
    clean = [str(x).strip() for x in new_posts]
    if platform == "x" and any(len(x) > 280 for x in clean):
        raise RuntimeError("AI rewrite exceeded the X character limit")
    return clean


def propose_schedule(*, platforms: list[str], timezone_name: str, context: str = "") -> dict[str, list[dict[str, str]]]:
    now = datetime.utcnow().isoformat() + "Z"
    prompt = f"""You are a social publishing scheduler. Suggest three sensible future posting times for each requested platform.
Return ONLY valid JSON in this exact shape:
{{"x":[{{"label":"...","local_time":"YYYY-MM-DDTHH:MM"}}],"facebook":[],"instagram":[],"tiktok":[]}}
Include only requested platforms. Use timezone {timezone_name}. Current UTC time is {now}.
Prefer realistic creator posting windows and spread the options rather than placing all suggestions together. Context: {context or '(none)'}.
Do not claim the times are guaranteed to maximize engagement; they are suggested starting points.
Platforms: {', '.join(platforms)}
"""
    data = _parse_json(_responses(prompt, max_output_tokens=1200))
    if not isinstance(data, dict):
        raise RuntimeError("AI returned invalid scheduling suggestions")
    return {p: data.get(p, []) for p in platforms}
