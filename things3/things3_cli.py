#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple read-only Thing 3 CLI."""

from __future__ import print_function

import argparse
import csv
import json
import sys
import webbrowser
from types import ModuleType
from typing import Any, Callable, cast

import things3
from things3.things3 import Things3
from things3.things3_opml import Things3OPML

argcomplete: ModuleType | None = None
try:
    import argcomplete as _argcomplete
except ImportError:  # pragma: no cover - optional shell completion
    pass
else:
    argcomplete = _argcomplete


class Things3CLI:
    """Simple read-only Thing 3 CLI."""

    print_json = False
    print_csv = False
    print_opml = False
    anonymize = False

    def __init__(self, database=None):
        self.things3 = Things3(database)

    def print_tasks(self, tasks):
        """Print a task."""
        if self.print_json:
            print(json.dumps(tasks))
        elif self.print_opml:
            Things3OPML().print_tasks(tasks)
        elif self.print_csv:
            fieldnames = [
                "uuid",
                "title",
                "context",
                "context_uuid",
                "size",
                "type",
                "due",
                "created",
                "modified",
                "started",
                "stopped",
                "notes",
            ]
            writer = csv.DictWriter(
                sys.stdout, fieldnames=fieldnames, delimiter=";", extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(tasks)
        else:
            for task in tasks:
                title = task["title"]
                context = task["context"] if "context" in task else ""
                print(" - ", title, " (", context, ")")

    @classmethod
    def print_unimplemented(cls):
        """Show warning that method is not yet implemented."""
        print("not implemented yet (see things.sh for a more complete CLI)")

    @classmethod
    def get_parser(cls):
        """Create command line argument parser"""
        parser = argparse.ArgumentParser(description="Simple read-only Thing 3 CLI.")

        subparsers = parser.add_subparsers(
            help="", metavar="command", required=True, dest="command"
        )
        subparsers.add_parser("inbox", help="Shows inbox tasks")
        subparsers.add_parser("today", help="Shows todays tasks")
        subparsers.add_parser("upcoming", help="Shows upcoming tasks")
        subparsers.add_parser("next", help="Shows next tasks")
        subparsers.add_parser("backlog", help="Shows backlog tasks")
        subparsers.add_parser("completed", help="Shows completed tasks")
        subparsers.add_parser("cancelled", help="Shows cancelled tasks")
        subparsers.add_parser("trashed", help="Shows trashed tasks")
        subparsers.add_parser("feedback", help="Give feedback")
        subparsers.add_parser("all", help="Shows all tasks")
        subparsers.add_parser("csv", help="Exports tasks as CSV")
        subparsers.add_parser("areas", help="Shows all areas")
        subparsers.add_parser("opml", help="Exports tasks as OPML")
        subparsers.add_parser("due", help="Shows tasks with due dates")
        subparsers.add_parser("empty", help="Shows projects that are empty")
        subparsers.add_parser("headings", help="Shows headings")
        subparsers.add_parser("hours", help="Shows hours planned today")
        subparsers.add_parser("ical", help="Shows tasks ordered by due date as iCal")
        subparsers.add_parser("lint", help="Shows tasks that float around")
        subparsers.add_parser("logbook", help="Shows tasks completed today")
        subparsers.add_parser(
            "mostClosed", help="Shows days when most tasks were closed"
        )
        subparsers.add_parser(
            "mostCancelled", help="Shows days when most tasks were cancelled"
        )
        subparsers.add_parser(
            "mostTrashed", help="Shows days when most tasks were trashed"
        )
        subparsers.add_parser(
            "mostCreated", help="Shows days when most tasks were created"
        )
        subparsers.add_parser("mostTasks", help="Shows projects that have most tasks")
        subparsers.add_parser(
            "mostCharacters", help="Shows tasks that have most characters"
        )
        subparsers.add_parser("nextish", help="Shows all nextish tasks")
        subparsers.add_parser("old", help="Shows all old tasks")
        subparsers.add_parser("projects", help="Shows all projects")
        subparsers.add_parser("repeating", help="Shows all repeating tasks")
        subparsers.add_parser("schedule", help="Schedules an event using a template")
        subparsers.add_parser("search", help="Searches for a specific task")
        subparsers.add_parser("stat", help="Provides a number of statistics")
        subparsers.add_parser("statcsv", help="Exports some statistics as CSV")
        subparsers.add_parser("subtasks", help="Shows all subtasks")
        subparsers.add_parser("tag", help="Shows all tasks with the waiting for tag")
        subparsers.add_parser("tags", help="Shows all tags ordered by their usage")
        subparsers.add_parser(
            "waiting", help="Shows all tasks with the waiting for tag"
        )

        parser.add_argument(
            "-j",
            "--json",
            action="store_true",
            default=False,
            help="output as JSON",
            dest="json",
        )

        parser.add_argument(
            "-c",
            "--csv",
            action="store_true",
            default=False,
            help="output as CSV",
            dest="csv",
        )

        parser.add_argument(
            "-o",
            "--opml",
            action="store_true",
            default=False,
            help="output as OPML",
            dest="opml",
        )

        parser.add_argument(
            "-a",
            "--anonymize",
            action="store_true",
            default=False,
            help="anonymize output",
            dest="anonymize",
        )

        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s (version {things3.__version__})",
        )

        if argcomplete is not None:
            argcomplete.autocomplete(parser)

        return parser

    def main(self, args=None):
        """Main entry point of the app"""

        if args is None:
            self.main(Things3CLI.get_parser().parse_args())
        else:
            command = args.command
            self.print_json = args.json
            self.print_csv = args.csv
            self.print_opml = args.opml
            self.anonymize = args.anonymize
            self.things3.anonymize = self.anonymize

            if command in self.things3.functions:
                func = cast(
                    Callable[[Things3], list[dict[str, Any]]],
                    self.things3.functions[command],
                )
                self.print_tasks(func(self.things3))
            elif command == "opml":
                Things3OPML().print_all(self.things3)
            elif command == "csv":
                print("Deprecated: use --csv instead")
            elif command == "feedback":
                webbrowser.open("https://github.com/AlexanderWillner/KanbanView/issues")
            else:
                Things3CLI.print_unimplemented()


def main():
    """Main entry point for CLI installation"""
    Things3CLI().main()


if __name__ == "__main__":
    main()
