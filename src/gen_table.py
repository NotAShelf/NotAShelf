import json
import argparse


def generate_markdown_table(json_file):
    with open(json_file, "r") as file:
        data = json.load(file)

    nix_projects = []
    bash_go_projects = []

    for category, items in data.items():
        if category == "Nix":
            for item in items:
                nix_projects.append(
                    f"• [{item['title']}]({item['link']}) - {item['description']}"
                )
        elif category == "Bash, Go, Python, Typescript, Java, JS":
            for item in items:
                bash_go_projects.append(
                    f"• [{item['title']}]({item['link']}) - {item['description']}"
                )

    nix_content = "<br>".join(nix_projects)
    bash_go_content = "<br>".join(bash_go_projects)

    table = "| **Nix** | **Bash, Go, Python, Typescript, Java, JS** |\n"
    table += "| --- | --- |\n"
    table += f"| {nix_content} | {bash_go_content} |\n"

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
