from typing import Tuple

import pytest as pytest

from git_backups.utils import get_project_name_and_group

FORMATS: Tuple[str, ...] = (
    "ssh://user@host.xz:port/path/to/repo.git",
    "ssh://user@host.xz/path/to/repo.git",
    "ssh://host.xz:port/path/to/repo.git",
    "ssh://host.xz/path/to/repo.git",
    "ssh://user@host.xz/path/to/repo.git",
    "ssh://host.xz/path/to/repo.git",
    "ssh://user@host.xz/~user/path/to/repo.git",
    "ssh://host.xz/~user/path/to/repo.git",
    "ssh://user@host.xz/~/path/to/repo.git",
    "ssh://host.xz/~/path/to/repo.git",
    "user@host.xz:/path/to/repo.git",
    "host.xz:/path/to/repo.git",
    "user@host.xz:~user/path/to/repo.git",
    "host.xz:~user/path/to/repo.git",
    "user@host.xz:path/to/repo.git",
    "host.xz:path/to/repo.git",
    "rsync://host.xz/path/to/repo.git",
    "git://host.xz/path/to/repo.git",
    "git://host.xz/~user/path/to/repo.git",
    "http://host.xz/path/to/repo.git",
    "https://host.xz/path/to/repo.git",
    "/path/to/repo.git",
    "path/to/repo.git",
    "~/path/to/repo.git",
    "file:///path/to/repo.git",
    "file:///path/to/repo/",
    "file:///path/to/repo",
    "file://~/path/to/repo.git",
)
NO_PROJECT = [_.replace("path/to/", "") for _ in FORMATS]


@pytest.mark.parametrize("source", FORMATS)
def test_name_parser(source: str):
    assert get_project_name_and_group(source) == ("repo", "to")


@pytest.mark.parametrize("source", NO_PROJECT)
def test_name_empty(source: str):
    assert get_project_name_and_group(source) == ("repo", None)
