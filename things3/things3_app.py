#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""KanbanView (app) for Things 3."""

from __future__ import print_function

import os
import signal
import subprocess
import sys
from threading import Thread
from typing import Any

import webview

from things3 import things3, things3_api


class AppBridge:
    """Bridge methods exposed to the pywebview JavaScript runtime."""

    def open_url(self, url):
        """Open an external URL via Launch Services."""
        subprocess.run(
            ["open", "-b", "com.culturedcode.ThingsMac", str(url)],
            check=False,
        )
        return True


class Things3App:
    """App wrapper for simple read-only API for Things 3."""

    FILE = "kanban.html"

    def open_api(self):
        """Delay opening the browser."""
        print(f"Using database 2: {self.database}")
        self.api.main()

    def __init__(self, database=None, debug_text=""):
        self.database = things3.Things3.resolve_database_path(database)
        self.api = things3_api.Things3API(database=self.database, debug_text=debug_text)
        self.bridge = AppBridge()
        self.api_thread: Thread | None = None
        self.window: Any | None = None

    def sigterm_handler(self, _signo, _stack_frame):
        """Make sure the server shuts down."""
        print("Sigterm...")
        if self.api.flask_context is not None:
            self.api.flask_context.shutdown()

    @staticmethod
    def kill_stale_api_processes():
        """Stop leftover API listeners before starting the app wrapper."""
        result = subprocess.run(
            ["lsof", "-nti:" + str(things3_api.Things3API.port)],
            capture_output=True,
            check=False,
            text=True,
        )
        for pid in result.stdout.split():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass

    def main(self, appstore=False):
        """Run the app."""
        # kill possible zombie processes; can't use psutil in py2app context
        self.kill_stale_api_processes()

        # Make sure the server shuts down
        signal.signal(signal.SIGTERM, self.sigterm_handler)

        print(f"Using database 1: {self.database}")

        self.window = webview.create_window(
            title="KanbanView",
            url=f"http://{things3_api.Things3API.host}:"
            + f"{things3_api.Things3API.port}/{self.FILE}",
            js_api=self.bridge,
            width=1280,
            height=650,
            min_size=(1280, 650),
            frameless=False,
        )

        if self.window is None:
            raise RuntimeError("Could not create the webview window.")

        if not appstore:
            self.window.events.closed += advertise
        self.window.events.closing += self.closing
        self.api_thread = Thread(target=self.open_api)

        try:
            self.api_thread.start()
            webview.start(self.closing, args=(self.window,))  # blocking
            if self.api.flask_context is not None:
                self.api.flask_context.shutdown()
            self.api_thread.join()
        except KeyboardInterrupt:
            print("Shutting down...")
            if self.api.flask_context is not None:
                self.api.flask_context.shutdown()
            if self.api_thread is not None:
                self.api_thread.join()
            sys.exit(0)

    def closing(self, _window=None):
        """Close the app"""
        if not _window and self.window is not None:
            self.window.destroy()
            # self.api.flask_context.shutdown()
            # self.api_thread.join()
        else:
            print(f"Registering close function for: {_window}")


def advertise():
    """Show a hint to buy the app"""
    text = (
        "Thank you for using KanbanView! "
        + "If you enjoy using it, please consider buying the app."
    )
    title = "KanbanView"
    url = "https://kanbanview.app"
    subprocess.run(
        [
            "osascript",
            "-e",
            (
                f'set dialog to (display dialog "{text}" '
                'buttons {"Buy", "Later"} default button 1 '
                f'giving up after 10 with title "{title}" '
                'with icon POSIX file "resources/icon.icns")'
            ),
            "-e",
            'if the button returned of the result is "Buy" then',
            "-e",
            f'do shell script "open {url}"',
            "-e",
            "end if",
        ],
        check=False,
    )


def main():
    """Main entry point for CLI installation"""
    Things3App().main()


if __name__ == "__main__":
    main()
