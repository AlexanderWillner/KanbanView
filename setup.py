"""Packaging configuration for py2app builds and Python distribution metadata."""

import os
from pathlib import Path

from setuptools import find_packages, setup


def package_files(directory):
    """Automatically add data resources."""
    paths = []
    for path, _directories, filenames in os.walk(directory):
        for filename in filenames:
            paths.append((directory, [os.path.join(path, filename)]))
    return paths


APP = ["bin/things-app"]
APP_NAME = "KanbanView"
AUTHOR = "Alexander Willner"
AUTHOR_MAIL = "alex@willner.ws"
DESCRIPTION = "CLI, API, web service, and Kanban app for Things 3."
URL = "https://kanbanview.app"
VERSION = "3.0.0"
DATA_FILES = package_files("resources")
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/icon.icns",
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleGetInfoString": APP_NAME,
        "CFBundleIdentifier": "ws.willner.kanbanview",
        "CFBundleVersion": VERSION,
        "LSApplicationCategoryType": "public.app-category.productivity",
        "LSMinimumSystemVersion": "11",
        "NSHumanReadableCopyright": "Copyright 2023 " + AUTHOR,
    },
    "optimize": "2",
}

LONG_DESCRIPTION = Path("README.md").read_text(encoding="utf-8")

setup(
    app=APP,
    author=AUTHOR,
    author_email=AUTHOR_MAIL,
    name="things3-api",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url=URL,
    packages=find_packages(exclude=("tests", "tests.*")),
    classifiers=[
        "Development Status :: 5 - Production",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Environment :: Console",
        "Framework :: Flask",
        "Natural Language :: English",
    ],
    python_requires=">=3.11",
    version=VERSION,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    entry_points={
        "console_scripts": [
            "things-cli = things3.things3_cli:main",
            "things-api = things3.things3_api:main",
            "things-kanban = things3.things3_app:main",
        ]
    },
)
