"""Dartfish video embedding (same Embed URL scheme as the fencing dashboard)."""

from __future__ import annotations

import html
import os
import re
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

DARTFISH_CHANNEL_ID = os.environ.get("DARTFISH_CHANNEL_ID", "98310")
DARTFISH_COLLECTION_ID = os.environ.get("DARTFISH_COLLECTION_ID", "572153")
DARTFISH_LIMITED_ACCESS_ID = os.environ.get("DARTFISH_LIMITED_ACCESS_ID", "")

EMBED_BASE = "https://www.dartfish.tv/Embed"
SHORT_LINK_HOSTS = {"dartfi.sh", "www.dartfi.sh"}
# Share links carry the ids as CR=p<channel>c<collection>m<video>
_CR_PATTERN = re.compile(r"p(\d+)c(\d+)m(\d+)", re.IGNORECASE)
_IFRAME_SRC = re.compile(r"<iframe[^>]*\ssrc\s*=\s*[\"']([^\"']+)", re.IGNORECASE)


def dartfish_embed_url(link: str) -> str | None:
    """Embed URL for a Dartfish link or bare video id; None if it is not one.

    Accepts Dartfish's iframe embed code, an Embed URL (used as is), a
    player/share URL with ``videoId`` or ``CR`` parameters, or a numeric
    video id in the configured collection.
    """
    link = (link or "").strip()
    if not link:
        return None
    # Dartfish "Share > Embed" code pasted whole: use its iframe src
    src = _IFRAME_SRC.search(link)
    if src:
        link = html.unescape(src.group(1)).strip()
    if link.isdigit():
        return _build(DARTFISH_CHANNEL_ID, DARTFISH_COLLECTION_ID, link)

    url = urlparse(link if "://" in link else f"https://{link}")
    if not url.netloc.lower().endswith("dartfish.tv"):
        return None
    if url.path.lower().rstrip("/").endswith("/embed"):
        return link

    query = {k.lower(): v[0] for k, v in parse_qs(url.query).items()}
    # Share-link redirects (/sharing?...) carry the access id as "aid"
    access_id = query.get("limitedaccessid") or query.get("aid")
    if "videoid" in query:
        return _build(query.get("channelid", DARTFISH_CHANNEL_ID),
                      query.get("collectionid", DARTFISH_COLLECTION_ID),
                      query["videoid"], access_id)
    match = _CR_PATTERN.search(query.get("cr", ""))
    if match:
        return _build(*match.groups(), access_id)
    return None


def resolve_video_link(link: str) -> str | None:
    """Embed URL to store for what the user entered; None if it is not usable.

    Short share links (``dartfi.sh/...``) only reveal the video and access ids
    after their redirect, so they are followed once here (needs network).
    """
    link = (link or "").strip()
    host = urlparse(link if "://" in link else f"https://{link}").netloc.lower()
    if host in SHORT_LINK_HOSTS:
        link = _follow_redirect(link if "://" in link else f"https://{link}")
        if not link:
            return None
    return dartfish_embed_url(link)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # surface the 3xx so its Location can be read


_NO_REDIRECT_OPENER = build_opener(_NoRedirect)


def _follow_redirect(url: str, attempts: int = 2) -> str | None:
    """Target of a short link, read from its redirect header (the Dartfish
    page itself is not loaded)."""
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for _ in range(attempts):
        try:
            with _NO_REDIRECT_OPENER.open(request, timeout=10) as resp:
                return resp.geturl()  # no redirect: already the target
        except HTTPError as exc:
            if 300 <= exc.code < 400 and exc.headers.get("Location"):
                return urljoin(url, exc.headers["Location"])
            return None
        except (OSError, ValueError):
            continue  # transient network error: retry
    return None


def _build(channel_id: str, collection_id: str, video_id: str, limited_access_id: str | None = None) -> str:
    return f"{EMBED_BASE}?" + urlencode({
        "channelId": channel_id,
        "collectionId": collection_id,
        "videoId": video_id,
        "limitedAccessId": limited_access_id or DARTFISH_LIMITED_ACCESS_ID,
    })
