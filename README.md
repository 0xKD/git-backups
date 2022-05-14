Script to back up a git repo to a Gitlab instance.

#### Usage:

Create a config file (at `.env`)

```shell
export GITLAB_URL=https://your.custom.gitlab.instance
export GITLAB_USERNAME=username
export GITLAB_TOKEN=5v90m4u8nycw984y
```

Then run

```shell
source .env
python src/main.py git@github.com:jazzband/django-robots.git
```

This will create a project `django-robots` under the `jazzband` group on the target Gitlab instance.

#### Help

```
usage: main.py [-h] [--project PROJECT_NAME] [--group GROUP_NAME] source

positional arguments:
  source                Git repository URL

optional arguments:
  -h, --help            show this help message and exit
  --project PROJECT_NAME
                        Name of the destination Gitlab project. Will be inferred from
  --group GROUP_NAME    Group under which the destination project will be categorised (optional)
```
