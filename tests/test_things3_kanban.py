#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Module documentation goes here."""

import io
import unittest

from things3 import things3_kanban
from things3.things3 import Things3


class Things3KanbanCase(unittest.TestCase):
    """Class documentation goes here."""

    class CustomStringIO(io.StringIO):
        """Do not close output for testing."""

        def close(self):
            pass

    def setUp(self):
        self.things3 = Things3(database="resources/demo.sqlite3")

    def test_today(self):
        """Test Today."""
        output = self.CustomStringIO()
        things3_kanban.THINGS3 = self.things3
        things3_kanban.main(output)
        self.assertIn("Today MIT", output.getvalue())


if __name__ == "__main__":
    unittest.main()
