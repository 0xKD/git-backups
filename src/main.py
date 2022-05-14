"""
Backup git repos to a GitLab instance.
"""

import argparse
import contextlib
import functools
import logging
import os
import secrets
import shutil
import sys
import urllib.parse
from contextlib import contextmanager
from typing import Tuple, Optional

import gitlab
from git import Repo

GITLAB_URL = os.environ.get("GITLAB_URL", default="https://gitlab.com")
GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME")
GITLAB_PRIVATE_TOKEN = os.environ.get("GITLAB_PRIVATE_TOKEN")
BACKUP_REMOTE = "backup"


LOGGER = logging.getLogger(__name__)


def construct_gitlab_remote_url(project_name, group_name=None) -> str:
    if not (isinstance(group_name, str) and group_name.strip()):
        group_name = GITLAB_USERNAME

    parsed = urllib.parse.urlparse(GITLAB_URL)
    # noinspection PyProtectedMember
    new = parsed._replace(
        netloc=f"{GITLAB_USERNAME}:{GITLAB_PRIVATE_TOKEN}@{parsed.netloc}",
        path=f"{group_name}/{project_name}.git",
    )
    return new.geturl()  # noqa: pycharm thinks it is bytes


@functools.lru_cache
def _gitlab():
    return gitlab.Gitlab(url=GITLAB_URL, private_token=GITLAB_PRIVATE_TOKEN)


def get_or_create_group(group_name):
    gl = _gitlab()

    try:
        return gl.groups.list(search=group_name)[0]
    except (gitlab.GitlabError, IndexError):
        return gl.groups.create({"name": group_name, "path": group_name})


def get_or_create_project(project_name, group_name=None):
    if isinstance(group_name, str) and group_name.strip():
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


def backup_repo(source, project_name, group_name=None):
    """
    Backup a git repo (source) to destination (project_name) on GitLab.
    """

    if not (isinstance(group_name, str) and group_name.strip()):
        group_name = None

    with create_temp_dir() as workdir:
        repo = Repo.clone_from(source, workdir, multi_options=["--bare"])
        destination = construct_gitlab_remote_url(project_name, group_name=group_name)
        remote = repo.create_remote(
            BACKUP_REMOTE,
            destination,
        )

        get_or_create_project(project_name, group_name=group_name)
        remote.push(mirror=True)
        LOGGER.info("Backed up %s to %s", source, destination)


GIT_SSH = "git@"
GIT_HTTP = "http"


def get_project_name_and_group(source) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer project name and group from source git URL (if possible)
    """

    # warning: brittle
    try:
        if source.startswith(GIT_SSH):
            group, project = os.path.split(source.split(":")[-1])
        elif source.startswith(GIT_HTTP):
            parsed = urllib.parse.urlparse(source)
            group, project = os.path.split(parsed.path)
        else:
            group, project = None, None
    except (ValueError, IndexError) as e:
        LOGGER.warning("gxg: %s", e)
        group, project = None, None

    if isinstance(group, str) and group.strip():
        group = group.replace("/", "")

    if isinstance(project, str) and project.strip():
        project = project.replace(".git", "")

    return project, group


def exit_with_error(message, code=-1):
    sys.stderr.write(message + "\n")
    sys.exit(code)


def main(source, project_name=None, group_name=None):
    inferred_project, inferred_group = get_project_name_and_group(source)
    if not project_name:
        project_name = inferred_project

    if not group_name:
        group_name = inferred_group

    if not project_name:
        exit_with_error("Project name could not be inferred, please pass manually")

    backup_repo(source, project_name, group_name=group_name)


@contextmanager
def create_temp_dir():
    temp_folder = secrets.token_hex(8)
    destination = os.path.join("/tmp", temp_folder)

    try:
        os.mkdir(destination)
        yield destination
    finally:
        with contextlib.suppress(OSError):
            shutil.rmtree(destination)


# todo: add force flag (default=False) that checks if repo exists and has content
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Git repository URL")
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
    options = parser.parse_args()
    main(
        options.source,
        project_name=options.project_name,
        group_name=options.group_name,
    )
