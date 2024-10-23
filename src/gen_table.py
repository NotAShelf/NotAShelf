import json
import argparse
import os


def generate_markdown_table(json_file):
    # check if file exists
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"The file {json_file} does not exist.")

    with open(json_file, "r") as file:
        data = json.load(file)

    project_categories = {"Nix": [], "Go, Rust, Python, JavaScript, TypeScript": []}

    # iterate through each category and project in the json data
    for category, items in data.items():
        if category in project_categories:
            project_categories[category].extend(
                f"• [{item['title']}]({item['link']}) - {item['description']}"
                for item in items
            )

    # convert project lists to <br> separated strings
    nix_content = "<br>".join(project_categories["Nix"])
    other_content = "<br>".join(
        project_categories["Go, Rust, Python, JavaScript, TypeScript"]
    )

    # generate markdown table
    table = (
        "| **Nix** | **Go, Rust, Python, JavaScript, TypeScript** |\n"
        "| --- | --- |\n"
        f"| {nix_content} | {other_content} |\n"
    )

    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a Markdown table from a JSON file."
    )
    parser.add_argument("file_path", type=str, help="Path to the JSON file")
    args = parser.parse_args()

    json_file_path = args.file_path

    try:
        markdown_table = generate_markdown_table(json_file_path)
        print(markdown_table)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
