"""Blog RSS helpers for README generation."""

from __future__ import annotations

RSS_FEED_URL = "https://notashelf.dev/rss.xml"


def fetch_latest_posts(feed_url: str = RSS_FEED_URL, *, limit: int = 5) -> str:
    """Fetch latest blog posts from RSS and render them as markdown links."""
    import feedparser

    feed = feedparser.parse(feed_url)
    entries = feed.entries[:limit]

    if not entries:
        raise RuntimeError(f"No posts found in RSS feed: {feed_url}")

    return "\n".join(f"- [{post.title}]({post.link})" for post in entries)
