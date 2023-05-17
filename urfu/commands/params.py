import typing as t

import click

from urfu import config as urfu_config
from urfu import hooks
from urfu.types import Config


class ConfigLoaderParam(click.ParamType):
    """
    Convenient param child class that automatically loads the user configuration on auto-complete.
    """

    def __init__(self) -> None:
        self.root = None
        self._config: t.Optional[Config] = None

        @hooks.Actions.PROJECT_ROOT_READY.add()
        def _on_root_ready(root: str) -> None:
            self.root = root

    @property
    def config(self) -> Config:
        if self.root is None:
            return {}
        if self._config is None:
            self._config = urfu_config.load_full(self.root)
        return self._config
