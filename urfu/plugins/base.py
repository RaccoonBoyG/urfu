import os

import appdirs

from urfu.__about__ import __app__

PLUGINS_ROOT_ENV_VAR_NAME = "URFU_PLUGINS_ROOT"

# Folder path which contains *.yml and *.py file plugins.
# On linux this is typically ``~/.local/share/urfu-plugins``. On the nightly branch
# this will be ``~/.local/share/urfu-plugins-nightly``.
# The path can be overridden by defining the ``URFU_PLUGINS_ROOT`` environment
# variable.
PLUGINS_ROOT = os.path.expanduser(
    os.environ.get(PLUGINS_ROOT_ENV_VAR_NAME, "")
) or appdirs.user_data_dir(appname=__app__ + "-plugins")
