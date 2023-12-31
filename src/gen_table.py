import json
import argparse


def generate_markdown_table(json_file):
    with open(json_file, "r") as file:
        data = json.load(file)

    table = ""

    for category, items in data.items():
        table += f"| **{category}** |\n"
        table += "| --- |\n"

        projects = ""
        for item in items:
            projects += f"[{item['title']}]({item['link']}) - {item['description']}<br>"

        table += f"| • {projects} |\n\n"

    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a Markdown table from a JSON file."
    )
    parser.add_argument("file_path", type=str, help="Path to the JSON file")

    args = parser.parse_args()
    json_file_path = args.file_path

    markdown_table = generate_markdown_table(json_file_path)
    print(markdown_table)
