#!/usr/bin/python3

import asyncio
import json
import os
import re
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Dict, List, Mapping, Optional, Set, Tuple

import aiohttp
import requests
import yaml

AUTHORSHIP_DAYS = 90
AUTHORSHIP_REQUEST_LIMIT = 1800
LINGUIST_REVISION = "681a3171a3f8d1ccab93e646e7753cba42186915"
LINGUIST_URL = (
    "https://raw.githubusercontent.com/github-linguist/linguist/"
    f"{LINGUIST_REVISION}/lib/linguist/languages.yml"
)
LINGUIST_HEURISTICS_URL = LINGUIST_URL.replace("languages.yml", "heuristics.yml")

REQUEST_RETRIES = 8
RETRYABLE_HTTP_STATUSES = {202, 429, 500, 502, 503, 504}
RETRYABLE_GRAPHQL_HTTP_STATUSES = RETRYABLE_HTTP_STATUSES
RESPONSE_PREVIEW_CHARS = 300


def _preview_response(text: str) -> str:
    return text.replace("\n", " ")[:RESPONSE_PREVIEW_CHARS]


# Main classes
class Queries(object):
    """
    Class with functions to query the GitHub GraphQL (v4) API and the REST (v3)
    API. Also includes functions to dynamically generate GraphQL queries.
    """

    def __init__(
        self,
        username: str,
        access_token: str,
        session: aiohttp.ClientSession,
        max_connections: int = 10,
    ):
        self.username = username
        self.access_token = access_token
        self.session = session
        self.semaphore = asyncio.Semaphore(max_connections)
        self.authored_requests = 0
        self._request_lock = asyncio.Lock()
        self._next_request = 0.0
        self._next_search = 0.0

    async def _pace_authored_request(self, search: bool) -> None:
        async with self._request_lock:
            if self.authored_requests >= AUTHORSHIP_REQUEST_LIMIT:
                raise RuntimeError("Authored changes exceeded the 1,800-request budget")
            now = time.monotonic()
            ready = max(self._next_request, self._next_search if search else now)
            await asyncio.sleep(max(0, ready - now))
            now = time.monotonic()
            self._next_request = now + 0.2
            if search:
                self._next_search = now + 2.1
            self.authored_requests += 1

    async def authored_rest(
        self,
        path: str,
        params: Optional[Dict] = None,
        *,
        accept: str = "application/vnd.github+json",
    ) -> Dict | List | bytes:
        """Share the request budget and pace GitHub searches separately."""
        search = path == "/search/commits"
        for attempt in range(3):
            await self._pace_authored_request(search)
            try:
                async with self.session.get(
                    f"https://api.github.com{path}",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": accept,
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    params=params,
                ) as response:
                    if response.status == 200 and accept == "application/vnd.github.diff":
                        return await response.read()
                    text = await response.text()
                    if response.status == 403 and path.startswith("/repos/"):
                        async with self.session.get(
                            f"https://api.github.com{path}",
                            headers={
                                "Accept": accept,
                                "X-GitHub-Api-Version": "2022-11-28",
                            },
                            params=params,
                        ) as public_response:
                            if (
                                public_response.status == 200
                                and accept == "application/vnd.github.diff"
                            ):
                                return await public_response.read()
                            public_text = await public_response.text()
                            if public_response.status == 200:
                                return json.loads(public_text)
                            raise RuntimeError(
                                f"Authored changes API failed: {path}: HTTP {response.status}: "
                                f"{_preview_response(text)}; anonymous fallback returned HTTP "
                                f"{public_response.status}: {_preview_response(public_text)}"
                            )
                    if response.status == 200:
                        return json.loads(text)
                    if response.status not in RETRYABLE_HTTP_STATUSES:
                        raise RuntimeError(
                            f"Authored changes API failed: {path}: HTTP {response.status}: "
                            f"{_preview_response(text)}"
                        )
                    retry_after = response.headers.get("Retry-After", "0")
                    delay = max(2**attempt, float(retry_after))
                    if delay > 30:
                        raise RuntimeError("GitHub rate limit exceeds the generation deadline")
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
                delay = 2**attempt
            await asyncio.sleep(delay)
        raise RuntimeError(f"Authored changes API failed after retries: {path}")

    async def query(self, generated_query: str) -> Dict:
        """
        Make a request to the GraphQL API using the authentication token from
        the environment
        :param generated_query: string query to be sent to the API
        :return: decoded GraphQL JSON output
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        last_error: Exception | None = None

        for attempt in range(REQUEST_RETRIES):
            try:
                async with self.semaphore:
                    response = await self.session.post(
                        "https://api.github.com/graphql",
                        headers=headers,
                        json={"query": generated_query},
                    )
                text = await response.text()
                if response.status in RETRYABLE_GRAPHQL_HTTP_STATUSES:
                    last_error = RuntimeError(f"GitHub GraphQL returned {response.status}")
                    await asyncio.sleep(2**attempt)
                    continue
                if response.status >= 400:
                    raise RuntimeError(
                        "GitHub GraphQL request failed "
                        f"with HTTP {response.status}: {_preview_response(text)}"
                    )
                try:
                    result = json.loads(text)
                    if result.get("errors"):
                        raise RuntimeError(f"GitHub GraphQL errors: {result['errors']}")
                    return result
                except json.JSONDecodeError:
                    last_error = RuntimeError(
                        "GitHub GraphQL returned non-JSON response "
                        f"with HTTP {response.status}: {_preview_response(text)}"
                    )
                    print(last_error)
                    await asyncio.sleep(2**attempt)
                    continue
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                print("aiohttp failed for GraphQL query")

            try:
                async with self.semaphore:
                    response = requests.post(
                        "https://api.github.com/graphql",
                        headers=headers,
                        json={"query": generated_query},
                        timeout=30,
                    )
                if response.status_code in RETRYABLE_GRAPHQL_HTTP_STATUSES:
                    last_error = RuntimeError(
                        f"GitHub GraphQL fallback returned {response.status_code}"
                    )
                    await asyncio.sleep(2**attempt)
                    continue
                if response.status_code >= 400:
                    raise RuntimeError(
                        "GitHub GraphQL fallback request failed "
                        f"with HTTP {response.status_code}: {_preview_response(response.text)}"
                    )
                try:
                    result = response.json()
                    if result.get("errors"):
                        raise RuntimeError(f"GitHub GraphQL errors: {result['errors']}")
                    return result
                except requests.JSONDecodeError:
                    last_error = RuntimeError(
                        "GitHub GraphQL fallback returned non-JSON response "
                        f"with HTTP {response.status_code}: {_preview_response(response.text)}"
                    )
                    print(last_error)
                    await asyncio.sleep(2**attempt)
            except requests.RequestException as exc:
                last_error = exc
                print("requests failed for GraphQL query")

        raise RuntimeError("GitHub GraphQL query failed after retries") from last_error

    async def query_rest(self, path: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the REST API
        :param path: API path to query
        :param params: Query parameters to be passed to the API
        :return: deserialized REST JSON output
        """

        for _ in range(60):
            headers = {
                "Authorization": f"token {self.access_token}",
            }
            if params is None:
                params = dict()
            if path.startswith("/"):
                path = path[1:]
            try:
                async with self.semaphore:
                    r = await self.session.get(
                        f"https://api.github.com/{path}",
                        headers=headers,
                        params=tuple(params.items()),
                    )
                text = await r.text()
                if r.status in RETRYABLE_HTTP_STATUSES:
                    # print(f"{path} returned 202. Retrying...")
                    print(f"A path returned {r.status}. Retrying...")
                    await asyncio.sleep(2)
                    continue
                if r.status >= 400:
                    print(
                        "GitHub REST request failed "
                        f"with HTTP {r.status}: {_preview_response(text)}"
                    )
                    return dict()

                result = json.loads(text)
                if result is not None:
                    return result
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
                print("aiohttp failed for rest query")
                # Fall back on non-async requests
                try:
                    async with self.semaphore:
                        r = requests.get(
                            f"https://api.github.com/{path}",
                            headers=headers,
                            params=tuple(params.items()),
                            timeout=30,
                        )
                except requests.RequestException:
                    print("requests failed for rest query")
                    await asyncio.sleep(2)
                    continue

                if r.status_code in RETRYABLE_HTTP_STATUSES:
                    print(f"A path returned {r.status_code}. Retrying...")
                    await asyncio.sleep(2)
                    continue
                if r.status_code >= 400:
                    print(
                        "GitHub REST fallback request failed "
                        f"with HTTP {r.status_code}: {_preview_response(r.text)}"
                    )
                    return dict()
                try:
                    return r.json()
                except requests.JSONDecodeError:
                    print(
                        "GitHub REST fallback returned non-JSON response "
                        f"with HTTP {r.status_code}: {_preview_response(r.text)}"
                    )
                    await asyncio.sleep(2)
                    continue
        # print(f"There were too many 202s. Data for {path} will be incomplete.")
        print("There were too many 202s. Data for this repository will be incomplete.")
        return dict()

    @staticmethod
    def repos_overview(
        username: str, contrib_cursor: Optional[str] = None, owned_cursor: Optional[str] = None
    ) -> str:
        """
        :return: GraphQL query with overview of user repositories
        """
        return f"""{{
  user(login: {json.dumps(username)}) {{
    login,
    name,
    repositories(
        first: 100,
        orderBy: {{
            field: UPDATED_AT,
            direction: DESC
        }},
        after: {"null" if owned_cursor is None else '"' + owned_cursor + '"'}
    ) {{
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        nameWithOwner
        isFork
        stargazers {{
          totalCount
        }}
        forkCount
      }}
    }}
    repositoriesContributedTo(
        first: 100,
        includeUserRepositories: false,
        orderBy: {{
            field: UPDATED_AT,
            direction: DESC
        }},
        contributionTypes: [
            COMMIT,
            PULL_REQUEST,
            REPOSITORY,
            PULL_REQUEST_REVIEW
        ]
        after: {"null" if contrib_cursor is None else '"' + contrib_cursor + '"'}
    ) {{
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        nameWithOwner
        isFork
        stargazers {{
          totalCount
        }}
        forkCount
      }}
    }}
  }}
}}
"""

    @staticmethod
    def contrib_years(username: str) -> str:
        """
        :return: GraphQL query to get all years the user has been a contributor
        """
        return f"""
query {{
  user(login: {json.dumps(username)}) {{
    contributionsCollection {{
      contributionYears
    }}
  }}
}}
"""

    @staticmethod
    def contribs_by_year(year: str) -> str:
        """
        :param year: year to query for
        :return: portion of a GraphQL query with desired info for a given year
        """
        return f"""
    year{year}: contributionsCollection(
        from: "{year}-01-01T00:00:00Z",
        to: "{int(year) + 1}-01-01T00:00:00Z"
    ) {{
      contributionCalendar {{
        totalContributions
      }}
    }}
"""

    @classmethod
    def all_contribs(cls, username: str, years: List[str]) -> str:
        """
        :param years: list of years to get contributions for
        :return: query to retrieve contribution information for all user years
        """
        by_years = "\n".join(map(cls.contribs_by_year, years))
        return f"""
query {{
  user(login: {json.dumps(username)}) {{
    {by_years}
  }}
}}
"""


class LanguageClassifier:
    """Classify changed files with Linguist filename and content rules."""

    def __init__(self, definitions: Dict, heuristics: Dict):
        self.definitions = definitions
        self.heuristics = heuristics
        self.filenames: Dict[str, Set[str]] = {}
        self.extensions: Dict[str, Set[str]] = {}
        for name, data in definitions.items():
            group = data.get("group", name)
            for filename in data.get("filenames", []):
                self.filenames.setdefault(filename, set()).add(group)
            for extension in data.get("extensions", []):
                self.extensions.setdefault(extension, set()).add(group)

    @classmethod
    async def load(cls, session: aiohttp.ClientSession) -> "LanguageClassifier":
        metadata = []
        for url, label in (
            (LINGUIST_URL, "metadata"),
            (LINGUIST_HEURISTICS_URL, "heuristics"),
        ):
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Linguist {label} fetch failed: HTTP {response.status}")
                metadata.append(yaml.safe_load(await response.text()))
        definitions, heuristics = metadata
        return cls(definitions, heuristics)

    def _matches(self, rule: Dict, sample: str) -> bool:
        # Absence in a diff fragment cannot prove absence in the complete file.
        if "negative_pattern" in rule:
            return False
        if "and" in rule:
            return all(self._matches(part, sample) for part in rule["and"])
        pattern = rule.get("pattern")
        if "named_pattern" in rule:
            pattern = self.heuristics["named_patterns"][rule["named_pattern"]]
        if not pattern:
            return False
        return self._matches_pattern(pattern, sample)

    @staticmethod
    def _matches_pattern(pattern: str | List[str], sample: str) -> bool:
        patterns = pattern if isinstance(pattern, list) else [pattern]
        for expression in patterns:
            try:
                if re.search(expression, sample, re.MULTILINE):
                    return True
            except re.error:
                # Ruby-only regex constructs are inconclusive, not a language fallback.
                continue
        return False

    @staticmethod
    def _sample(patch: str, removed: bool) -> str:
        lines = []
        in_hunk = False
        for line in patch.splitlines():
            if line.startswith("@@"):
                in_hunk = True
                lines.append(line.rsplit("@@", 1)[-1].lstrip())
            elif in_hunk and (line.startswith(" ") or line.startswith("-" if removed else "+")):
                lines.append(line[1:])
        return "\n".join(lines)

    def _filename_candidates(self, basename: str) -> Set[str]:
        if basename in self.filenames:
            return self.filenames[basename]
        # Match the longest registered suffix, such as .blade.php before .php.
        for index, character in enumerate(basename):
            if character == "." and basename[index:] in self.extensions:
                return self.extensions[basename[index:]]
        return set()

    def _groups(self, languages: Mapping[str, int] | Set[str] | List[str]) -> Set[str]:
        names = languages.keys() if isinstance(languages, Mapping) else languages
        return {
            self.definitions[name].get("group", name) for name in names if name in self.definitions
        }

    def _content_candidates(self, basename: str, sample: str, candidates: Set[str]) -> Set[str]:
        if not sample:
            return set()
        for block in self.heuristics.get("disambiguations", []):
            if not any(basename.endswith(ext) for ext in block["extensions"]):
                continue
            for rule in block["rules"]:
                if self._matches(rule, sample):
                    languages = rule["language"]
                    languages = languages if isinstance(languages, list) else [languages]
                    matches = self._groups(languages) & candidates
                    if len(matches) == 1:
                        return matches
        return set()

    def classify(
        self,
        filename: str,
        patch: str = "",
        *,
        removed: bool = False,
        repository_languages: Optional[Mapping[str, int]] = None,
    ) -> Tuple[str, Optional[str]]:
        basename = PurePosixPath(filename).name
        candidates = self._filename_candidates(basename)
        if not candidates:
            return "Unclassified", None
        if len(candidates) != 1:
            matches = self._content_candidates(basename, self._sample(patch, removed), candidates)
            if matches:
                candidates = matches
            elif repository_languages:
                scores = {
                    candidate: sum(
                        size
                        for language, size in repository_languages.items()
                        if self.definitions.get(language, {}).get("group", language) == candidate
                    )
                    for candidate in candidates
                }
                highest = max(scores.values(), default=0)
                if highest:
                    candidates = {
                        candidate for candidate, score in scores.items() if score == highest
                    }
        if len(candidates) != 1:
            if repository_languages is None:
                return "Ambiguous", None
            name = sorted(candidates)[0]
            return name, self.definitions[name].get("color")
        name = next(iter(candidates))
        return name, self.definitions[name].get("color")


class Stats(object):
    """
    Retrieve and store statistics about GitHub usage.
    """

    def __init__(
        self,
        username: str,
        access_token: str,
        session: aiohttp.ClientSession,
        exclude_repos: Optional[Set] = None,
        exclude_langs: Optional[Set] = None,
        consider_forked_repos: bool = False,
    ):
        self.username = username
        self._exclude_repos = set() if exclude_repos is None else exclude_repos
        self._exclude_langs = set() if exclude_langs is None else exclude_langs
        self._consider_forked_repos = consider_forked_repos
        self.queries = Queries(username, access_token, session)

        self._name = None
        self._stargazers = None
        self._forks = None
        self._total_contributions = None
        self._languages = None
        self._repos = None
        self._fork_repos = set()
        self._lines_changed = None
        self._views = None
        self._authored_repos = set()
        self.authored_commits = 0
        self.authored_repo_count = 0
        self.authored_end = datetime.now(timezone.utc).date() - timedelta(days=1)
        self.authored_start = self.authored_end - timedelta(days=AUTHORSHIP_DAYS - 1)
        self._language_context: Dict[str, Dict[str, int]] = {}
        self._language_context_lock = asyncio.Lock()

    async def to_str(self) -> str:
        """
        :return: summary of all available statistics
        """
        languages = await self.languages_proportional
        formatted_languages = "\n  - ".join([f"{k}: {v:0.4f}%" for k, v in languages.items()])
        lines_changed = await self.lines_changed
        return f"""Name: {await self.name}
Stargazers: {await self.stargazers:,}
Forks: {await self.forks:,}
All-time contributions: {await self.total_contributions:,}
Repositories with contributions: {len(await self.all_repos)}
Authored lines added, {self.authored_start}..{self.authored_end}: {lines_changed[0]:,}
Authored lines deleted, same period: {lines_changed[1]:,}
Authored lines changed, same period: {lines_changed[0] + lines_changed[1]:,}
Project page views: {await self.views:,}
Languages:
  - {formatted_languages}"""

    async def _overview_pages(self):
        cursors = {"repositories": None, "repositoriesContributedTo": None}
        pending = set(cursors)
        while pending:
            result = await self.queries.query(
                Queries.repos_overview(
                    self.username,
                    owned_cursor=cursors["repositories"],
                    contrib_cursor=cursors["repositoriesContributedTo"],
                )
            )
            user = result["data"]["user"]
            nodes = {"repositories": [], "repositoriesContributedTo": []}
            for connection in tuple(pending):
                page = user[connection]
                nodes[connection] = page["nodes"]
                info = page["pageInfo"]
                if info["hasNextPage"]:
                    cursors[connection] = info["endCursor"]
                else:
                    pending.remove(connection)
            yield user, nodes["repositories"], nodes["repositoriesContributedTo"]

    def _summarize_repositories(self, owned: Dict, contributed: Dict) -> Tuple:
        repos, ignored, fork_repos = set(), set(), set()
        stars = forks = 0
        excluded = {name.casefold() for name in self._exclude_repos}
        for name, repo in (contributed | owned).items():
            if name.casefold() in excluded:
                continue
            if repo["isFork"]:
                fork_repos.add(name)
            if name not in owned and not self._consider_forked_repos:
                ignored.add(name)
                continue
            if repo["isFork"] and not self._consider_forked_repos:
                continue
            repos.add(name)
            stars += repo["stargazers"]["totalCount"]
            forks += repo["forkCount"]
        return repos, ignored, fork_repos, stars, forks

    async def get_stats(self) -> None:
        owned, contributed = {}, {}
        async for user, owned_nodes, contributed_nodes in self._overview_pages():
            name = user["name"]
            if name is None:
                name = user["login"]
            owned.update((repo["nameWithOwner"], repo) for repo in owned_nodes)
            contributed.update((repo["nameWithOwner"], repo) for repo in contributed_nodes)
        repos, ignored, fork_repos, stars, forks = self._summarize_repositories(owned, contributed)
        self._name = name
        self._repos = repos
        self._ignored_repos = ignored
        self._fork_repos = fork_repos
        self._stargazers = stars
        self._forks = forks

    async def _search_authored(self, start: date, end: date) -> List[Dict]:
        query = (
            f"author:{self.username} merge:false "
            f"committer-date:{start.isoformat()}..{end.isoformat()}"
        )
        params = {"q": query, "per_page": 100, "page": 1, "sort": "committer-date", "order": "asc"}
        first = await self.queries.authored_rest("/search/commits", params)
        total = first["total_count"]
        if total > 1000 or first["incomplete_results"]:
            if start == end:
                raise RuntimeError(f"Cannot completely enumerate authored commits on {start}")
            middle = start + (end - start) // 2
            return await self._search_authored(start, middle) + await self._search_authored(
                middle + timedelta(days=1), end
            )
        items = list(first["items"])
        for page in range(2, (total + 99) // 100 + 1):
            result = await self.queries.authored_rest("/search/commits", {**params, "page": page})
            if result["incomplete_results"] or result["total_count"] != total:
                raise RuntimeError(
                    "Authored commit search changed or became incomplete while paging"
                )
            items.extend(result["items"])
        if len(items) != total:
            raise RuntimeError("Authored commit search returned a truncated result set")
        return items

    async def _fork_authored(self) -> List[Dict]:
        # Commit search does not index every fork. Enumerate known forks directly.
        if self._repos is None:
            await self.get_stats()
        items = []
        for repo in sorted(self._fork_repos):
            page = 1
            while True:
                batch = await self.queries.authored_rest(
                    f"/repos/{repo}/commits",
                    {
                        "author": self.username,
                        "since": f"{self.authored_start}T00:00:00Z",
                        "until": f"{self.authored_end}T23:59:59Z",
                        "per_page": 100,
                        "page": page,
                    },
                )
                for item in batch:
                    if len(item["parents"]) <= 1:
                        items.append({**item, "repository": {"full_name": repo}})
                if len(batch) < 100:
                    break
                page += 1
        return items

    @staticmethod
    async def _raw_diff_numstat(diff: bytes, sha: str) -> bytes:
        # --numstat only reads the diff; it does not apply it or touch the checkout.
        # An isolated cwd also prevents git apply's subdirectory filtering.
        with tempfile.TemporaryDirectory(prefix="profile-diff-") as directory:
            process = await asyncio.create_subprocess_exec(
                "git",
                "apply",
                "--numstat",
                "-z",
                cwd=directory,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            communication = asyncio.create_task(process.communicate(diff))
            try:
                output, errors = await asyncio.wait_for(asyncio.shield(communication), timeout=30)
            except BaseException:
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                # Drain the pipes before removing the temporary directory.
                await communication
                raise
        if process.returncode:
            raise RuntimeError(
                f"Cannot read raw diff for commit {sha}: "
                f"{_preview_response(errors.decode('utf-8', errors='replace'))}"
            )
        return output

    @staticmethod
    def _parse_numstat(output: bytes) -> Dict[str, Tuple[int, int]]:
        counts = {}
        for row in output.split(b"\0")[:-1]:
            added, deleted, filename = row.split(b"\t", 2)
            name = filename.decode("utf-8", errors="surrogateescape")
            # Binary entries have no line counts, matching GitHub's zero line stats.
            if added == deleted == b"-":
                counts[name] = (0, 0)
            else:
                counts[name] = (int(added), int(deleted))
        return counts

    async def _diff_files(self, repo: str, sha: str, files: List[Dict]) -> List[Dict]:
        """Recover per-file counts when GitHub omits stats for large changed files."""
        diff = await self.queries.authored_rest(
            f"/repos/{repo}/commits/{sha}", accept="application/vnd.github.diff"
        )
        counts = self._parse_numstat(await self._raw_diff_numstat(diff, sha))
        return [
            {
                **file,
                "additions": counts[file["filename"]][0],
                "deletions": counts[file["filename"]][1],
            }
            for file in files
        ]

    @staticmethod
    def _file_totals(files: List[Dict]) -> Tuple[int, int]:
        return sum(file["additions"] for file in files), sum(file["deletions"] for file in files)

    async def _commit_files(self, repo: str, sha: str) -> List[Dict]:
        files = []
        totals = None
        for page in range(1, 31):
            result = await self.queries.authored_rest(
                f"/repos/{repo}/commits/{sha}", {"per_page": 100, "page": page}
            )
            if totals is None:
                totals = result["stats"]["additions"], result["stats"]["deletions"]
            batch = result["files"]
            files.extend(batch)
            if len(batch) < 100:
                break
        else:
            # GitHub returns no more than 3,000 files; an exact cap is not provably complete.
            raise RuntimeError(f"Commit {sha} reaches GitHub's 3,000-file cap")
        if self._file_totals(files) != totals:
            files = await self._diff_files(repo, sha, files)
            if self._file_totals(files) != totals:
                raise RuntimeError(
                    f"Incomplete changed-file totals for commit {sha}, including raw diff"
                )
        return files

    async def _repository_languages(self, repo: str) -> Dict[str, int]:
        async with self._language_context_lock:
            if repo not in self._language_context:
                result = await self.queries.authored_rest(f"/repos/{repo}/languages")
                self._language_context[repo] = {
                    language: int(size) for language, size in result.items()
                }
            return self._language_context[repo]

    def _select_authored_commits(self, items: List[Dict]) -> Tuple[Dict[str, str], Set[str]]:
        commits = {}
        excluded = {repo.casefold() for repo in self._exclude_repos}
        authored_repos = set()
        for item in items:
            repo = item["repository"]["full_name"]
            if repo.casefold() in excluded:
                continue
            authored_repos.add(repo)
            commits.setdefault(item["sha"], repo)
        if self.queries.authored_requests + len(commits) > AUTHORSHIP_REQUEST_LIMIT:
            raise RuntimeError(
                "Complete authored history for this window exceeds the request budget"
            )
        return commits, authored_repos

    async def _collect_authored_changes(
        self, commits: Dict[str, str], classifier: LanguageClassifier
    ) -> Tuple[Dict, Tuple[int, int]]:
        excluded_languages = {lang.casefold() for lang in self._exclude_langs}

        languages = {}
        additions = deletions = 0
        queue = asyncio.Queue()
        for sha, repo in commits.items():
            queue.put_nowait((sha, repo))

        async def collect():
            nonlocal additions, deletions
            while not queue.empty():
                sha, repo = queue.get_nowait()
                for file in await self._commit_files(repo, sha):
                    additions += file["additions"]
                    deletions += file["deletions"]
                    changed = file["additions"] + file["deletions"]
                    if not changed:
                        continue
                    patch = file.get("patch") or ""
                    removed = file["status"] == "removed"
                    name, color = classifier.classify(file["filename"], patch, removed=removed)
                    if name == "Ambiguous":
                        context = await self._repository_languages(repo)
                        name, color = classifier.classify(
                            file["filename"], patch, removed=removed, repository_languages=context
                        )
                    if name.casefold() in excluded_languages:
                        continue
                    data = languages.setdefault(name, {"size": 0, "color": color})
                    data["size"] += changed

        async with asyncio.TaskGroup() as workers:
            for _ in range(2):
                workers.create_task(collect())
        total = sum(data["size"] for data in languages.values())
        for data in languages.values():
            data["prop"] = 100 * data["size"] / total
        return languages, (additions, deletions)

    async def get_authored_stats(self) -> None:
        """Collect non-merge authored changes committed in the stated 90-day window."""
        if self._languages is not None:
            return
        items = await self._search_authored(self.authored_start, self.authored_end)
        items = items + await self._fork_authored()
        commits, authored_repos = self._select_authored_commits(items)
        classifier = await LanguageClassifier.load(self.queries.session)
        languages, lines_changed = await self._collect_authored_changes(commits, classifier)
        self._languages = languages
        self._lines_changed = lines_changed
        self._authored_repos = authored_repos
        self.authored_commits = len(commits)
        self.authored_repo_count = len(authored_repos)
        print(
            f"Authored changes: {self.authored_start}..{self.authored_end}; "
            f"{len(commits):,} unique non-merge commits in {len(authored_repos):,} repositories; "
            f"{self.queries.authored_requests}/{AUTHORSHIP_REQUEST_LIMIT} REST requests."
        )

    @property
    async def name(self) -> str:
        """
        :return: GitHub user's name (e.g., Jacob Strieb)
        """
        if self._name is not None:
            return self._name
        await self.get_stats()
        assert self._name is not None
        return self._name

    @property
    async def stargazers(self) -> int:
        """
        :return: total number of stargazers on user's repos
        """
        if self._stargazers is not None:
            return self._stargazers
        await self.get_stats()
        assert self._stargazers is not None
        return self._stargazers

    @property
    async def forks(self) -> int:
        """
        :return: total number of forks on user's repos
        """
        if self._forks is not None:
            return self._forks
        await self.get_stats()
        assert self._forks is not None
        return self._forks

    @property
    async def languages(self) -> Dict:
        """
        :return: summary of languages used by the user
        """
        if self._languages is not None:
            return self._languages
        await self.get_authored_stats()
        assert self._languages is not None
        return self._languages

    @property
    async def languages_proportional(self) -> Dict:
        """
        :return: summary of languages used by the user, with proportional usage
        """
        if self._languages is None:
            await self.get_authored_stats()
            assert self._languages is not None

        return {k: v["prop"] for (k, v) in self._languages.items()}

    @property
    async def repos(self) -> List[str]:
        """
        :return: list of names of user's repos
        """
        if self._repos is not None:
            return self._repos
        await self.get_stats()
        assert self._repos is not None
        return self._repos

    @property
    async def all_repos(self) -> List[str]:
        """
        :return: list of names of user's repos with contributed repos included
                irrespective of whether the ignore flag is set or not
        """
        if self._repos is not None and self._ignored_repos is not None:
            return self._repos | self._ignored_repos | self._authored_repos
        await self.get_stats()
        assert self._repos is not None
        assert self._ignored_repos is not None
        return self._repos | self._ignored_repos | self._authored_repos

    @property
    async def total_contributions(self) -> int:
        """
        :return: count of user's total contributions as defined by GitHub
        """
        if self._total_contributions is not None:
            return self._total_contributions

        self._total_contributions = 0
        years = (await self.queries.query(Queries.contrib_years(self.username)))["data"]["user"][
            "contributionsCollection"
        ]["contributionYears"]
        by_year = (await self.queries.query(Queries.all_contribs(self.username, years)))["data"][
            "user"
        ].values()
        for year in by_year:
            self._total_contributions += year["contributionCalendar"]["totalContributions"]
        return self._total_contributions

    @property
    async def lines_changed(self) -> Tuple[int, int]:
        """Return authored non-merge additions/deletions in the stated 90-day window."""
        await self.get_authored_stats()
        assert self._lines_changed is not None
        return self._lines_changed

    @property
    async def views(self) -> int:
        """
        Note: only returns views for the last 14 days (as-per GitHub API)
        :return: total number of page views the user's projects have received
        """
        if self._views is not None:
            return self._views

        total = 0
        for repo in await self.repos:
            r = await self.queries.query_rest(f"/repos/{repo}/traffic/views")
            for view in r.get("views", []):
                total += view["count"]

        self._views = total
        return total


# Main Function


async def main() -> None:
    """
    Used mostly for testing; this module is not usually run standalone
    """
    access_token = os.getenv("ACCESS_TOKEN")
    user = os.getenv("PROFILE_USERNAME")
    if not user:
        raise RuntimeError("PROFILE_USERNAME is required to proceed")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        s = Stats(user, access_token, session)
        print(await s.to_str())


if __name__ == "__main__":
    asyncio.run(main())
