from __future__ import annotations

import click

from urfu import env as urfu_env
from urfu import hooks
from urfu.commands import compose
from urfu.types import Config, get_typed


class LocalTaskRunner(compose.ComposeTaskRunner):
    NAME = "local"

    def __init__(self, root: str, config: Config):
        """
        Load docker-compose files from local/.
        """
        super().__init__(root, config)
        self.project_name = get_typed(self.config, "LOCAL_PROJECT_NAME", str)
        self.docker_compose_files += [
            urfu_env.pathjoin(self.root, "local", "docker-compose.yml"),
            urfu_env.pathjoin(self.root, "local", "docker-compose.prod.yml"),
            urfu_env.pathjoin(self.root, "local", "docker-compose.override.yml"),
        ]
        self.docker_compose_job_files += [
            urfu_env.pathjoin(self.root, "local", "docker-compose.jobs.yml"),
            urfu_env.pathjoin(self.root, "local", "docker-compose.jobs.override.yml"),
        ]


# pylint: disable=too-few-public-methods
class LocalContext(compose.BaseComposeContext):
    def job_runner(self, config: Config) -> LocalTaskRunner:
        return LocalTaskRunner(self.root, config)


@click.group(help="Run Open edX locally with docker-compose")
@click.pass_context
def local(context: click.Context) -> None:
    context.obj = LocalContext(context.obj.root)


@hooks.Actions.COMPOSE_PROJECT_STARTED.add()
def _stop_on_dev_start(root: str, config: Config, project_name: str) -> None:
    """
    Stop the local platform as soon as a platform with a different project name is
    started.
    """
    runner = LocalTaskRunner(root, config)
    if project_name != runner.project_name:
        runner.docker_compose("stop")


compose.add_commands(local)
