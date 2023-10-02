import os
import re
from typing import Optional, Tuple
from urllib import parse


def is_empty(val: Optional[str]) -> bool:
    if not val:
        return True

    return not val.strip()


def clean_name(s: str) -> str:
    """
    Split on ":", take last item.
    Trim trailing (.git) and slash from the name
    """
    return re.sub(r"(.git)?/?$", "", s.split(":")[-1])


def validate_group_name(s: str) -> bool:
    """
    Name can contain only letters, digits, emojis, '_', '.', dash, space, parenthesis.
     It must start with letter, digit, emoji, or '_'.

    >>> validate_group_name("foobar+")
    False
    >>> validate_group_name("basic(b)")
    True
    """
    return re.fullmatch(r"\w[\w\-.() ]*", s) is not None


def validate_project_name(s: str) -> bool:
    """
    Name can contain only letters, digits, emojis, '_', '.', '+', dashes, or spaces.
     It must start with a letter, digit, emoji, or '_'.

    >>> validate_project_name("basic(b)")
    False
    >>> validate_project_name("foo.bar")
    True
    """
    return (
        re.fullmatch(
            r"[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*(/[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*)*", s
        )
        is not None
    )


def get_project_name_and_group(source) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse project name and group from source git URL (if possible)
    Returns None (for either items if no valid name could be determined)

    >>> get_project_name_and_group("git@github.com:0xKD/elixir.git")
    ('elixir', '0xKD')
    >>> get_project_name_and_group("/home/user/repos/sample.git")
    ('sample', 'repos')
    """

    try:
        parsed = parse.urlparse(source)
        group, project = os.path.split(clean_name(parsed.path))
    except (ValueError, TypeError):
        group, project = None, None

    if group and group.strip():
        group = os.path.basename(group)

    if project and project.strip():
        project = clean_name(project)

    return (
        project if validate_project_name(project) else None,
        group if validate_group_name(group) else None,
    )
