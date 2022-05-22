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

import gitlab
from git import Repo, GitCommandError
from gitlab.v4.objects import Project

from git_backups import utils

GITLAB_URL = os.environ.get("GITLAB_URL", default="https://gitlab.com")
GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME")
GITLAB_PRIVATE_TOKEN = os.environ.get("GITLAB_PRIVATE_TOKEN")
BACKUP_REMOTE = "backup"


LOGGER = logging.getLogger(__name__)


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


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="subcommand")

    # gitbak src (add, remove)
    source_parser = sub.add_parser("source", aliases=["src"], help="Manage sources")
    source_sub = source_parser.add_subparsers(dest="source_action")
    source_add = source_sub.add_parser("add", help="Add git source to config")
    source_add.add_argument("source", help="Git repository URL")
    source_remove = source_sub.add_parser("remove", help="Remove git source to config")
    source_remove.add_argument("source", help="Git repository URL")

    # gitbak sync
    sync_parser = sub.add_parser("sync", help="Backup repository")
    sync_parser.add_argument("source", help="Git repository URL")
    sync_parser.add_argument(
        "--project",
        dest="project_name",
        help="Name of the destination Gitlab project. Will be inferred from ",
    )
    sync_parser.add_argument(
        "--group",
        dest="group_name",
        default=None,
        help="Group under which the destination project will be categorised (optional)",
    )
    sync_parser.add_argument(
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
