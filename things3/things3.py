#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple read-only API for Things 3."""

from __future__ import print_function

__author__ = "Alexander Willner"
__copyright__ = "2020 Alexander Willner"
__credits__ = ["Alexander Willner"]
__license__ = "Apache License 2.0"
__version__ = "2.5.0"
__maintainer__ = "Alexander Willner"
__email__ = "alex@willner.ws"
__status__ = "Development"

import sqlite3
import sys
from random import shuffle
from os import environ
import getpass
import configparser
from pathlib import Path


# pylint: disable=R0904
class Things3():
    """Simple read-only API for Things 3."""

    # Database info
    FILE_DB = '/Library/Containers/'\
              'com.culturedcode.ThingsMac/Data/Library/'\
              'Application Support/Cultured Code/Things/Things.sqlite3'

    TABLE_TASK = "TMTask"
    TABLE_AREA = "TMArea"
    TABLE_TAG = "TMTag"
    TABLE_TASKTAG = "TMTaskTag"
    DATE_CREATE = "creationDate"
    DATE_MOD = "userModificationDate"
    DATE_DUE = "dueDate"
    DATE_START = "startDate"
    DATE_STOP = "stopDate"
    IS_INBOX = "start = 0"
    IS_ANYTIME = "start = 1"
    IS_SOMEDAY = "start = 2"
    IS_SCHEDULED = f"{DATE_START} IS NOT NULL"
    IS_NOT_SCHEDULED = f"{DATE_START} IS NULL"
    IS_DUE = f"{DATE_DUE} IS NOT NULL"
    IS_NOT_DUE = f"{DATE_DUE} IS NULL"
    IS_RECURRING = "recurrenceRule IS NOT NULL"
    IS_NOT_RECURRING = "recurrenceRule IS NULL"
    IS_TASK = "type = 0"
    IS_PROJECT = "type = 1"
    IS_HEADING = "type = 2"
    IS_TRASHED = "trashed = 1"
    IS_NOT_TRASHED = "trashed = 0"
    IS_OPEN = "status = 0"
    IS_CANCELLED = "status = 2"
    IS_DONE = "status = 3"
    RECURRING_IS_NOT_PAUSED = "instanceCreationPaused = 0"
    RECURRING_HAS_NEXT_STARTDATE = "nextInstanceStartDate IS NOT NULL"
    MODE_TASK = "type = 0"
    MODE_PROJECT = "type = 1"

    # Variables
    debug = False
    user = getpass.getuser()
    database = f"/Users/{user}/{FILE_DB}"
    filter = ""
    tag_waiting = "Waiting"
    tag_mit = "MIT"
    tag_cleanup = "Cleanup"
    anonymize = False
    config = configparser.ConfigParser()
    config.read(str(Path.home()) + '/.kanbanviewrc')

    # pylint: disable=R0913
    def __init__(self,
                 database=None,
                 tag_waiting=None,
                 tag_mit=None,
                 tag_cleanup=None,
                 anonymize=None):

        cfg = self.get_from_config(self.config, tag_waiting, 'TAG_WAITING')
        self.tag_waiting = cfg if cfg else self.tag_waiting

        cfg = self.get_from_config(self.config, anonymize, 'ANONYMIZE')
        self.anonymize = cfg if cfg else self.anonymize

        cfg = self.get_from_config(self.config, tag_mit, 'TAG_MIT')
        self.tag_mit = cfg if cfg else self.tag_mit

        cfg = self.get_from_config(self.config, tag_cleanup, 'TAG_CLEANUP')
        self.tag_cleanup = cfg if cfg else self.tag_cleanup

        cfg = self.get_from_config(self.config, database, 'THINGSDB')
        self.database = cfg if cfg else self.database

    @staticmethod
    def get_from_config(config, variable, preference):
        """Set variable. Priority: input, environment, config"""
        result = None
        if variable is not None:
            result = variable
        elif environ.get(preference):
            result = environ.get(preference)
        elif 'DATABASE' in config and preference in config['DATABASE']:
            result = config['DATABASE'][preference]
        return result

    @staticmethod
    def anonymize_string(string):
        """Scramble text."""
        if string is None:
            return None
        string = list(string)
        shuffle(string)
        string = ''.join(string)
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
                task['title'] = self.anonymize_string(task['title'])
                task['context'] = self.anonymize_string(task['context'])
        return tasks

    def get_inbox(self):
        """Get all tasks from the inbox."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_INBOX}
                ORDER BY TASK.duedate DESC , TASK.todayIndex
                """
        return self.get_rows(query)

    def get_today(self):
        """Get all tasks from the today list."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                (TASK.{self.IS_ANYTIME} OR (
                     TASK.{self.IS_SOMEDAY} AND
                     TASK.{self.DATE_START} <= strftime('%s', 'now')
                     )
                ) AND
                TASK.{self.IS_SCHEDULED} AND (
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
                ORDER BY TASK.duedate DESC , TASK.todayIndex
                """
        return self.get_rows(query)

    def get_someday(self):
        """Get someday tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_SOMEDAY} AND
                TASK.{self.IS_NOT_SCHEDULED} AND
                TASK.{self.IS_NOT_RECURRING} AND (
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
                ORDER BY TASK.duedate DESC, TASK.creationdate DESC
                """
        return self.get_rows(query)

    def get_upcoming(self):
        """Get upcoming tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_SOMEDAY} AND
                TASK.{self.IS_SCHEDULED} AND
                TASK.{self.IS_NOT_RECURRING} AND (
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
                ORDER BY TASK.startdate, TASK.todayIndex
                """
        return self.get_rows(query)

    def get_waiting(self):
        """Get waiting tasks."""
        return self.get_tag(self.tag_waiting)

    def get_mit(self):
        """Get most important tasks."""
        return self.get_tag(self.tag_mit)

    def get_tag(self, tag):
        """Get task with specific tag"""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_NOT_RECURRING} AND
                TAGS.tags=(SELECT uuid FROM {self.TABLE_TAG}
                             WHERE title='{tag}'
                          )
                AND (
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
                ORDER BY TASK.duedate DESC , TASK.todayIndex
                """
        return self.get_rows(query)

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
                ORDER BY TASK.duedate DESC , TASK.todayIndex
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
                ORDER BY TASK.duedate DESC , TASK.todayIndex
                """
        return self.get_rows(query)

    def get_completed(self):
        """Get completed tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_DONE}
                ORDER BY TASK.{self.DATE_STOP}
                """
        return self.get_rows(query)

    def get_cancelled(self):
        """Get cancelled tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_CANCELLED}
                ORDER BY TASK.{self.DATE_STOP}
                """
        return self.get_rows(query)

    def get_trashed(self):
        """Get trashed tasks."""
        query = f"""
                TASK.{self.IS_TRASHED} AND
                TASK.{self.IS_TASK}
                ORDER BY TASK.{self.DATE_STOP}
                """
        return self.get_rows(query)

    def get_projects(self):
        """Get projects."""
        query = f"""
                SELECT
                    TASK.uuid,
                    TASK.title,
                    NULL as context
                FROM
                    {self.TABLE_TASK} AS TASK
                WHERE
                    TASK.{self.IS_NOT_TRASHED} AND
                    TASK.{self.IS_PROJECT} AND
                    TASK.{self.IS_OPEN}
                ORDER BY TASK.title
                """
        return self.execute_query(query)

    def get_areas(self):
        """Get areas."""
        query = f"""
            SELECT
                AREA.uuid AS uuid,
                AREA.title AS title
            FROM
                {self.TABLE_AREA} AS AREA
            ORDER BY AREA.title
            """
        return self.execute_query(query)

    def get_all(self):
        """Get all tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND (
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
                """
        return self.get_rows(query)

    def get_due(self):
        """Get due tasks."""
        query = f"""
                TASK.{self.IS_NOT_TRASHED} AND
                TASK.{self.IS_TASK} AND
                TASK.{self.IS_OPEN} AND
                TASK.{self.IS_DUE} AND (
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
                ORDER BY TASK.{self.DATE_DUE}
                """
        return self.get_rows(query)

    def get_lint(self):
        """Get tasks that float around"""
        query = f"""
            TASK.{self.IS_NOT_TRASHED} AND
            TASK.{self.IS_OPEN} AND
            TASK.{self.IS_TASK} AND
            (TASK.{self.IS_SOMEDAY} OR TASK.{self.IS_ANYTIME}) AND
            TASK.project IS NULL AND
            TASK.area IS NULL AND
            TASK.actionGroup IS NULL
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
                creationDate AS created,
                userModificationDate AS modified,
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
            ORDER BY tasks DESC
            """
        return self.execute_query(query)

    def get_daystats(self):
        """Get a history of task activities"""
        days = 365
        query = f"""
                WITH RECURSIVE timeseries(x) AS (
                    SELECT 0
                    UNION ALL
                    SELECT x+1 FROM timeseries
                    LIMIT {days}
                )
                SELECT
                    date(julianday("now", "-{days} days"),
                         "+" || x || " days") as date,
                    CREATED.TasksCreated as created,
                    CLOSED.TasksClosed as completed,
                    CANCELLED.TasksCancelled as cancelled,
                    TRASHED.TasksTrashed as trashed
                FROM timeseries
                LEFT JOIN
                    (SELECT COUNT(uuid) AS TasksCreated,
                        date(creationDate,"unixepoch") AS DAY
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
                        date(userModificationDate,"unixepoch") AS DAY
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
        query = f"""
                SELECT
                    SUM(TAG.title) AS minutes
                FROM
                    {self.TABLE_TASK} AS TASK
                LEFT OUTER JOIN
                TMTask PROJECT ON TASK.project = PROJECT.uuid
                LEFT OUTER JOIN
                    TMArea AREA ON TASK.area = AREA.uuid
                LEFT OUTER JOIN
                    TMTask HEADING ON TASK.actionGroup = HEADING.uuid
                LEFT OUTER JOIN
                    TMTask HEADPROJ ON HEADING.project = HEADPROJ.uuid
                LEFT OUTER JOIN
                    TMTaskTag TAGS ON TASK.uuid = TAGS.tasks
                LEFT OUTER JOIN
                    TMTag TAG ON TAGS.tags = TAG.uuid
                WHERE
                    printf("%d", TAG.title) = TAG.title AND
                    TASK.{self.IS_NOT_TRASHED} AND
                    TASK.{self.IS_TASK} AND
                    TASK.{self.IS_OPEN} AND
                    TASK.{self.IS_ANYTIME} AND
                    TASK.{self.IS_SCHEDULED} AND (
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
                """
        return self.execute_query(query)

    def get_cleanup(self):
        """Tasks and projects that need work."""
        result = []
        result.extend(self.get_lint())
        result.extend(self.get_empty_projects())
        result.extend(self.get_tag(self.tag_cleanup))
        return result

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
                    WHEN TASK.recurrenceRule IS NULL
                    THEN date(TASK.dueDate,"unixepoch")
                ELSE NULL
                END AS due,
                date(TASK.creationDate,"unixepoch") as created,
                date(TASK.userModificationDate,"unixepoch") as modified,
                date(TASK.startDate,"unixepoch") as started,
                date(TASK.stopDate,"unixepoch") as stopped,
                (SELECT COUNT(uuid)
                 FROM TMTask AS PROJECT_TASK
                 WHERE
                   PROJECT_TASK.project = TASK.uuid AND
                   PROJECT_TASK.{self.IS_NOT_TRASHED} AND
                   PROJECT_TASK.{self.IS_OPEN}
                ) AS size,
                CASE
                    WHEN TASK.type = 0 THEN 'task'
                    WHEN TASK.type = 1 THEN 'project'
                    WHEN TASK.type = 2 THEN 'heading'
                END AS type
            FROM
                {self.TABLE_TASK} AS TASK
            LEFT OUTER JOIN
                {self.TABLE_TASK} PROJECT ON TASK.project = PROJECT.uuid
            LEFT OUTER JOIN
                {self.TABLE_AREA} AREA ON TASK.area = AREA.uuid
            LEFT OUTER JOIN
                {self.TABLE_TASK} HEADING ON TASK.actionGroup = HEADING.uuid
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
            print(sql)
        try:
            connection = sqlite3.connect(self.database)
            connection.row_factory = Things3.dict_factory
            cursor = connection.cursor()
            cursor.execute(sql)
            tasks = cursor.fetchall()
            tasks = self.anonymize_tasks(tasks)
            if self.debug:
                for task in tasks:
                    print(task)
            return tasks
        except sqlite3.OperationalError as error:
            print(f"Could not query the database at: {self.database}.")
            print(f"Details: {error}.")
            sys.exit(2)

    # pylint: disable=C0103
    def mode_project(self):
        """Hack to switch to project view"""
        self.IS_TASK = self.MODE_PROJECT

    # pylint: disable=C0103
    def mode_task(self):
        """Hack to switch to project view"""
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
        "stats-min-today": get_minutes_today
    }
