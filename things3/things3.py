#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple read-only API for Things 3."""

from __future__ import print_function

import configparser
import glob
import os
import sqlite3
import sys
import webbrowser
from contextlib import closing
from datetime import datetime, timedelta
from os import environ, path
from pathlib import Path
from random import shuffle
from typing import Any, Callable

# the new core library, migration ongoing
import things

from things3 import __version__

# pylint: disable=R0904,R0902


class Things3:
    """Simple read-only API for Things 3."""

    # Database info
    FILE_CONFIG = str(Path.home()) + "/.kanbanviewrc"
    FILE_DB = (
        "~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac"
        "/ThingsData-*/Things Database.thingsdatabase/main.sqlite"
    )
    TABLE_TASK = "TMTask"
    TABLE_AREA = "TMArea"
    TABLE_TAG = "TMTag"
    TABLE_TASKTAG = "TMTaskTag"
    DATE_CREATE = "creationDate"
    DATE_MOD = "userModificationDate"
    DATE_DUE = "deadline"
    DATE_START = "startDate"
    DATE_STOP = "stopDate"
    IS_INBOX = "start = 0"  # noqa
    IS_ANYTIME = "start = 1"
    IS_SOMEDAY = "start = 2"
    IS_SCHEDULED = f"{DATE_START} IS NOT NULL"
    IS_NOT_SCHEDULED = f"{DATE_START} IS NULL"
    IS_DUE = f"{DATE_DUE} IS NOT NULL"  # noqa
    IS_RECURRING = "rt1_recurrenceRule IS NOT NULL"
    IS_NOT_RECURRING = "rt1_recurrenceRule IS NULL"  # noqa
    IS_TASK = "type = 0"
    IS_PROJECT = "type = 1"
    IS_HEADING = "type = 2"
    IS_TRASHED = "trashed = 1"
    IS_NOT_TRASHED = "trashed = 0"
    IS_OPEN = "status = 0"
    IS_CANCELLED = "status = 2"
    IS_DONE = "status = 3"
    RECURRING_IS_NOT_PAUSED = "rt1_instanceCreationPaused = 0"
    RECURRING_HAS_NEXT_STARTDATE = "rt1_nextInstanceStartDate IS NOT NULL"
    MODE_TASK = "type = 0"
    MODE_PROJECT = "type = 1"

    # Variables
    debug = False
    database = FILE_DB
    filter = ""
    tag_waiting = "Waiting"
    tag_mit = "MIT"
    tag_cleanup = "Cleanup"
    tag_seinfeld = "Seinfeld"
    tag_a = "A"
    tag_b = "B"
    tag_c = "C"
    tag_d = "D"
    stat_days = 365
    anonymize = False
    config = configparser.ConfigParser()
    config.read(FILE_CONFIG, encoding="utf-8")
    mode = "to-do"
    filter_project = None
    filter_area = None
    debug_text = ""

    # pylint: disable=R0913
    def __init__(
        self,
        database=None,
        tag_waiting=None,
        tag_mit=None,
        tag_cleanup=None,
        tag_seinfeld=None,
        tag_a=None,
        tag_b=None,
        tag_c=None,
        tag_d=None,
        stat_days=None,
        anonymize=None,
        debug_text="",
    ):
        self.debug_text = debug_text

        cfg = self.get_from_config(tag_waiting, "TAG_WAITING")
        self.tag_waiting = cfg if cfg else self.tag_waiting
        self.set_config("TAG_WAITING", self.tag_waiting)

        cfg = self.get_from_config(anonymize, "ANONYMIZE")
        self.anonymize = (cfg == "True") if (cfg == "True") else self.anonymize
        self.set_config("ANONYMIZE", self.anonymize)

        cfg = self.get_from_config(tag_mit, "TAG_MIT")
        self.tag_mit = cfg if cfg else self.tag_mit
        self.set_config("TAG_MIT", self.tag_mit)

        cfg = self.get_from_config(tag_cleanup, "TAG_CLEANUP")
        self.tag_cleanup = cfg if cfg else self.tag_cleanup
        self.set_config("TAG_CLEANUP", self.tag_cleanup)

        cfg = self.get_from_config(tag_seinfeld, "TAG_SEINFELD")
        self.tag_seinfeld = cfg if cfg else self.tag_seinfeld
        self.set_config("TAG_SEINFELD", self.tag_seinfeld)

        cfg = self.get_from_config(tag_a, "TAG_A")
        self.tag_a = cfg if cfg else self.tag_a
        self.set_config("TAG_A", self.tag_a)

        cfg = self.get_from_config(tag_b, "TAG_B")
        self.tag_b = cfg if cfg else self.tag_b
        self.set_config("TAG_B", self.tag_b)

        cfg = self.get_from_config(tag_c, "TAG_C")
        self.tag_c = cfg if cfg else self.tag_c
        self.set_config("TAG_C", self.tag_c)

        cfg = self.get_from_config(tag_d, "TAG_D")
        self.tag_d = cfg if cfg else self.tag_d
        self.set_config("TAG_D", self.tag_d)

        cfg = self.get_from_config(stat_days, "STAT_DAYS")
        self.stat_days = cfg if cfg else self.stat_days
        self.set_config("STAT_DAYS", self.stat_days)

        cfg = self.get_from_config(database, "THINGSDB")
        self.database = cfg if cfg else self.database
        self.database = self.resolve_database_path(self.database)
        self.set_config("THINGSDB", self.database)

    def set_config(self, key, value, domain="DATABASE"):
        """Write variable to config."""
        if domain not in self.config:
            self.config.add_section(domain)
        if value is not None and key is not None:
            self.config.set(domain, str(key), str(value))
            with open(self.FILE_CONFIG, "w+", encoding="utf-8") as configfile:
                self.config.write(configfile)

    def get_config(self, key, domain="DATABASE"):
        """Get variable from config."""
        result = None
        if domain in self.config and key in self.config[domain]:
            result = path.expanduser(self.config[domain][key])
        return result

    def get_from_config(self, variable, key, domain="DATABASE"):
        """Set variable. Priority: input, environment, config"""
        result = None
        if variable is not None:
            result = variable
        elif environ.get(key):
            result = environ.get(key)
        elif domain in self.config and key in self.config[domain]:
            result = path.expanduser(self.config[domain][key])
        return result

    @classmethod
    def resolve_database_path(cls, database=None):
        """Resolve the configured Things database, with a demo fallback."""
        candidates = []
        if database is not None:
            candidates.append(database)
        env_database = environ.get("THINGSDB")
        if env_database:
            candidates.append(env_database)
        config_database = None
        if "DATABASE" in cls.config and "THINGSDB" in cls.config["DATABASE"]:
            config_database = path.expanduser(cls.config["DATABASE"]["THINGSDB"])
        if config_database:
            candidates.append(config_database)
        candidates.append(cls.FILE_DB)

        for candidate in candidates:
            expanded = path.expanduser(str(candidate))
            matches = glob.glob(expanded)
            if matches:
                return matches[0]
            if path.exists(expanded):
                return expanded

        demo_database = path.join(
            path.dirname(path.dirname(__file__)), "resources", "demo.sqlite3"
        )
        if path.exists(demo_database):
            return demo_database

        raise FileNotFoundError(
            "Could not locate a Things database. Set THINGSDB explicitly."
        )

    @staticmethod
    def anonymize_string(string):
        """Scramble text."""
        if string is None:
            return None
        string = list(string)
        shuffle(string)
        string = "".join(string)
        return string

    @staticmethod
    def dict_factory(cursor, row):
        """Convert SQL result into a dictionary"""
        dictionary = {}
        for idx, col in enumerate(cursor.description):
            dictionary[col[0]] = row[idx]
        return dictionary

    def anonymize_tasks(self, tasks):
        """Scramble output for screenshots."""
        if self.anonymize:
            for task in tasks:
                task["title"] = self.anonymize_string(task["title"])
                task["context"] = (
                    self.anonymize_string(task["context"]) if "context" in task else ""
                )
        return tasks

    def defaults(self, database=None):
        """Some default options for the new API."""
        defaults = {
            "type": self.mode,
            "project": self.filter_project,
            "area": self.filter_area,
        }
        if database is None:
            defaults["filepath"] = self.database
        else:
            defaults["database"] = database
        return defaults

    def run_things_query(self, callback: Callable[[Any], list[dict[str, Any]]]):
        """Run a things-py query and close the database deterministically."""
        database = things.Database(filepath=self.database)
        try:
            return callback(database)
        finally:
            database.connection.close()

    def convert_new_things_lib(self, tasks, database=None):
        """Convert tasks from new library to old expectations."""
        for task in tasks:
            task["context"] = (
                task.get("project_title")
                or task.get("area_title")
                or task.get("heading_title")
            )
            task["context_uuid"] = (
                task.get("project") or task.get("area") or task.get("heading")
            )
            task["due"] = task.get("deadline")
            task["started"] = task.get("start_date")
            kwargs: dict[str, Any] = {"count_only": True}
            if database is None:
                kwargs["filepath"] = self.database
            else:
                kwargs["database"] = database
            task["size"] = things.projects(task["uuid"], **kwargs)
        tasks.sort(key=lambda task: task["title"] or "", reverse=False)
        tasks = self.anonymize_tasks(tasks)
        return tasks

    def get_inbox(self):
        """Get tasks from inbox."""
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.inbox(**self.defaults(database=database)), database=database
            )
        )

    def get_today(self):
        """Get tasks from today."""
        tasks = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.today(**self.defaults(database=database)), database=database
            )
        )
        tasks.sort(key=lambda task: task.get("started", ""), reverse=True)
        tasks.sort(key=lambda task: task.get("todayIndex", ""), reverse=False)
        return tasks

    def get_task(self, area=None, project=None):
        """Get tasks."""
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.tasks(
                    type=self.mode,
                    area=area,
                    project=project,
                    database=database,
                ),
                database=database,
            )
        )

    def get_someday(self):
        """Get someday tasks."""
        tasks = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.someday(**self.defaults(database=database)), database=database
            )
        )
        tasks.sort(key=lambda task: task["deadline"] or "", reverse=True)
        return tasks

    def get_upcoming(self):
        """Get upcoming tasks."""
        tasks = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.upcoming(**self.defaults(database=database)), database=database
            )
        )
        tasks.sort(key=lambda task: task["started"] or "", reverse=False)
        return tasks

    def get_waiting(self):
        """Get waiting tasks."""
        tasks = self.get_tag(self.tag_waiting)
        tasks.sort(key=lambda task: task["started"] or "", reverse=False)
        return tasks

    def get_mit(self):
        """Get most important tasks."""
        return self.get_tag(self.tag_mit)

    def get_tag(self, tag):
        """Get task with specific tag."""
        try:
            tasks = self.run_things_query(
                lambda database: self.convert_new_things_lib(
                    things.tasks(tag=tag, **self.defaults(database=database)),
                    database=database,
                )
            )
        except ValueError:
            tasks = []
        if tag in [self.tag_waiting]:
            tasks.sort(key=lambda task: task["started"] or "", reverse=False)
        return tasks

    def get_tag_today(self, tag):
        """Get today tasks with specific tag."""
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.today(tag=tag, **self.defaults(database=database)),
                database=database,
            )
        )

    def get_anytime(self):
        """Get anytime tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_ANYTIME} AND
                TASK.{self.IS_NOT_SCHEDULED} AND (
                    (
                        PROJECT.title IS NULL OR (
                            PROJECT.{self.IS_ANYTIME} AND
                            PROJECT.{self.IS_NOT_SCHEDULED} AND
                            PROJECT.{self.IS_NOT_TRASHED}
                        )
                    ) AND (
                        HEADPROJ.title IS NULL OR (
                            HEADPROJ.{self.IS_ANYTIME} AND
                            HEADPROJ.{self.IS_NOT_SCHEDULED} AND
                            HEADPROJ.{self.IS_NOT_TRASHED}
                        )
                    )
                )
                ORDER BY TASK.deadline DESC , TASK.todayIndex
                """
        if self.filter:
            # ugly hack for Kanban task view on project
            query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_ANYTIME} AND
                TASK.{self.IS_NOT_SCHEDULED} AND (
                    (
                        PROJECT.title IS NULL OR (
                            PROJECT.{self.IS_NOT_TRASHED}
                        )
                    ) AND (
                        HEADPROJ.title IS NULL OR (
                            HEADPROJ.{self.IS_NOT_TRASHED}
                        )
                    )
                )
                ORDER BY TASK.deadline DESC , TASK.todayIndex
                """
        return self.get_rows(query)

    def get_completed(self):
        """Get completed tasks."""
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.completed(**self.defaults(database=database)),
                database=database,
            )
        )

    def get_cancelled(self):
        """Get cancelled tasks."""
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.canceled(**self.defaults(database=database)), database=database
            )
        )

    def get_trashed(self):
        """Get trashed tasks."""
        query = f"""
                TASK.{self.IS_TRASHED} AND
                TASK.{self.IS_TASK}
                ORDER BY TASK.{self.DATE_STOP}
                """
        return self.get_rows(query)

    def get_projects(self, area=None):
        """Get projects."""
        projects = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.projects(area=area, database=database),
                database=database,
            )
        )
        for project in projects:
            project["size"] = self.run_things_query(
                lambda database: things.todos(
                    project=project["uuid"],
                    count_only=True,
                    database=database,
                )
            )
        return projects

    def get_areas(self):
        """Get areas."""
        areas = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.areas(database=database), database=database
            )
        )
        for area in areas:
            area["size"] = self.run_things_query(
                lambda database: things.todos(
                    area=area["uuid"],
                    count_only=True,
                    database=database,
                )
            )
        return areas

    def get_all(self):
        """Get all tasks."""
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.tasks(**self.defaults(database=database)), database=database
            )
        )

    def get_due(self):
        """Get due tasks."""
        tasks = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.deadlines(**self.defaults(database=database)),
                database=database,
            )
        )
        tasks.sort(key=lambda task: task["deadline"] or "", reverse=False)
        return tasks

    def get_lint(self):
        """Get tasks that float around"""
        query = f"""
            TASK.{self.IS_NOT_TRASHED} AND
            TASK.{self.IS_OPEN} AND
            TASK.{self.IS_TASK} AND
            (TASK.{self.IS_SOMEDAY} OR TASK.{self.IS_ANYTIME}) AND
            TASK.project IS NULL AND
            TASK.area IS NULL AND
            TASK.heading IS NULL
            """
        return self.get_rows(query)

    def get_empty_projects(self):
        """Get projects that are empty"""
        query = f"""
            TASK.{self.IS_NOT_TRASHED} AND
            TASK.{self.IS_OPEN} AND
            TASK.{self.IS_PROJECT} AND
            TASK.{self.IS_ANYTIME}
            GROUP BY TASK.uuid
            HAVING
                (SELECT COUNT(uuid)
                 FROM TMTask AS PROJECT_TASK
                 WHERE
                   PROJECT_TASK.project = TASK.uuid AND
                   PROJECT_TASK.{self.IS_NOT_TRASHED} AND
                   PROJECT_TASK.{self.IS_OPEN} AND
                   (PROJECT_TASK.{self.IS_ANYTIME} OR
                    PROJECT_TASK.{self.IS_SCHEDULED} OR
                      (PROJECT_TASK.{self.IS_RECURRING} AND
                       PROJECT_TASK.{self.RECURRING_IS_NOT_PAUSED} AND
                       PROJECT_TASK.{self.RECURRING_HAS_NEXT_STARTDATE}
                      )
                   )
                ) = 0
            """
        return self.get_rows(query)

    def get_largest_projects(self):
        """Get projects that are empty"""
        query = f"""
            SELECT
                TASK.uuid,
                TASK.title AS title,
                {self.DATE_CREATE} AS created,
                {self.DATE_MOD} AS modified,
                (SELECT COUNT(uuid)
                 FROM TMTask AS PROJECT_TASK
                 WHERE
                   PROJECT_TASK.project = TASK.uuid AND
                   PROJECT_TASK.{self.IS_NOT_TRASHED} AND
                   PROJECT_TASK.{self.IS_OPEN}
                ) AS tasks
            FROM
                {self.TABLE_TASK} AS TASK
            WHERE
               TASK.{self.IS_NOT_TRASHED} AND
               TASK.{self.IS_OPEN} AND
               TASK.{self.IS_PROJECT}
            GROUP BY TASK.uuid
            ORDER BY tasks COLLATE NOCASE DESC
            """
        return self.execute_query(query)

    def get_daystats(self):
        """Get a history of task activities"""
        query = f"""
                WITH RECURSIVE timeseries(x) AS (
                    SELECT 0
                    UNION ALL
                    SELECT x+1 FROM timeseries
                    LIMIT {self.stat_days}
                )
                SELECT
                    date(julianday("now", "-{self.stat_days} days"),
                         "+" || x || " days") as date,
                    CREATED.TasksCreated as created,
                    CLOSED.TasksClosed as completed,
                    CANCELLED.TasksCancelled as cancelled,
                    TRASHED.TasksTrashed as trashed
                FROM timeseries
                LEFT JOIN
                    (SELECT COUNT(uuid) AS TasksCreated,
                        date({self.DATE_CREATE},"unixepoch") AS DAY
                        FROM {self.TABLE_TASK} AS TASK
                        WHERE DAY NOT NULL
                          AND TASK.{self.IS_TASK}
                        GROUP BY DAY)
                    AS CREATED ON CREATED.DAY = date
                LEFT JOIN
                    (SELECT COUNT(uuid) AS TasksCancelled,
                        date(stopDate,"unixepoch") AS DAY
                        FROM {self.TABLE_TASK} AS TASK
                        WHERE DAY NOT NULL
                          AND TASK.{self.IS_CANCELLED} AND TASK.{self.IS_TASK}
                        GROUP BY DAY)
                        AS CANCELLED ON CANCELLED.DAY = date
                LEFT JOIN
                    (SELECT COUNT(uuid) AS TasksTrashed,
                        date({self.DATE_MOD},"unixepoch") AS DAY
                        FROM {self.TABLE_TASK} AS TASK
                        WHERE DAY NOT NULL
                          AND TASK.{self.IS_TRASHED} AND TASK.{self.IS_TASK}
                        GROUP BY DAY)
                        AS TRASHED ON TRASHED.DAY = date
                LEFT JOIN
                    (SELECT COUNT(uuid) AS TasksClosed,
                        date(stopDate,"unixepoch") AS DAY
                        FROM {self.TABLE_TASK} AS TASK
                        WHERE DAY NOT NULL
                          AND TASK.{self.IS_DONE} AND TASK.{self.IS_TASK}
                        GROUP BY DAY)
                        AS CLOSED ON CLOSED.DAY = date
                """
        return self.execute_query(query)

    def get_minutes_today(self):
        """Count the planned minutes for today."""
        tasks = self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.today(**self.defaults(database=database)), database=database
            )
        )
        minutes = 0
        for task in tasks:
            for tag in task.get("tags", []):
                try:
                    minutes += int(tag)
                except ValueError:
                    pass
        return [{"minutes": minutes}]

    def get_seinfeld(self, tag):
        """Tasks logged recently with a specific tag."""

        stop_date = (datetime.today() - timedelta(days=66)).strftime("%Y-%m-%d")
        return self.run_things_query(
            lambda database: self.convert_new_things_lib(
                things.logbook(
                    **self.defaults(database=database),
                    stop_date=stop_date,
                    tag=tag,
                ),
                database=database,
            )
        )

    def get_cleanup(self):
        """Tasks and projects that need work."""
        result = []
        result.extend(self.get_lint())
        result.extend(self.get_empty_projects())
        result.extend(self.get_tag(self.tag_cleanup))
        result = [i for n, i in enumerate(result) if i not in result[n + 1 :]]
        return result

    def reset_config(self):
        """Reset the configuration."""
        print("Deleting: " + self.FILE_CONFIG)
        os.remove(self.FILE_CONFIG)

    def feedback(self):
        """Send feedback."""

        recipient = "support@kanbanview.app"
        subject = "[KanbanView] Feedback"
        body = f"""
Description:
Version: {__version__}

Steps that will reproduce the problem?
1.
2.
3.

What is the expected result?


What happens instead?


Possible workaround:


Any additional information:
========= DEBUG INFORMATION =========
{self.debug_text}
========= DEBUG INFORMATION =========
        """
        # with open("body.txt", "r") as b:
        #     body = b.read()
        # body = body.replace(" ", "%20")
        print(body)
        webbrowser.open(
            "mailto:?to=" + recipient + "&subject=" + subject + "&body=" + body, new=1
        )

    @staticmethod
    def get_not_implemented():
        """Not implemented warning."""
        return [{"title": "not implemented"}]

    def get_rows(self, sql):
        """Query Things database."""

        sql = f"""
            SELECT DISTINCT
                TASK.uuid,
                TASK.title,
                CASE
                    WHEN AREA.title IS NOT NULL THEN AREA.title
                    WHEN PROJECT.title IS NOT NULL THEN PROJECT.title
                    WHEN HEADING.title IS NOT NULL THEN HEADING.title
                END AS context,
                CASE
                    WHEN AREA.uuid IS NOT NULL THEN AREA.uuid
                    WHEN PROJECT.uuid IS NOT NULL THEN PROJECT.uuid
                END AS context_uuid,
                CASE
                    WHEN TASK.rt1_recurrenceRule IS NULL
                    THEN strftime('%d.%m.', TASK.deadline,"unixepoch") ||
                         substr(strftime('%Y', TASK.deadline,"unixepoch"),3, 2)
                ELSE NULL
                END AS due,
                date(TASK.{self.DATE_CREATE},"unixepoch") as created,
                date(TASK.{self.DATE_MOD},"unixepoch") as modified,
                strftime('%d.%m.', TASK.startDate,"unixepoch") ||
                  substr(strftime('%Y', TASK.startDate,"unixepoch"),3, 2)
                  as started,
                date(TASK.stopDate,"unixepoch") as stopped,
                (SELECT COUNT(uuid)
                 FROM TMTask AS PROJECT_TASK
                 WHERE
                   PROJECT_TASK.project = TASK.uuid AND
                   PROJECT_TASK.{self.IS_NOT_TRASHED} AND
                   PROJECT_TASK.{self.IS_OPEN}
                ) AS size,
                CASE
                    WHEN TASK.{self.IS_TASK} THEN 'task'
                    WHEN TASK.{self.IS_PROJECT} THEN 'project'
                    WHEN TASK.{self.IS_HEADING} THEN 'heading'
                END AS type,
                CASE
                    WHEN TASK.{self.IS_OPEN} THEN 'open'
                    WHEN TASK.{self.IS_CANCELLED} THEN 'cancelled'
                    WHEN TASK.{self.IS_DONE} THEN 'done'
                END AS status,
                TASK.notes
            FROM
                {self.TABLE_TASK} AS TASK
            LEFT OUTER JOIN
                {self.TABLE_TASK} PROJECT ON TASK.project = PROJECT.uuid
            LEFT OUTER JOIN
                {self.TABLE_AREA} AREA ON TASK.area = AREA.uuid
            LEFT OUTER JOIN
                {self.TABLE_TASK} HEADING ON TASK.heading = HEADING.uuid
            LEFT OUTER JOIN
                {self.TABLE_TASK} HEADPROJ ON HEADING.project = HEADPROJ.uuid
            LEFT OUTER JOIN
                {self.TABLE_TASKTAG} TAGS ON TASK.uuid = TAGS.tasks
            LEFT OUTER JOIN
                {self.TABLE_TAG} TAG ON TAGS.tags = TAG.uuid
            WHERE
                {self.filter}
                {sql}
                """

        return self.execute_query(sql)

    def execute_query(self, sql):
        """Run the actual query"""
        if self.debug is True:
            print(self.database)
            print(sql)
        try:
            with closing(
                sqlite3.connect(  # pylint: disable=E1101
                    "file:" + self.database + "?mode=ro", uri=True
                )
            ) as connection:
                connection.row_factory = Things3.dict_factory
                cursor = connection.cursor()
                cursor.execute(sql)
                tasks = cursor.fetchall()
                cursor.close()
            tasks = self.anonymize_tasks(tasks)
            if self.debug:
                for task in tasks:
                    print(task)
            return tasks
        except sqlite3.OperationalError as error:  # pylint: disable=E1101
            print(f"Could not query the database at: {self.database}.")
            print(f"Details: {error}.")
            sys.exit(2)

    # pylint: disable=C0103
    def mode_project(self):
        """Hack to switch to project view"""
        self.mode = "project"
        self.IS_TASK = self.MODE_PROJECT

    # pylint: disable=C0103
    def mode_task(self):
        """Hack to switch to project view"""
        self.mode = "to-do"
        self.IS_TASK = self.MODE_TASK

    functions = {
        "inbox": get_inbox,
        "today": get_today,
        "next": get_anytime,
        "backlog": get_someday,
        "upcoming": get_upcoming,
        "waiting": get_waiting,
        "mit": get_mit,
        "completed": get_completed,
        "cancelled": get_cancelled,
        "trashed": get_trashed,
        "projects": get_projects,
        "areas": get_areas,
        "all": get_all,
        "due": get_due,
        "lint": get_lint,
        "empty": get_empty_projects,
        "cleanup": get_cleanup,
        "top-proj": get_largest_projects,
        "stats-day": get_daystats,
        "stats-min-today": get_minutes_today,
        "reset": reset_config,
        "feedback": feedback,
    }
