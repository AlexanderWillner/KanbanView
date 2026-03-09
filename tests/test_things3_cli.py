#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Module documentation goes here."""

import io
import unittest
from contextlib import redirect_stdout

from things3 import things3_cli


class Things3CLICase(unittest.TestCase):
    """Class documentation goes here."""

    def setUp(self):
        self.cli = things3_cli.Things3CLI(database="resources/demo.sqlite3")

    def test_methods(self):
        """Invoke all commands."""
        parser = self.cli.get_parser()
        for command in parser._subparsers._actions[1].choices:  # pylint: disable=W0212
            if command != "feedback":
                args = parser.parse_args([command])
                new_out = io.StringIO()
                with redirect_stdout(new_out):
                    self.cli.main(args)
                self.assertIn(" ", new_out.getvalue())

    def test_today(self):
        """Test Today."""
        args = self.cli.get_parser().parse_args(["today"])
        new_out = io.StringIO()
        with redirect_stdout(new_out):
            self.cli.main(args)
        self.assertIn("Today MIT", new_out.getvalue())

    def test_csv(self):
        """Test Next via CSV."""
        args = self.cli.get_parser().parse_args(["-c", "next"])
        new_out = io.StringIO()
        with redirect_stdout(new_out):
            self.cli.main(args)
        self.assertIn("D82v818cpDQ2NLPZTqWwib", new_out.getvalue())

    def test_json(self):
        """Test Upcoming via JSON."""
        args = self.cli.get_parser().parse_args(["-j", "upcoming"])
        new_out = io.StringIO()
        with redirect_stdout(new_out):
            self.cli.main(args)
        self.assertIn("SGnEWYTSAcnXBLYuMourDj", new_out.getvalue())


if __name__ == "__main__":
    unittest.main()
