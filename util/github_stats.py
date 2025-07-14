#!/usr/bin/python3

import asyncio
import os

import aiohttp
import requests


class Queries:
    def __init__(self, username: str, access_token: str,
                 session: aiohttp.ClientSession, max_connections: int = 10):
        self.username = username
        self.access_token = access_token
        self.session = session
        self.semaphore = asyncio.Semaphore(max_connections)

    async def query(self, generated_query: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        try:
            async with self.semaphore:
                r = await self.session.post("https://api.github.com/graphql",
                                            headers=headers,
                                            json={"query": generated_query})
            return await r.json()
        except Exception as e:
            print("aiohttp failed for GraphQL query")
            print(e)
            async with self.semaphore:
                r = requests.post("https://api.github.com/graphql",
                                  headers=headers,
                                  json={"query": generated_query})
                return r.json()

    async def query_rest(self, path: str, params: dict | None = None) -> dict:
        for _ in range(60):
            headers = {
                "Authorization": f"token {self.access_token}",
            }
            if params is None:
                params = {}
            if path.startswith("/"):
                path = path[1:]
            try:
                async with self.semaphore:
                    r = await self.session.get(f"https://api.github.com/{path}",
                                               headers=headers,
                                               params=tuple(params.items()))
                if r.status == 202:
                    print("A path returned 202. Retrying...")
                    await asyncio.sleep(2)
                    continue

                result = await r.json()
                if result is not None:
                    return result
            except Exception as e:
                print("aiohttp failed for rest query")
                print(e)
                async with self.semaphore:
                    r = requests.get(f"https://api.github.com/{path}",
                                     headers=headers,
                                     params=tuple(params.items()))
                    if r.status_code == 202:
                        print("A path returned 202. Retrying...")
                        await asyncio.sleep(2)
                        continue
                    elif r.status_code == 200:
                        return r.json()
        print("There were too many 202s. Data for this repository will be incomplete.")
        return {}

    @staticmethod
    def repos_overview(contrib_cursor: str | None = None,
                       owned_cursor: str | None = None) -> str:
        return f"""{{
  viewer {{
    login,
    name,
    repositories(
        first: 100,
        orderBy: {{
            field: UPDATED_AT,
            direction: DESC
        }},
        isFork: false,
        after: {"null" if owned_cursor is None else '"'+ owned_cursor +'"'}
    ) {{
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        nameWithOwner
        stargazers {{
          totalCount
        }}
        forkCount
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{
              name
              color
            }}
          }}
        }}
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
        after: {"null" if contrib_cursor is None else '"'+ contrib_cursor +'"'}
    ) {{
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        nameWithOwner
        stargazers {{
          totalCount
        }}
        forkCount
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{
              name
              color
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""

    @staticmethod
    def contrib_years() -> str:
        return """
query {
  viewer {
    contributionsCollection {
      contributionYears
    }
  }
}
"""

    @staticmethod
    def contribs_by_year(year: str) -> str:
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
    def all_contribs(cls, years: list[str]) -> str:
        by_years = "\n".join(map(cls.contribs_by_year, years))
        return f"""
query {{
  viewer {{
    {by_years}
  }}
}}
"""

class Stats:
    def __init__(self, username: str, access_token: str,
                 session: aiohttp.ClientSession,
                 exclude_repos: set | None = None,
                 exclude_langs: set | None = None,
                 consider_forked_repos: bool = False):
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
        self._lines_changed = None
        self._views = None

    async def to_str(self):
        stats = await self.get_stats()
        return str(stats)

    async def get_stats(self):
        return {
            "name": await self.name,
            "stargazers": await self.stargazers,
            "forks": await self.forks,
            "languages": await self.languages,
            "repos": await self.repos,
            "total_contributions": await self.total_contributions,
            "lines_changed": await self.lines_changed,
            "views": await self.views,
        }

    @property
    async def name(self):
        if self._name is not None:
            return self._name
        q = """
        query {
          viewer {
            name
          }
        }
        """
        result = await self.queries.query(q)
        self._name = result.get("data", {}).get("viewer", {}).get("name", "")
        return self._name

    @property
    async def stargazers(self):
        if self._stargazers is not None:
            return self._stargazers
        # Implement actual logic as needed
        self._stargazers = 0
        return self._stargazers

    @property
    async def forks(self):
        if self._forks is not None:
            return self._forks
        # Implement actual logic as needed
        self._forks = 0
        return self._forks

    @property
    async def languages(self):
        if self._languages is not None:
            return self._languages
        # Implement actual logic as needed
        self._languages = {}
        return self._languages

    @property
    async def repos(self):
        if self._repos is not None:
            return self._repos
        # Implement actual logic as needed
        self._repos = []
        return self._repos

    @property
    async def all_repos(self):
        # Implement actual logic as needed
        return await self.repos

    @property
    async def total_contributions(self):
        if self._total_contributions is not None:
            return self._total_contributions
        # Implement actual logic as needed
        self._total_contributions = 0
        return self._total_contributions

    @property
    async def lines_changed(self):
        if self._lines_changed is not None:
            return self._lines_changed
        # Implement actual logic as needed
        self._lines_changed = (0, 0)
        return self._lines_changed

    @property
    async def views(self):
        if self._views is not None:
            return self._views
        # Implement actual logic as needed
        self._views = 0
        return self._views

async def main():
    access_token = os.getenv("ACCESS_TOKEN")
    user = os.getenv("GITHUB_ACTOR")
    if not access_token or not user:
        raise Exception("Both ACCESS_TOKEN and GITHUB_ACTOR env vars are required to proceed!")
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
        stats = await s.get_stats()
        print(stats)
