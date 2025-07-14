import feedparser

RSS_FEED_URL = "https://notashelf.dev/rss.xml"
PLACEHOLDER = "{{ BLOG_POSTS_PLACEHOLDER }}"


def fetch_latest_posts():
    feed = feedparser.parse(RSS_FEED_URL)
    posts = feed.entries[:5]
    markdown_list = "\n".join(f"- [{post.title}]({post.link})" for post in posts)
    return markdown_list


def update_readme(output_file):
    posts_markdown = fetch_latest_posts()
    with open(output_file, encoding="utf-8") as file:
        content = file.read()
    updated_content = content.replace(PLACEHOLDER, posts_markdown)
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(updated_content)
