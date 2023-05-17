import click

from urfu import config as urfu_config
from urfu import env as urfu_env
from urfu import fmt
from urfu.commands import k8s
from urfu.commands.context import Context
from urfu.types import Config

from . import common as common_upgrade


def upgrade_from(context: click.Context, from_release: str) -> None:
    config = urfu_config.load(context.obj.root)

    running_release = from_release
    if running_release == "ironwood":
        upgrade_from_ironwood(config)
        running_release = "juniper"

    if running_release == "juniper":
        upgrade_from_juniper(config)
        running_release = "koa"

    if running_release == "koa":
        upgrade_from_koa(config)
        running_release = "lilac"

    if running_release == "lilac":
        upgrade_from_lilac(config)
        running_release = "maple"

    if running_release == "maple":
        upgrade_from_maple(context.obj, config)
        running_release = "nutmeg"

    if running_release == "nutmeg":
        common_upgrade.upgrade_from_nutmeg(context, config)
        running_release = "olive"

    if running_release == "olive":
        upgrade_from_olive(context.obj, config)
        running_release = "palm"


def upgrade_from_ironwood(config: Config) -> None:
    if not config["RUN_MONGODB"]:
        fmt.echo_info(
            "You are not running MongoDB (RUN_MONGODB=false). It is your "
            "responsibility to upgrade your MongoDb instance to v3.6. There is "
            "nothing left to do to upgrade from Ironwood."
        )
        return
    message = """Automatic release upgrade is unsupported in Kubernetes. To upgrade from Ironwood, you should upgrade
your MongoDb cluster from v3.2 to v3.6. You should run something similar to:

    # Upgrade from v3.2 to v3.4
    urfu k8s stop
    urfu config save --set DOCKER_IMAGE_MONGODB=mongo:3.4.24
    urfu k8s start
    urfu k8s exec mongodb mongo --eval 'db.adminCommand({ setFeatureCompatibilityVersion: "3.4" })'

    # Upgrade from v3.4 to v3.6
    urfu k8s stop
    urfu config save --set DOCKER_IMAGE_MONGODB=mongo:3.6.18
    urfu k8s start
    urfu k8s exec mongodb mongo --eval 'db.adminCommand({ setFeatureCompatibilityVersion: "3.6" })'

    urfu config save --unset DOCKER_IMAGE_MONGODB"""
    fmt.echo_info(message)


def upgrade_from_juniper(config: Config) -> None:
    if not config["RUN_MYSQL"]:
        fmt.echo_info(
            "You are not running MySQL (RUN_MYSQL=false). It is your "
            "responsibility to upgrade your MySQL instance to v5.7. There is "
            "nothing left to do to upgrade from Juniper."
        )
        return

    message = """Automatic release upgrade is unsupported in Kubernetes. To upgrade from Juniper, you should upgrade
your MySQL database from v5.6 to v5.7. You should run something similar to:

    urfu k8s start
    urfu k8s exec mysql bash -e -c "mysql_upgrade \
        -u $(urfu config printvalue MYSQL_ROOT_USERNAME) \
        --password='$(urfu config printvalue MYSQL_ROOT_PASSWORD)'
"""
    fmt.echo_info(message)


def upgrade_from_koa(config: Config) -> None:
    if not config["RUN_MONGODB"]:
        fmt.echo_info(
            "You are not running MongoDB (RUN_MONGODB=false). It is your "
            "responsibility to upgrade your MongoDb instance to v4.0. There is "
            "nothing left to do to upgrade to Lilac from Koa."
        )
        return
    message = """Automatic release upgrade is unsupported in Kubernetes. To upgrade from Koa to Lilac, you should upgrade
your MongoDb cluster from v3.6 to v4.0. You should run something similar to:

    urfu k8s stop
    urfu config save --set DOCKER_IMAGE_MONGODB=mongo:4.0.25
    urfu k8s start
    urfu k8s exec mongodb mongo --eval 'db.adminCommand({ setFeatureCompatibilityVersion: "4.0" })'
    urfu config save --unset DOCKER_IMAGE_MONGODB
    """
    fmt.echo_info(message)


def upgrade_from_lilac(config: Config) -> None:
    common_upgrade.upgrade_from_lilac(config)
    fmt.echo_info(
        "All Kubernetes services and deployments need to be deleted during "
        "upgrade from Lilac to Maple"
    )
    k8s.delete_resources(config, resources=["deployments", "services"])


def upgrade_from_maple(context: Context, config: Config) -> None:
    fmt.echo_info("Upgrading from Maple")
    # The environment needs to be updated because the backpopulate/backfill commands are from Nutmeg
    urfu_env.save(context.root, config)

    if config["RUN_MYSQL"]:
        # Start mysql
        k8s.kubectl_apply(
            context.root,
            "--selector",
            "app.kubernetes.io/name=mysql",
        )
        k8s.wait_for_deployment_ready(config, "mysql")

    # lms upgrade
    k8s.kubectl_apply(
        context.root,
        "--selector",
        "app.kubernetes.io/name=lms",
    )
    k8s.wait_for_deployment_ready(config, "lms")

    # Command backpopulate_user_tours
    k8s.kubectl_exec(
        config, "lms", ["sh", "-e", "-c", "./manage.py lms migrate user_tours"]
    )
    k8s.kubectl_exec(
        config, "lms", ["sh", "-e", "-c", "./manage.py lms backpopulate_user_tours"]
    )

    # cms upgrade
    k8s.kubectl_apply(
        context.root,
        "--selector",
        "app.kubernetes.io/name=cms",
    )
    k8s.wait_for_deployment_ready(config, "cms")

    # Command backfill_course_tabs
    k8s.kubectl_exec(
        config, "cms", ["sh", "-e", "-c", "./manage.py cms migrate contentstore"]
    )
    k8s.kubectl_exec(
        config,
        "cms",
        ["sh", "-e", "-c", "./manage.py cms migrate split_modulestore_django"],
    )
    k8s.kubectl_exec(
        config, "cms", ["sh", "-e", "-c", "./manage.py cms backfill_course_tabs"]
    )

    # Command simulate_publish
    k8s.kubectl_exec(
        config, "cms", ["sh", "-e", "-c", "./manage.py cms migrate course_overviews"]
    )
    k8s.kubectl_exec(
        config, "cms", ["sh", "-e", "-c", "./manage.py cms simulate_publish"]
    )


def upgrade_from_olive(context: Context, config: Config) -> None:
    # Note that we need to exec because the ora2 folder is not bind-mounted in the job
    # services.
    k8s.kubectl_apply(
        context.root,
        "--selector",
        "app.kubernetes.io/name=lms",
    )
    k8s.wait_for_deployment_ready(config, "lms")
    k8s.kubectl_exec(
        config,
        "lms",
        ["sh", "-e", "-c", common_upgrade.PALM_RENAME_ORA2_FOLDER_COMMAND],
    )
