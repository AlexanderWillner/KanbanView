#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Module documentation goes here."""

import configparser
import json
import unittest

from things3 import things3, things3_api


class Things3APICase(unittest.TestCase):
    """Class documentation goes here."""

    def setUp(self):
        self.things3_api = things3_api.Things3API(database="resources/demo.sqlite3")
        self.things3 = things3.Things3(database="resources/demo.sqlite3")
        self.things3.config = configparser.ConfigParser()
        self.things3.config.read("tests/kanbanviewrc")
        self.things3_api.things3 = self.things3
        self.things3_api.test_mode = "task"

    def test_today(self):
        """Test Today."""
        result = json.loads(self.things3_api.api("today").response[0])
        self.assertEqual(5, len(result))

    def test_areas(self):
        """Test areas."""
        result = json.loads(self.things3_api.api("areas").response[0])
        self.assertEqual(1, len(result))

    def test_get_tag(self):
        """Test tags."""
        result = json.loads(self.things3_api.tag("Waiting").response[0])
        self.assertEqual(3, len(result))

    def test_not_implemented(self):
        """Test not implemented."""
        result = self.things3_api.api("not-implemented").status_code
        self.assertEqual(404, result)

    def test_not_found(self):
        """Test not found."""
        result = self.things3_api.on_get("sdf").status_code
        self.assertEqual(404, result)

    def test_toggle(self):
        """Test toggle."""
        result = json.loads(self.things3_api.api("next").response[0])
        self.assertEqual(32, len(result))
        self.things3_api.test_mode = "project"
        result = json.loads(self.things3_api.api("next").response[0])
        self.assertEqual(6, len(result))
        self.things3_api.test_mode = "task"
        result = json.loads(self.things3_api.api("next").response[0])
        self.assertEqual(32, len(result))

    def test_filter(self):
        """Test Filter."""
        self.things3_api.api_filter("project", "D8A6Aknfmq69iW5noxLfz4")
        result = json.loads(self.things3_api.api("next").response[0])
        self.assertEqual(2, len(result))
        self.things3_api.api_filter_reset()
        result = json.loads(self.things3_api.api("next").response[0])
        self.assertEqual(32, len(result))

    def test_get_file(self):
        """Test get file."""
        result = self.things3_api.on_get("/kanban.html").response[0].decode("utf-8")
        self.assertIn("kanban.js", result)

    def test_config(self):
        """Test configuration."""
        result = self.things3_api.config_get("TAG_MIT").response[0].decode("utf-8")
        self.assertEqual("😀", result)


if __name__ == "__main__":
    unittest.main()
