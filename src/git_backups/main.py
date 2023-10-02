"""
Backup git repos to a GitLab instance.
"""

import argparse
import functools
import logging
import os
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta

import gitlab
from git import Repo, GitCommandError
from gitlab.v4.objects import Project

from git_backups import utils
from git_backups.github import fetch_starred_repositories

try:
    from tqdm import tqdm
except ImportError:
    # dummy
    def tqdm(iterable, *args, **kwargs):
        return iterable


GITLAB_URL = os.environ.get("GITLAB_URL", default="https://gitlab.com")
GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME")
GITLAB_PRIVATE_TOKEN = os.environ.get("GITLAB_PRIVATE_TOKEN")
BACKUP_REMOTE = "backup"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def construct_gitlab_remote_url(project_name, group_name=None) -> str:
    if utils.is_empty(group_name):
        group_name = GITLAB_USERNAME

    parsed = urllib.parse.urlparse(GITLAB_URL)
    # noinspection PyProtectedMember
    new = parsed._replace(
        netloc=f"{GITLAB_USERNAME}:{GITLAB_PRIVATE_TOKEN}@{parsed.netloc}",
        path=f"{group_name}/{project_name}.git",
    )
    return new.geturl()  # noqa: pycharm thinks it is bytes


@functools.lru_cache(maxsize=64)
def _gitlab():
    return gitlab.Gitlab(url=GITLAB_URL, private_token=GITLAB_PRIVATE_TOKEN)


def get_or_create_group(group_name):
    gl = _gitlab()

    try:
        return gl.groups.list(search=group_name)[0]
    except (gitlab.GitlabError, IndexError):
        return gl.groups.create({"name": group_name, "path": group_name})


def get_or_create_project(project_name, group_name=None):
    if not utils.is_empty(group_name):
        group = get_or_create_group(group_name)
    else:
        group = None

    gl = _gitlab()

    try:
        return gl.projects.list(search=project_name)[0]
    except (gitlab.GitlabError, IndexError):
        return gl.projects.create(
            {"name": project_name, "namespace_id": group.get_id() if group else None}
        )


def project_is_empty(project: Project) -> bool:
    try:
        return next(project.commits.list(per_page=1, as_list=False)) is None
    except StopIteration:
        return True


def backup_repo(source, project_name, group_name: str = None, overwrite=False):
    """
    Backup a git repo (source) to destination (project_name) on GitLab.
    """

    if utils.is_empty(group_name):
        group_name = None

    try:
        with tempfile.TemporaryDirectory() as workdir:
            project = get_or_create_project(project_name, group_name=group_name)
            if not overwrite and not project_is_empty(project):
                LOGGER.error(
                    "Project (%s) already exists, skipping %s", project.name, source
                )
                return exit_with_error(-3)

            repo = Repo.clone_from(source, workdir, multi_options=["--bare"])
            destination = construct_gitlab_remote_url(
                project_name, group_name=group_name
            )
            remote = repo.create_remote(
                BACKUP_REMOTE,
                destination,
            )

            remote.push(mirror=True)
            LOGGER.info("Backed up %s to %s", source, destination)
    except GitCommandError as e:
        LOGGER.error(e.stderr)
        return exit_with_error(-2)


def exit_with_error(code=-1):
    sys.exit(code)


def is_recently_backed_up(group_name, project_name, days=7):
    gl = _gitlab()
    try:
        project = gl.projects.get(f"{group_name}/{project_name}")
        updated_at = datetime.strptime(
            project.attributes["last_activity_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        if datetime.utcnow() - updated_at <= timedelta(days=days):
            return True
    except gitlab.exceptions.GitlabGetError:
        # If project is not found, it hasn't been backed up yet
        pass


def copy_github(token):
    starred_repos = fetch_starred_repositories(token, limit=10)
    for repo in starred_repos:
        project_name, group_name = utils.get_project_name_and_group(repo)
        if not project_name:
            LOGGER.error(
                f"Project name invalid/could not be inferred, skipping ({repo})"
            )
            continue

        if is_recently_backed_up(group_name, project_name):
            LOGGER.warning(f"{repo} was backed up recently, skipping")
            continue

        LOGGER.info("Backing up %s", repo)
        backup_repo(repo, project_name, group_name=group_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", dest="source", help="Git repository URL")
    parser.add_argument(
        "--copy-github",
        dest="copy_github",
        action="store_true",
        help="Clone GitHub starred repos",
    )
    parser.add_argument(
        "--project",
        dest="project_name",
        help="Name of the destination Gitlab project. Will be inferred from ",
    )
    parser.add_argument(
        "--group",
        dest="group_name",
        default=None,
        help="Group under which the destination project will be categorised (optional)",
    )
    parser.add_argument(
        "-f",
        "--force",
        default=False,
        dest="overwrite",
        action="store_true",
        help=(
            "Overwrite existing project data on the target Gitlab instance"
            " (will not overwrite by default)"
        ),
    )
    options = parser.parse_args()

    if options.copy_github:
        copy_github(GITHUB_TOKEN)
        return

    inferred_project, inferred_group = utils.get_project_name_and_group(options.source)
    project_name = options.project_name or inferred_project
    group_name = options.group_name or inferred_group
    if not project_name:
        LOGGER.error(
            "Project name could not be inferred, please pass manually (%s)",
            options.source,
        )
        return exit_with_error()

    backup_repo(
        options.source,
        project_name,
        group_name=group_name,
        overwrite=options.overwrite,
    )


if __name__ == "__main__":
    main()
