#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple read-only Things 3 Web Serivce."""

from __future__ import print_function

import json
import socket
import sys
from os import getcwd
from typing import Any, Callable, cast

from flask import Flask, Response, request
from werkzeug.serving import make_server

from things3.things3 import Things3


class Things3API:
    """API Wrapper for the simple read-only API for Things 3."""

    PATH = getcwd() + "/resources/"
    DEFAULT = "kanban.html"
    test_mode = "task"
    host = "localhost"
    port = 15000

    def on_get(self, url=DEFAULT):
        """Handles other GET requests"""
        status = 200
        filename = self.PATH + url
        content_type = "application/json"
        if filename.endswith("css"):
            content_type = "text/css"
        if filename.endswith("html"):
            content_type = "text/html"
        if filename.endswith("js"):
            content_type = "text/javascript"
        if filename.endswith("png"):
            content_type = "image/png"
        if filename.endswith("jpg"):
            content_type = "image/jpeg"
        if filename.endswith("ico"):
            content_type = "image/x-ico"
        try:
            with open(filename, "rb") as source:
                data = source.read()
        except FileNotFoundError:
            data = "not found"
            content_type = "text"
            status = 404
        return Response(response=data, content_type=content_type, status=status)

    def mode_selector(self):
        """Switch between project and task mode"""
        try:
            mode = request.args.get("mode")
        except RuntimeError:
            mode = "task"
        if mode == "project" or self.test_mode == "project":
            self.things3.mode_project()

    def config_get(self, key):
        """Read key from config"""
        data = self.things3.get_config(key)
        return Response(response=data)

    def config_set(self, key):
        """Write key to config"""
        value = request.get_data().decode("utf-8").strip()
        if value:
            self.things3.set_config(key, value)
        return Response()

    def seinfeld(self, tag):
        """Get tasks logged recently with a specific tag."""
        data = self.things3.get_seinfeld(tag)
        data = json.dumps(data)
        return Response(response=data, content_type="application/json")

    def tag(self, tag, area=None):
        """Get specific tag."""
        self.mode_selector()
        if area is not None:
            data = self.things3.get_tag_today(tag)
        else:
            data = self.things3.get_tag(tag)
        self.things3.mode_task()
        data = json.dumps(data)
        return Response(response=data, content_type="application/json")

    def api(self, command):
        """Return database as JSON strings."""
        if command in self.things3.functions:
            func = cast(
                Callable[[Things3], list[dict[str, Any]]],
                self.things3.functions[command],
            )
            self.mode_selector()
            data = func(self.things3)
            self.things3.mode_task()
            data = json.dumps(data)
            return Response(response=data, content_type="application/json")

        data = json.dumps(self.things3.get_not_implemented())
        return Response(response=data, content_type="application/json", status=404)

    def get_url(self):
        """Get the public url for the endpoint"""
        fqdn = f"{socket.gethostname()}.local"  # pylint: disable=E1101
        return f"http://{fqdn}:{self.port}"

    def api_filter(self, mode, uuid):
        """Filter view by specific modifiers"""
        if mode == "area" and uuid != "":
            self.things3.filter = f"TASK.area = '{uuid}' AND"
            self.things3.filter_area = uuid
        if mode == "project" and uuid != "":
            self.things3.filter = f"""
                (TASK.project = '{uuid}' OR HEADING.project = '{uuid}') AND
                """
            self.things3.filter_project = uuid
        return Response(status=200)

    def api_filter_reset(self):
        """Reset filter modifiers"""
        self.things3.filter = ""
        self.things3.filter_project = None
        self.things3.filter_area = None
        return Response(status=200)

    def __init__(self, database=None, host=None, port=None, expose=None, debug_text=""):
        # pylint: disable-msg=too-many-arguments
        self.things3 = Things3(database=database, debug_text=debug_text)

        cfg = self.things3.get_from_config(host, "KANBANVIEW_HOST")
        self.host = cfg if cfg else self.host
        self.things3.set_config("KANBANVIEW_HOST", self.host)

        cfg = self.things3.get_from_config(port, "KANBANVIEW_PORT")
        self.port = cfg if cfg else self.port
        self.things3.set_config("KANBANVIEW_PORT", self.port)

        cfg = self.things3.get_from_config(expose, "API_EXPOSE")
        self.host = "0.0.0.0" if (str(cfg).lower() == "true") else "localhost"
        self.things3.set_config("KANBANVIEW_HOST", self.host)
        self.things3.set_config("API_EXPOSE", str(cfg).lower() == "true")

        self.flask = Flask(__name__)
        self.flask.add_url_rule("/config/<key>", view_func=self.config_get)
        self.flask.add_url_rule(
            "/config/<key>", view_func=self.config_set, methods=["PUT"]
        )
        self.flask.add_url_rule("/api/<command>", view_func=self.api)
        self.flask.add_url_rule("/api/<command>", view_func=self.api, methods=["PUT"])
        self.flask.add_url_rule("/api/url", view_func=self.get_url)
        self.flask.add_url_rule("/api/seinfeld/<tag>", view_func=self.seinfeld)
        self.flask.add_url_rule("/api/tag/<tag>", view_func=self.tag)
        self.flask.add_url_rule("/api/tag/<tag>/<area>", view_func=self.tag)
        self.flask.add_url_rule("/api/filter/<mode>/<uuid>", view_func=self.api_filter)
        self.flask.add_url_rule("/api/filter/reset", view_func=self.api_filter_reset)
        self.flask.add_url_rule("/<url>", view_func=self.on_get)
        self.flask.add_url_rule("/", view_func=self.on_get)
        self.flask.app_context().push()
        self.flask_context = None

    def main(self):
        """Main function."""
        print(f"Serving at http://{self.host}:{self.port} ...")

        try:
            self.flask_context = make_server(
                self.host, self.port, self.flask, threaded=True
            )
            self.flask_context.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down...")
            sys.exit(0)


def main():
    """Main entry point for CLI installation"""
    Things3API().main()


if __name__ == "__main__":
    main()
