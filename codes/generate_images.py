#!/usr/bin/env python


import asyncio
import os
import aiohttp


from github_stats import Stats


def generate_output_folder() -> None:
    """
    Create the output folder if it does not already exist
    """
    try:
        os.makedirs("generated", exist_ok=True)
    except OSError as e:
        print(f"Error creating output folder: {str(e)}")


async def generate_overview(s: Stats) -> None:
    """
    Generate an SVG badge with summary statistics
    :param s: Represents user's GitHub statistics
    """
    with open("templates/overview.svg", "r") as f:
        output = f.read()

    output = output.replace("{{ name }}", await s.name)
    output = output.replace("{{ stars }}", f"{await s.stargazers:,}")
    output = output.replace("{{ forks }}", f"{await s.forks:,}")
    output = output.replace("{{ contributions }}", f"{await s.total_contributions:,}")
    changed = (await s.lines_changed)[0] + (await s.lines_changed)[1]
    output = output.replace("{{ lines_changed }}", f"{changed:,}")
    output = output.replace("{{ views }}", f"{await s.views:,}")
    output = output.replace("{{ repos }}", f"{len(await s.all_repos):,}")

    generate_output_folder()
    with open("generated/overview.svg", "w") as f:
        f.write(output)


async def generate_languages(s: Stats) -> None:
    """
    Generate an SVG badge with summary languages used
    :param s: Represents user's GitHub statistics
    """
    with open("templates/languages.svg", "r") as f:
        output = f.read()

    progress = ""
    lang_list = ""
    sorted_languages = sorted(
        (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
    )
    delay_between = 150
    for i, (lang, data) in enumerate(sorted_languages):
        color = data.get("color", "#000000")
        ratio = [0.98, 0.02] if data.get("prop", 0) > 50 else [0.99, 0.01]
        if i == len(sorted_languages) - 1:
            ratio = [1, 0]
        progress += (
            f'<span style="background-color: {color};'
            f'width: {(ratio[0] * data.get("prop", 0)):0.3f}%;'
            f'margin-right: {(ratio[1] * data.get("prop", 0)):0.3f}%;" '
            f'class="progress-item"></span>'
        )
        lang_list += f"""
<li style="animation-delay: {i * delay_between}ms;">
<svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};"
viewBox="0 0 16 16" version="1.1" width="16" height="16"><path
fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path></svg>
<span class="lang">{lang}</span>
<span class="percent">{data.get("prop", 0):0.2f}%</span>
</li>
"""

    output = output.replace(r"{{ progress }}", progress)
    output = output.replace(r"{{ lang_list }}", lang_list)

    generate_output_folder()
    with open("generated/languages.svg", "w") as f:
        f.write(output)


async def main() -> None:
    """
    Generate all badges
    """
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise Exception("A personal access token is required to proceed!")
    user = os.getenv("GITHUB_ACTOR")
    exclude_repos = os.getenv("EXCLUDED")
    exclude_repos = (
        {x.strip() for x in exclude_repos.split(",")} if exclude_repos else None
    )
    exclude_langs = os.getenv("EXCLUDED_LANGS")
    exclude_langs = (
        {x.strip() for x in exclude_langs.split(",")} if exclude_langs else None
    )
    consider_forked_repos = bool(os.getenv("COUNT_STATS_FROM_FORKS"))

    async with aiohttp.ClientSession() as session:
        s = Stats(
            user,
            access_token,
            session,
            exclude_repos=exclude_repos,
            exclude_langs=exclude_langs,
            consider_forked_repos=consider_forked_repos,
        )
        await asyncio.gather(generate_languages(s), generate_overview(s))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
