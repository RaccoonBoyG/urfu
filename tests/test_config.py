import json
import os
import unittest
from unittest.mock import Mock, patch

import click

from tests.helpers import PluginsTestCase, temporary_root
from urfu import config as urfu_config
from urfu import fmt, hooks, interactive, utils
from urfu.types import Config, get_typed


class ConfigTests(unittest.TestCase):
    def test_version(self) -> None:
        defaults = urfu_config.get_defaults()
        self.assertNotIn("URFU_VERSION", defaults)

    def test_merge(self) -> None:
        config1: Config = {"x": "y"}
        config2: Config = {"x": "z"}
        urfu_config.merge(config1, config2)
        self.assertEqual({"x": "y"}, config1)

    def test_merge_not_render(self) -> None:
        config: Config = {}
        base = urfu_config.get_base()
        with patch.object(utils, "random_string", return_value="abcd"):
            urfu_config.merge(config, base)

        # Check that merge does not perform a rendering
        self.assertNotEqual("abcd", config["MYSQL_ROOT_PASSWORD"])

    @patch.object(fmt, "echo")
    def test_update_twice_should_return_same_config(self, _: Mock) -> None:
        with temporary_root() as root:
            config1 = urfu_config.load_minimal(root)
            urfu_config.save_config_file(root, config1)
            config2 = urfu_config.load_minimal(root)

        self.assertEqual(config1, config2)

    def test_interactive(self) -> None:
        def mock_prompt(*_args: None, **kwargs: str) -> str:
            return kwargs["default"]

        with temporary_root() as rootdir:
            with patch.object(click, "prompt", new=mock_prompt):
                with patch.object(click, "confirm", new=mock_prompt):
                    config = urfu_config.load_minimal(rootdir)
                    interactive.ask_questions(config)

        self.assertIn("MYSQL_ROOT_PASSWORD", config)
        self.assertEqual(8, len(get_typed(config, "MYSQL_ROOT_PASSWORD", str)))
        self.assertEqual("www.myopenedx.com", config["LMS_HOST"])
        self.assertEqual("studio.www.myopenedx.com", config["CMS_HOST"])

    def test_is_service_activated(self) -> None:
        config: Config = {"RUN_SERVICE1": True, "RUN_SERVICE2": False}
        self.assertTrue(urfu_config.is_service_activated(config, "service1"))
        self.assertFalse(urfu_config.is_service_activated(config, "service2"))

    @patch.object(fmt, "echo")
    def test_json_config_is_overwritten_by_yaml(self, _: Mock) -> None:
        with temporary_root() as root:
            # Create config from scratch
            config_yml_path = os.path.join(root, urfu_config.CONFIG_FILENAME)
            config_json_path = os.path.join(
                root, urfu_config.CONFIG_FILENAME.replace("yml", "json")
            )
            config = urfu_config.load_full(root)

            # Save config to json
            with open(config_json_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            self.assertFalse(os.path.exists(config_yml_path))
            self.assertTrue(os.path.exists(config_json_path))

            # Reload and compare
            current = urfu_config.load_full(root)
            self.assertTrue(os.path.exists(config_yml_path))
            self.assertFalse(os.path.exists(config_json_path))
            self.assertEqual(config, current)


class ConfigPluginTestCase(PluginsTestCase):
    @patch.object(fmt, "echo")
    def test_removed_entry_is_added_on_save(self, _: Mock) -> None:
        with temporary_root() as root:
            mock_random_string = Mock()

            hooks.Filters.ENV_TEMPLATE_FILTERS.add_item(
                ("random_string", mock_random_string),
            )
            mock_random_string.return_value = "abcd"
            config1 = urfu_config.load_full(root)
            password1 = config1.pop("MYSQL_ROOT_PASSWORD")

            urfu_config.save_config_file(root, config1)

            mock_random_string.return_value = "efgh"
            config2 = urfu_config.load_full(root)
            password2 = config2["MYSQL_ROOT_PASSWORD"]

        self.assertEqual("abcd", password1)
        self.assertEqual("efgh", password2)
