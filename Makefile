-include appstore/Makefile

.PHONY: help deps-install install uninstall run open run-api open-api kill-api run-app cli test app doc clean auto-style lint code-style code-lint type-check css-lint js-lint html-lint code-count feedback pre-commit png jpg upload db-to-things db-from-things

.DEFAULT_GOAL := help

MAIN=things3_kanban
APP=things3_app
SERVER=things3_api
CLI=things3_cli
SRC_CORE=things3
SRC_TEST=tests
DEST=kanban-static.html
SERVER_PORT=15000
DEST_SRV=http://localhost:$(SERVER_PORT)/kanban.html

SYSTEM_PYTHON=python3
UV=uv
UV_CACHE_DIR=$(CURDIR)/.uv-cache
UV_DATA_DIR=$(CURDIR)/.uv-data
UV_PROJECT_ENVIRONMENT=$(CURDIR)/.venv
RUNTIME_HOME=$(CURDIR)/.make-home
UV_ENV=UV_CACHE_DIR=$(UV_CACHE_DIR) XDG_DATA_HOME=$(UV_DATA_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) HOME=$(RUNTIME_HOME)
UV_RUN=$(UV_ENV) $(UV) run
UV_SYNC=$(UV_ENV) $(UV) sync
PYTHON=$(UV_RUN) python
DEFAULT_THINGSDB=$(shell sh -c 'set -- "$$HOME"/Library/Group\ Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things\ Database.thingsdatabase/main.sqlite; if [ -e "$$1" ]; then printf "%s\n" "$$1"; elif [ -e resources/demo.sqlite3 ]; then printf "%s\n" resources/demo.sqlite3; fi')
RUN_ENV=THINGSDB="$${THINGSDB:-$(DEFAULT_THINGSDB)}"

define ensure_runtime_home
	@mkdir -p $(RUNTIME_HOME)
endef

help:
	@echo "CLI, API and Web Service for Things3."
	@echo ""
	@echo "Configuration:"
	@echo " * Static Kanban : $(DEST)"
	@echo " * Dynamic Kanban: $(DEST_SRV)"
	@echo ""
	@echo "Environment:"
	@echo " * THINGSDB    - Path to database"
	@echo " * TAG_WAITING - Tag for tasks you are waiting for"
	@echo " * TAG_MIT     - Tag for most important task"
	@echo ""
	@echo "Available commands:"
	@echo " * deps-install - Create/update the uv environment (.venv)."
	@echo " * run          - Render the static Kanban HTML."
	@echo " * run-api      - Start the dynamic web service."
	@echo " * run-app      - Start the macOS app wrapper."
	@echo " * cli          - Run the CLI (use 'args=' for arguments)."
	@echo " * test         - Run the unit test suite with coverage."
	@echo " * code-style   - Check formatting with Ruff."
	@echo " * code-lint    - Run Ruff lint checks."
	@echo " * type-check   - Run ty type checking."
	@echo " * lint         - Run formatting, linting, and type checking."
	@echo " * auto-style   - Apply Ruff formatting and fixes."
	@echo " * app          - Build the macOS app bundle via py2app."
	@echo " * clean        - Remove generated artifacts."
	@echo " * feedback     - Open the issue tracker."

deps-install:
	$(ensure_runtime_home)
	@$(UV_SYNC) --group dev

install: deps-install
	@echo "Environment ready. Use '$(UV_RUN) things-cli' or 'make cli args=...'."

uninstall:
	@rm -rf $(UV_PROJECT_ENVIRONMENT) $(UV_CACHE_DIR) $(UV_DATA_DIR)

run:
	$(ensure_runtime_home)
	@$(RUN_ENV) $(PYTHON) -m $(SRC_CORE).$(MAIN)
	@echo "File created: $(DEST)"

open:
	@open $(DEST)

run-api:
	$(ensure_runtime_home)
	@$(PYTHON) -m $(SRC_CORE).$(SERVER)

open-api:
	@open $(DEST_SRV)

kill-api:
	@pids=$$(lsof -nti:$(SERVER_PORT)); \
	if [ -n "$$pids" ]; then \
		kill $$pids >/dev/null 2>&1 || echo "Warning: could not stop PID(s): $$pids"; \
	fi

run-app:
	$(ensure_runtime_home)
	@$(PYTHON) -m $(SRC_CORE).$(APP)

cli:
	$(ensure_runtime_home)
	@$(PYTHON) -m $(SRC_CORE).$(CLI) $(args)

test:
	$(ensure_runtime_home)
	@$(PYTHON) -m coverage erase
	@$(PYTHON) -m coverage run -a -m $(SRC_TEST).test_things3
	@$(PYTHON) -m coverage run -a -m $(SRC_TEST).test_things3_api
	@$(PYTHON) -m coverage run -a -m $(SRC_TEST).test_things3_cli
	@$(PYTHON) -m coverage run -a -m $(SRC_TEST).test_things3_kanban
	@$(PYTHON) -m coverage report

app: clean
	$(ensure_runtime_home)
	@$(UV_ENV) ./scripts/build_app.sh

doc:
	@$(PYTHON) -m pydoc $(SRC_CORE).things3

clean:
	@rm -f $(DEST)
	@find . -name \*.pyc -delete
	@find . -name __pycache__ -delete
	@rm -rf .make-home
	@rm -rf .mypy_cache htmlcov build dist *.egg-info .eggs
	@rm -f .coverage

auto-style:
	@$(UV_RUN) ruff format .
	@$(UV_RUN) ruff check --fix .

lint: code-style code-lint type-check

code-style:
	@$(UV_RUN) ruff format --check .

code-lint:
	@$(UV_RUN) ruff check .

type-check:
	@$(UV_RUN) ty check $(SRC_CORE)

css-lint:
	@type csslint >/dev/null 2>&1 || (echo "Run 'npm install -g csslint' first." >&2 ; exit 1)
	@csslint --format=compact resources/kanban.css

js-lint:
	@type standard >/dev/null 2>&1 || (echo "Run 'npm install -g standard' first." >&2 ; exit 1)
	@standard resources/*.js

html-lint:
	@type tidy >/dev/null 2>&1 || (echo "Run 'brew install tidy' first." >&2 ; exit 1)
	@tidy -qe --mute --mute MISSING_ENDTAG_BEFORE,DISCARDING_UNEXPECTED,TRIM_EMPTY_ELEMENT resources/*.html

code-count:
	@type cloc >/dev/null 2>&1 || (echo "Run 'brew install cloc' first." >&2 ; exit 1)
	@cloc $(SRC_CORE)

feedback:
	@open https://github.com/AlexanderWillner/KanbanView/issues

pre-commit:
	@make clean kill-api
	@make deps-install auto-style lint
	@THINGSDB=resources/demo.sqlite3 make run
	@THINGSDB=resources/demo.sqlite3 make test

png:
	@type optipng >/dev/null 2>&1 || (echo "Run 'brew install optipng' first." >&2 ; exit 1)
	@echo "Optimizing PNG..."
	@find . -iname "*.png" -exec optipng -silent {} \;

jpg:
	@type jpegoptim >/dev/null 2>&1 || (echo "Run 'brew install jpegoptim' first." >&2 ; exit 1)
	@echo "Optimizing JPG..."
	@find . -iname "*.jpg" -exec jpegoptim -q {} \;

upload: clean
	@$(UV_RUN) python -m build
	@$(UV_RUN) python -m twine upload dist/things3*

db-to-things:
	@cp resources/demo.sqlite3 ~/Library/Group\ Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things\ Database.thingsdatabase/main.sqlite

db-from-things:
	@cp ~/Library/Group\ Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things\ Database.thingsdatabase/main.sqlite resources/demo.sqlite3
