@echo off

ECHO.
ECHO [INFO] Setting up environment variables for local testing...
set DB_HOST=localhost
set DB_USER=user
set DB_PASSWORD=password
set DB_PORT=5432
set DB_NAME=mydatabase

ECHO [INFO] Activating virtual environment and running pytest...
ECHO.

call .venv\Scripts\activate && pytest -v

ECHO.
ECHO [INFO] Cleaning up environment variables...
set DB_HOST=
set DB_USER=
set DB_PASSWORD=
set DB_PORT=
set DB_NAME=

ECHO [INFO] Done.
