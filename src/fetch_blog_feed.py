import feedparser
import argparse

RSS_FEED_URL = "https://blog.notashelf.dev/feed.xml"
PLACEHOLDER = "{{ BLOG_POSTS_PLACEHOLDER }}"


def fetch_latest_posts():
    """Fetch the latest 5 posts from the RSS feed and return as a markdown list."""
    feed = feedparser.parse(RSS_FEED_URL)
    posts = feed.entries[:5]

    markdown_list = "\n".join(f"- [{post.title}]({post.link})" for post in posts)
    return markdown_list


def update_readme(output_file):
    """Replace the placeholder in the given output file with the latest blog posts."""
    posts_markdown = fetch_latest_posts()

    with open(output_file, "r", encoding="utf-8") as file:
        content = file.read()

    updated_content = content.replace(PLACEHOLDER, posts_markdown)

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(updated_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update README with latest blog posts")
    parser.add_argument("output_file", help="Path to the output markdown file")
    args = parser.parse_args()

    update_readme(args.output_file)
