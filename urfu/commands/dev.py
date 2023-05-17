from __future__ import annotations

import typing as t

import click

from urfu import env as urfu_env
from urfu import hooks
from urfu.commands import compose
from urfu.types import Config, get_typed


class DevTaskRunner(compose.ComposeTaskRunner):
    NAME = "dev"

    def __init__(self, root: str, config: Config):
        """
        Load docker-compose files from dev/ and local/
        """
        super().__init__(root, config)
        self.project_name = get_typed(self.config, "DEV_PROJECT_NAME", str)
        self.docker_compose_files += [
            urfu_env.pathjoin(self.root, "local", "docker-compose.yml"),
            urfu_env.pathjoin(self.root, "dev", "docker-compose.yml"),
            urfu_env.pathjoin(self.root, "local", "docker-compose.override.yml"),
            urfu_env.pathjoin(self.root, "dev", "docker-compose.override.yml"),
        ]
        self.docker_compose_job_files += [
            urfu_env.pathjoin(self.root, "local", "docker-compose.jobs.yml"),
            urfu_env.pathjoin(self.root, "dev", "docker-compose.jobs.yml"),
            urfu_env.pathjoin(self.root, "local", "docker-compose.jobs.override.yml"),
            urfu_env.pathjoin(self.root, "dev", "docker-compose.jobs.override.yml"),
        ]


class DevContext(compose.BaseComposeContext):
    def job_runner(self, config: Config) -> DevTaskRunner:
        return DevTaskRunner(self.root, config)


@click.group(help="Run Open edX locally with development settings")
@click.pass_context
def dev(context: click.Context) -> None:
    context.obj = DevContext(context.obj.root)


@hooks.Actions.COMPOSE_PROJECT_STARTED.add()
def _stop_on_local_start(root: str, config: Config, project_name: str) -> None:
    """
    Stop the dev platform as soon as a platform with a different project name is
    started.
    """
    runner = DevTaskRunner(root, config)
    if project_name != runner.project_name:
        runner.docker_compose("stop")


@hooks.Filters.IMAGES_BUILD_REQUIRED.add()
def _build_openedx_dev_on_launch(
    image_names: list[str], context_name: t.Literal["local", "dev"]
) -> list[str]:
    if context_name == "dev":
        image_names.append("openedx-dev")
    return image_names


compose.add_commands(dev)
