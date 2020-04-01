#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""KanbanView Server for KanbanView for Things 3."""

from __future__ import print_function

__author__ = "Alexander Willner"
__copyright__ = "Copyright 2020 Alexander Willner"
__credits__ = ["Alexander Willner"]
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Alexander Willner"
__email__ = "alex@willner.ws"
__status__ = "Development"

from io import StringIO
from os.path import dirname, realpath
from os import system
from signal import signal, SIGINT
import sys
import webbrowser
from wsgiref.simple_server import make_server
import things3_to_kanban

FILE = 'kanban.html'
PATH = '/../resources/'
PORT = 8080
HTTPD = None


def handler(signal_received, frame):
    """Handle any cleanup here."""
    print("Shutting down...: " + str(signal_received) + " / " + str(frame))
    HTTPD.server_close()
    sys.exit(0)


def kanban_server(environ, start_response):
    """Serving generated HTML tables via AJAX."""

    if environ['REQUEST_METHOD'] == 'POST':
        start_response('200 OK', [('Content-type', 'text/plain')])
        output = StringIO()
        things3_to_kanban.write_html_columns(output)
        return [output.getvalue().encode()]

    filename = environ['PATH_INFO'][1:]
    filename = dirname(realpath(__file__)) + PATH + filename
    response_body = open(filename, 'rb').read()
    start_response('200 OK', [('Content-Length', str(len(response_body)))])
    return [response_body]


if __name__ == "__main__":
    signal(SIGINT, handler)
    # kill possible zombie processes; can't use psutil in py2app context
    system('lsof -nti:' + str(PORT) + ' | xargs kill -9 ; sleep 1')

    HTTPD = make_server("", PORT, kanban_server)
    webbrowser.open('http://localhost:%s/%s' % (PORT, FILE))
    HTTPD.serve_forever()