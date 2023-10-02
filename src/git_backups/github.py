import logging

import requests

LOGGER = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/graphql"


def fetch_user_repositories(github_token, limit=1000, only_sources=True):
    """
    Fetch all repositories of the authenticated user given a GitHub token
    """
    cursor = None
    user_repos = []

    headers = {
        "Authorization": f"bearer {github_token}",
        "Content-Type": "application/json",
    }

    while True:
        # GraphQL Query to fetch user repositories
        query = """
        {
            viewer {
                repositories(first: 100, after: %s, %s) {
                    edges {
                        node {
                            nameWithOwner
                            url
                            isFork
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
        """ % (
            f'"{cursor}"' if cursor else "null",
            "isFork: false" if only_sources else "",
        )

        try:
            response = requests.post(
                GITHUB_API_URL, json={"query": query}, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            edges = (
                data.get("data", {})
                .get("viewer", {})
                .get("repositories", {})
                .get("edges", [])
            )
            page_info = (
                data.get("data", {})
                .get("viewer", {})
                .get("repositories", {})
                .get("pageInfo", {})
            )

            for edge in edges:
                node = edge.get("node", {})
                user_repos.append(node.get("url"))

            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")
        except requests.RequestException as e:
            LOGGER.error(f"Error occurred while fetching user repositories: {str(e)}")
            continue

    return user_repos[:limit]


def fetch_starred_repositories(github_token, limit=1000):
    """
    Fetch all starred repositories given a GitHub token
    """
    cursor = None
    starred_repos = []

    headers = {
        "Authorization": f"bearer {github_token}",
        "Content-Type": "application/json",
    }

    while True:
        # GraphQL Query to fetch starred repositories
        query = """
        {
            viewer {
                starredRepositories(first: 100, after: %s, orderBy: {field: STARRED_AT, direction: DESC}) {
                    edges {
                        node {
                            nameWithOwner
                            url
                        }
                        starredAt
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
        """ % (
            f'"{cursor}"' if cursor else "null"
        )

        try:
            response = requests.post(
                GITHUB_API_URL, json={"query": query}, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            edges = (
                data.get("data", {})
                .get("viewer", {})
                .get("starredRepositories", {})
                .get("edges", [])
            )
            page_info = (
                data.get("data", {})
                .get("viewer", {})
                .get("starredRepositories", {})
                .get("pageInfo", {})
            )

            for edge in edges:
                node = edge.get("node", {})
                starred_repos.append(node.get("url"))

            if not page_info.get("hasNextPage") or len(starred_repos) >= limit:
                break

            cursor = page_info.get("endCursor")
        except requests.RequestException as e:
            LOGGER.error(
                f"Error occurred while fetching starred repositories: {str(e)}"
            )
            continue

    return starred_repos[:limit]
