#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""KanbanView (static) for Things 3."""

from __future__ import print_function

from os import getcwd

from things3.things3 import Things3

# Basic variables
FILE_HTML = getcwd() + "/kanban-static.html"
THINGS3 = Things3()


def write_html_column(cssclass, file, header, rows):
    """Create a column in the output."""

    file.write(
        "<div class='column'><div class=''>"
        + "<h2 class='h2 "
        + cssclass
        + "'>"
        + header
        + "<span class='size'>"
        + str(len(rows))
        + "</span></h2>"
    )

    for row in rows:
        task_uuid = str(row["uuid"]) if row["uuid"] is not None else ""
        task_title = str(row["title"]) if row["title"] is not None else ""
        context_title = str(row["context"]) if row["context"] is not None else ""
        context_uuid = (
            str(row["context_uuid"]) if row["context_uuid"] is not None else ""
        )
        deadline = str(row["due"]) if row["due"] is not None else ""

        task_link = (
            '<a href="things:///show?id=' + task_uuid + '">' + task_title + "</a>"
            if task_uuid != ""
            else task_title
        )
        context_link = (
            '<a href="things:///show?id=' + context_uuid + '">' + context_title + "</a>"
            if context_uuid != ""
            else context_title
        )
        css_class = "hasProject" if context_title != "" else "hasNoProject"
        css_class = "hasDeadline" if deadline != "" else css_class

        file.write(
            '<div class="box">'
            + task_link
            + '<div class="deadline">'
            + deadline
            + "</div>"
            + '<div class="area '
            + css_class
            + '">'
            + context_link
            + "</div>"
            + "</div>"
        )
    file.write("</div></div>")


def write_html_header(file):
    """Write HTML header."""

    message = """
        <!DOCTYPE html>
        <html>
        <head>
          <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
          <link rel="stylesheet" href="./resources/kanban.css">
          <title>KanbanView for Things 3</title>
        </head>

        <body>
            <header>
                <a href="https://kanbanview.app"
                    title="visit product page" target="_blank">
                <picture id="app">
                    <source class="logo" srcset="resources/logo-dark.png"
                        media="(prefers-color-scheme: dark)">
                    <img class="logo" src="resources/logo.png" alt="logo">
                </picture>
                </a>
            </header>
          <article class='some-page-wrapper'>
            <div class='row'>
        """
    file.write(message)


def write_html_footer(file):
    """Write HTML footer."""

    message = """
            </div>
          </article>
        <footer class="footer"><br />
        Copyright &copy;2020 Alexander Willner
        </footer></body></html>"""
    file.write(message)


def write_html_columns(file):
    """Write HTML columns."""

    write_html_column("color1", file, "Backlog", THINGS3.get_someday())
    write_html_column("color8", file, "Grooming", THINGS3.get_cleanup())
    write_html_column("color5", file, "Upcoming", THINGS3.get_upcoming())
    write_html_column("color3", file, "Waiting", THINGS3.get_waiting())
    write_html_column("color4", file, "Inbox", THINGS3.get_inbox())
    write_html_column("color2", file, "MIT", THINGS3.get_mit())
    write_html_column("color6", file, "Today", THINGS3.get_today())
    write_html_column("color7", file, "Next", THINGS3.get_anytime())


def main(output):
    """Convert Things 3 database to Kanban HTML view."""

    with output as file:
        write_html_header(file)
        write_html_columns(file)
        write_html_footer(file)


if __name__ == "__main__":
    with open(FILE_HTML, "w", encoding="utf-8") as target:
        main(target)
