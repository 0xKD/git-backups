from typing import Tuple

import pytest as pytest

from git_backups.utils import get_project_name_and_group

GIT_SOURCES: Tuple[str, ...] = (
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
NO_GROUP = [_.replace("path/to/", "") for _ in GIT_SOURCES]


@pytest.mark.parametrize("source", GIT_SOURCES)
def test_source_parser(source: str):
    assert get_project_name_and_group(source) == ("repo", "to")


@pytest.mark.parametrize("source", NO_GROUP)
def test_source_parser_empty_group(source: str):
    assert get_project_name_and_group(source) == ("repo", None)
