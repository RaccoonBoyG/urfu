#!/usr/bin/env python3
from urfu import hooks
from urfu.commands.cli import main
from urfu.plugins.v0 import OfficialPlugin


@hooks.Actions.CORE_READY.add()
def _discover_official_plugins() -> None:
    # Manually discover plugins: that's because entrypoint plugins are not properly
    # detected within the binary bundle.
    with hooks.Contexts.PLUGINS.enter():
        OfficialPlugin.discover_all()


if __name__ == "__main__":
    # Call the regular main function, which will not detect any entrypoint plugin
    main()
