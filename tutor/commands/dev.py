from __future__ import annotations

import click

from tutor import config as tutor_config
from tutor import env as tutor_env
from tutor import fmt, hooks
from tutor import interactive as interactive_config
from tutor import utils
from tutor.commands import compose
from tutor.types import Config, get_typed


class DevTaskRunner(compose.ComposeTaskRunner):
    def __init__(self, root: str, config: Config):
        """
        Load docker-compose files from dev/ and local/
        """
        super().__init__(root, config)
        self.project_name = get_typed(self.config, "DEV_PROJECT_NAME", str)
        self.docker_compose_files += [
            tutor_env.pathjoin(self.root, "local", "docker-compose.yml"),
            tutor_env.pathjoin(self.root, "dev", "docker-compose.yml"),
            tutor_env.pathjoin(self.root, "local", "docker-compose.override.yml"),
            tutor_env.pathjoin(self.root, "dev", "docker-compose.override.yml"),
        ]
        self.docker_compose_job_files += [
            tutor_env.pathjoin(self.root, "local", "docker-compose.jobs.yml"),
            tutor_env.pathjoin(self.root, "dev", "docker-compose.jobs.yml"),
            tutor_env.pathjoin(self.root, "local", "docker-compose.jobs.override.yml"),
            tutor_env.pathjoin(self.root, "dev", "docker-compose.jobs.override.yml"),
        ]


class DevContext(compose.BaseComposeContext):
    def job_runner(self, config: Config) -> DevTaskRunner:
        return DevTaskRunner(self.root, config)


@click.group(help="Run Open edX locally with development settings")
@click.pass_context
def dev(context: click.Context) -> None:
    context.obj = DevContext(context.obj.root)


@click.command(help="Configure and run Open edX from scratch, for development")
@click.option("-I", "--non-interactive", is_flag=True, help="Run non-interactively")
@click.option("-p", "--pullimages", is_flag=True, help="Update docker images")
@click.pass_context
def launch(
    context: click.Context,
    non_interactive: bool,
    pullimages: bool,
) -> None:
    utils.warn_macos_docker_memory()

    click.echo(fmt.title("Interactive platform configuration"))
    config = tutor_config.load_minimal(context.obj.root)
    if not non_interactive:
        interactive_config.ask_questions(config, run_for_prod=False)
    tutor_config.save_config_file(context.obj.root, config)
    config = tutor_config.load_full(context.obj.root)
    tutor_env.save(context.obj.root, config)

    click.echo(fmt.title("Stopping any existing platform"))
    context.invoke(compose.stop)

    if pullimages:
        click.echo(fmt.title("Docker image updates"))
        context.invoke(compose.dc_command, command="pull")

    click.echo(fmt.title("Starting the platform in detached mode"))
    context.invoke(compose.start, detach=True)

    click.echo(fmt.title("Database creation and migrations"))
    context.invoke(compose.do.commands["init"])

    fmt.echo_info(
        """The Open edX platform is now running in detached mode
Your Open edX platform is ready and can be accessed at the following urls:
    {http}://{lms_host}:8000
    {http}://{cms_host}:8001
    """.format(
            http="https" if config["ENABLE_HTTPS"] else "http",
            lms_host=config["LMS_HOST"],
            cms_host=config["CMS_HOST"],
        )
    )


@hooks.Actions.COMPOSE_PROJECT_STARTED.add()
def _stop_on_local_start(root: str, config: Config, project_name: str) -> None:
    """
    Stop the dev platform as soon as a platform with a different project name is
    started.
    """
    runner = DevTaskRunner(root, config)
    if project_name != runner.project_name:
        runner.docker_compose("stop")


dev.add_command(launch)
compose.add_commands(dev)
