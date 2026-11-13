# Scaleinn CLI

Command-line interface for the **Scaleinn** cloud platform, architecturally inspired by AWS CLI v2
(one top-level `scaleinn` command, one sub-command group per service).

```bash
scaleinn --version
scaleinn configure
scaleinn object-storage list-buckets [--search TEXT] [--output json|table]
scaleinn ct list [--search TEXT] [--page N] [--size N] [--sort-by FIELD] [--sort-direction ASC|DESC] [--output json|table]
```

## Contents

1. [Project overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technology stack](#3-technology-stack)
4. [Directory structure](#4-directory-structure)
5. [Important files](#5-important-files)
6. [Installation from source](#6-installation-from-source)
7. [Authentication configuration](#7-authentication-configuration)
8. [Root authentication](#8-root-authentication)
9. [IAM authentication](#9-iam-authentication)
10. [Project selection](#10-project-selection)
11. [Token storage and management](#11-token-storage-and-management)
12. [Object Storage examples](#12-object-storage-examples)
13. [CT examples](#13-ct-examples)
14. [HTTP / HTTPS configuration](#14-http--https-configuration)
15. [Logging and debugging](#15-logging-and-debugging)
16. [Error handling](#16-error-handling)
17. [Running the tests](#17-running-the-tests)
18. [Building the Debian package](#18-building-the-debian-package)
19. [APT installation and uninstallation](#19-apt-installation-and-uninstallation)
20. [Adding a new resource module](#20-adding-a-new-resource-module)
21. [Command execution flow](#21-command-execution-flow)
22. [API contracts](#22-api-contracts)

---

## 1. Project overview

The CLI is a **lightweight API client**. It parses commands, manages login and the selected project,
builds requests, and displays responses. It never talks to Proxmox, MinIO or any other
infrastructure directly: every operation goes through the Scaleinn backend API, which is
responsible for authentication, authorization (project access), resource managers and audit logs.

Implemented now:

| Area | Status |
|------|--------|
| `configure` (root / IAM login, project selection) | Login is integrated with the real `POST /api/v1/orca/user/login` API. The accessible-projects API is integrated too; its response schema is unconfirmed, so if the response is not recognized the project ID is typed in. Token refresh is a **placeholder** (see [section 22](#22-api-contracts)). |
| `object-storage list-buckets` | Done, against the real `get-all-bucket` API (served from its own URL, port 8086). |
| `ct list` | Done, against the real `GET /api/v1/orca/compute/lxc/get-list-by-projectid` API (search, paging and sorting supported). |

## 2. Architecture

```text
                USER
                  |
                  v
             SCALEINN CLI
                  |
                  v
             AUTHENTICATION
                  |
                  v
       CONFIGURATION MANAGEMENT
                  |
          +-------+-------+
          |               |
          v               v
      API URL         PROJECT ID
          |               |
          +-------+-------+
                  |
                  v
          COMMON API CLIENT
                  |
                  v
          SCALEINN BACKEND API
                  |
                  v
       BACKEND REQUEST PROCESSING
                  |
          +-------+-------+
          |       |       |
          v       v       v
       Resource Audit  Other
       Manager  Logs   Services
          |
          v
       PROXMOX / MINIO / OTHER
       CLOUD INFRASTRUCTURE
```

Layering inside the CLI (each layer only depends on the ones below it):

```text
services/<name>/commands.py     parse arguments, call operations, render output
services/<name>/operations.py   build the request for each API, call session.client
core/session.py                 config + tokens + API client for this invocation
core/api_client.py              the ONLY place that performs HTTP
core/token_manager.py, config.py, credentials.py, project_manager.py
```

## 3. Technology stack

| Concern | Choice | Why |
|---------|--------|-----|
| Language | Python 3.9+ (Ubuntu 22.04+, Debian 12+) | |
| CLI framework | **Click** | See below. |
| HTTP | **requests** | See below. |
| Config / credentials | JSON files in `~/.scaleinn` | Required by the spec; trivial to inspect and edit. |
| Logging | `logging` with a redacting formatter | Secrets are masked in every line. |
| Tests | pytest | |
| Packaging | setuptools (`pyproject.toml`) + debhelper/pybuild | |

**Click vs Typer: Click.** Typer is a thin layer on top of Click that derives commands from type
hints. This project needs explicit command trees assembled from independent service modules
(`@click.group` per service, registered in one place), custom error handling and a custom
`--version` string. Click does all of that directly. Using it avoids an extra dependency, and
`python3-click` is a standard Debian/Ubuntu package, which keeps the `.deb` small and lets it rely on
system Python packages instead of bundling a virtualenv.

**requests vs HTTPX: requests.** The CLI performs one synchronous call per command, so async and
HTTP/2 add nothing. `requests` is ubiquitous, stable, has simple TLS/CA-bundle handling, and is
available as `python3-requests` on every target distribution.

## 4. Directory structure

```text
scaleinn-cli/
|-- README.md
|-- LICENSE
|-- pyproject.toml
|-- requirements.txt
|-- .gitignore
|
|-- src/scaleinn/
|   |-- __init__.py
|   |-- main.py                     console-script entry point
|   |-- cli.py                      root Click group, global options, error handling
|   |-- version.py                  __version__ (single source of truth)
|   |
|   |-- core/
|   |   |-- env.py                  backend URLs per protocol (https / http) + optional env values
|   |   |-- config.py               ~/.scaleinn/config.json load/update (atomic, 700/600)
|   |   |-- credentials.py          ~/.scaleinn/credentials.json (tokens only, 600)
|   |   |-- token_manager.py        token storage, expiry tracking, refresh
|   |   |-- authentication.py       interactive login flow (prompts, store tokens)
|   |   |-- project_manager.py      fetch / choose / save / read the selected project
|   |   |-- api_client.py           common HTTP client (GET/POST/PUT/PATCH/DELETE)
|   |   |-- session.py              per-invocation context passed to commands
|   |   |-- exceptions.py           error classes + exit codes
|   |   |-- logger.py               logging setup + secret redaction
|   |   |-- output.py               --output option and table/JSON rendering
|   |
|   |-- auth/                       account-level backend APIs
|   |   |-- operations.py           projects, organisations and my-policies APIs (one file)
|   |   |-- root_auth.py            root endpoint key + payload
|   |   |-- iam_auth.py             IAM endpoint key + payload
|   |   |-- login.py                dispatcher + login-response parsing
|   |   |-- refresh.py              token refresh
|   |
|   |-- commands/
|   |   |-- configure.py            `scaleinn configure`
|   |   |-- version.py              `scaleinn version`
|   |
|   |-- services/
|   |   |-- __init__.py             register_services(): the one place services are listed
|   |   |-- object_storage/{commands,operations,models}.py
|   |   |-- ct/{commands,operations,models}.py
|   |
|   |-- utils/                      file_utils, table_formatter, json_formatter, terminal
|
|-- tests/                          pytest suite (no network, no real credentials)
|-- packaging/debian/               control, rules, changelog, copyright, source/format
|-- scripts/                        build_deb.sh, install.sh, uninstall.sh
```

## 5. Important files

| File | Role |
|------|------|
| `cli.py` | Defines the `scaleinn` group, `--version`, `--debug`; sets up logging and the `Session`; converts `ScaleinnError` into a clean message plus exit code. |
| `core/api_client.py` | All HTTP: base URL from config, bearer header, query/JSON, error mapping, timeouts, TLS settings, sanitized logging. |
| `core/config.py` | Reads and updates `config.json`; `update_config(**changes)` rewrites only the given keys and preserves the rest. |
| `core/credentials.py` | Persists only `access_token`, `refresh_token`, `token_type`, `expires_at`. A password cannot be written through it. |
| `core/token_manager.py` | Expiry check, proactive refresh, refresh-and-retry support. |
| `core/project_manager.py` | The only code that knows how the selected project is stored. Services use `session.project_id`. |
| `core/session.py` | Lazily builds config, token manager and API client for one command run. |
| `services/*/operations.py` | **One file per service holding every API operation.** Add new operations here, not in new files. |
| `services/*/commands.py` | Click group + commands for the service; thin wrappers over `operations.py`. |
| `services/*/models.py` | Service-specific validation / data structures. |
| `core/env.py` | Backend base URLs (`apiUrl`, `objectStorageUrl`), one block for https and one for http, plus `backupOptionValue`. |
| `auth/operations.py` | The projects, organisations and my-policies APIs. |
| `auth/*_auth.py`, `login.py`, `refresh.py` | The only files that contain login/refresh payload details. |

## 6. Installation from source

```bash
git clone <your repository> scaleinn-cli && cd scaleinn-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
scaleinn --version
```

## 7. Authentication configuration

```bash
scaleinn configure
```

```text
Welcome to Scaleinn CLI

Select authentication type:

1. Root User
2. IAM User

Enter your choice: 1
Username: root
Password: ********

Authenticating with Scaleinn...

Authentication successful!

Fetching accessible projects...

+---+--------------+--------+------------+
| # | Project Name | Status | Project ID |
+---+--------------+--------+------------+
| 1 | Production   | Active | exch4bt42y |
| 2 | Development  | Active | dev00000aa |
+---+--------------+--------+------------+

Select project [1-2]: 1

Project selected successfully!
Selected project: Production
Project ID: exch4bt42y

Scaleinn CLI configuration completed.
```

Options of `scaleinn configure`:

| Option | Purpose |
|--------|---------|
| `--api-url URL` | Backend URL (`https://...` or `http://...`). Saved to `config.json`. |
| `--verify-ssl / --no-verify-ssl` | Enable/disable TLS certificate verification (disable only in controlled dev/test environments). |
| `--ca-bundle PATH` | Custom CA certificate bundle. |
| `--project-only` | Change only the selected project using the current login (no password prompt). |
| `--with-token` | **Interim**: supply an existing bearer token instead of a password (hidden prompt) while the login API contract is pending. |

`config.json` (non-secret, mode 600 in a 700 directory):

```json
{
    "protocol": "https",
    "api_url": null,
    "object_storage_url": null,
    "auth_type": "root",
    "project_id": "exch4bt42y",
    "project_name": "Production",
    "default_output": "table",
    "verify_ssl": true
}
```

`protocol` (`https` or `http`) selects which block of `core/env.py` supplies the backend URLs.
`api_url` and `object_storage_url` are optional overrides; `null` means "use the environment value",
so editing `env.py` takes effect without touching any config file.

Optional keys: `ca_bundle` (path), `timeout` (read timeout in seconds, default 30) and `endpoints`
(login-path overrides and the future refresh path; see [section 22](#22-api-contracts)).

## 8. Root authentication

Choose **1. Root User** and enter *Username* and *Password*. The password is read with a hidden
prompt, sent once to the root-login endpoint, and discarded. Only the returned tokens are stored.

## 9. IAM authentication

Choose **2. IAM User** and enter the *Login ID* (the registered e-mail address) and *Password*. The
flow is identical to root login but uses the IAM-login endpoint and payload.

Both login types are implemented in `auth/` and use the same backend API:

```text
POST {api_url}/api/v1/orca/user/login
{"usernameOrEmail": "<username or login e-mail>", "password": "<password>"}
```

The response is searched for the access token (`access_token`, `accessToken` or `token`, also inside
a `data` envelope), an optional refresh token and an optional expiry (`expires_in` / `expires_at`).
If the backend later needs an explicit root/IAM discriminator, change `auth/root_auth.py` /
`auth/iam_auth.py` (the only places that know the payload).

## 10. Project selection

Project selection is centralized in `core/project_manager.py`:

* `scaleinn configure` fetches the projects the authenticated user can access, shows them in a table
  and stores the chosen **project ID and name** in `config.json`.
* Run `scaleinn configure --project-only` at any time to switch projects without logging in again.
* Services never read the stored value themselves; they use `session.project_id`.
* The stored project ID is a convenience, **not an authorization**. The backend validates access on
  every request, and a 403 is reported as an access-denied error.
* The list comes from `GET /api/v1/orca/projects/list?search=&size=100&sortDir=DESC` (see
  `auth/operations.py`). Its response schema is unconfirmed: the CLI accepts a list of records, also
  inside a `data` / `content` envelope. If the response is not recognized, `configure` says so and asks
  for the project ID/name manually (HTTP errors such as 401/403 are still reported as errors).

## 11. Token storage and management

* `~/.scaleinn` is created with mode **700**; `credentials.json` and `config.json` with mode **600**.
* Files are written **atomically** (temp file in the same directory, fsync, `os.replace`).
* `credentials.json` contains only `access_token`, `refresh_token` (if provided), `token_type` and
  `expires_at` (ISO-8601 UTC, derived from `expires_in`/`expires_at` when the backend sends them).
* Passwords are never stored. Tokens and passwords are never printed and are masked in logs.
* **Expiry:** a token whose expiry has passed is refreshed before the request when a refresh endpoint
  is configured; otherwise the CLI asks you to run `scaleinn configure`.
* **HTTP 401:** the request is retried **once** after a successful refresh (safe, because a 401 means
  the backend did not process the request); otherwise you are asked to sign in again.
* No other automatic retries are performed, so create/delete operations can never be duplicated.

## 12. Object Storage examples

```bash
scaleinn object-storage --help
scaleinn object-storage list-buckets
scaleinn object-storage list-buckets --search my-bucket
scaleinn object-storage list-buckets --output json
scaleinn --debug object-storage list-buckets
```

This calls:

```text
GET {api_url}/api/v1/object-storage/bucket/get-all-bucket?projectId=<selected project>&search=<text>
Authorization: Bearer <access token>
```

The response schema has not been confirmed, so no field names are assumed. `--output json` prints
the backend response unchanged. `--output table` (the default) renders a table when the response
contains one unambiguous list of records and otherwise falls back to JSON with a note on stderr.
Once the schema is confirmed, pass explicit columns to `render(...)` in
`services/object_storage/commands.py`.

## 13. CT examples

```bash
scaleinn ct --help
scaleinn ct list
scaleinn ct list --search web --page 0 --size 50
scaleinn ct list --sort-by createdDate --sort-direction ASC
scaleinn ct list --output json
```

This calls:

```text
GET {api_url}/api/v1/orca/compute/lxc/get-list-by-projectid
    ?projectId=<selected project>&sortBy=createdDate&sortDirection=DESC&page=0&size=100&search=
Authorization: Bearer <access token>
```

The values shown are the defaults of `--sort-by`, `--sort-direction`, `--page`, `--size` and
`--search`. The response schema has not been confirmed, so `--output json` prints the backend
response unchanged, and the table view works on any single list of records (also inside a `data`
envelope such as `{"data": {"content": [...]}}`), falling back to JSON otherwise.

## 14. HTTP / HTTPS configuration

Backend URLs live in `src/scaleinn/core/env.py`, in two separate blocks, like an `environment.ts`:

| Key | `https` block | `http` block |
|-----|---------------|--------------|
| `apiUrl` (login, projects, organisations, policies, CT and every other module) | `https://app.scaleinn.in:8443` | `http://192.168.192.234:8080` * |
| `objectStorageUrl` (Object Storage only) | `https://app.scaleinn.in:8086` | `http://192.168.192.234:8080` * |
| `backupOptionValue` (optional, for later APIs) | `backup-store` | `backup-store` |

\* placeholder: the real HTTP host/ports were not supplied; edit `env.py`.

```bash
scaleinn configure --protocol https                  # default: use the https block
scaleinn configure --protocol http --project-only    # use the http block (resets URL overrides)
scaleinn configure --api-url https://other.example:8443 --project-only         # override one URL
scaleinn configure --object-storage-url https://other.example:8086 --project-only
scaleinn configure --ca-bundle /etc/ssl/my-company-ca.pem --project-only
scaleinn configure --no-verify-ssl --project-only     # development/testing only
```

* `protocol` in `config.json` picks the block; `api_url` / `object_storage_url` override single URLs.
* Operations choose their service through the API client: `client.get(path)` uses `apiUrl`, and
  `client.get(path, service="object_storage")` uses `objectStorageUrl`.
* With **HTTP** (any service URL), a warning is printed (to stderr, once per command) because bearer
  tokens are sent without TLS. Use HTTPS in production.
* With `--no-verify-ssl`, a warning is printed as well.
* TLS failures produce a hint about `--ca-bundle`.

To add a service with its own URL: add its key to both blocks of `env.py` and one line to `SERVICES`
in `core/config.py`, then pass `service="<name>"` from its `operations.py`.

## 15. Logging and debugging

* Log file: `~/.scaleinn/logs/scaleinn.log` (mode 600, rotated at 1 MB, 3 backups), INFO level.
* `scaleinn --debug <command>` also prints DEBUG logs to stderr.

```text
2026-11-12 10:00:01 INFO  CLI initialized
2026-11-12 10:00:01 INFO  Initializing Object Storage module
2026-11-12 10:00:01 INFO  Loading configuration
2026-11-12 10:00:01 INFO  Authentication loaded
2026-11-12 10:00:01 INFO  Project selected: exch4bt42y
2026-11-12 10:00:01 INFO  Calling get-all-bucket API
2026-11-12 10:00:01 INFO  GET /api/v1/object-storage/bucket/get-all-bucket
2026-11-12 10:00:02 INFO  Backend response received: HTTP 200
2026-11-12 10:00:02 INFO  Command completed
```

Redaction: request bodies, headers and response bodies are never logged. In addition,
`core/logger.py` masks `Bearer ...`, `password`/`token`/`secret` style fields and any token/password
registered at runtime, in every log line and traceback.

## 16. Error handling

Errors are shown as a short message with an optional hint (no tracebacks) and use stable exit codes:

| Exit code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid usage or input (e.g. unknown option, empty project list) |
| 3 | Authentication failed / session expired / HTTP 401 / not logged in with `--project-only` |
| 4 | Access denied (HTTP 403) |
| 5 | Network problem: connection failure, TLS failure, timeout |
| 6 | Local configuration problem: not logged in, no project selected, endpoint not configured |
| 7 | Backend returned another error status (4xx/5xx) or an unusable response |

## 17. Running the tests

```bash
pip install -e ".[dev]"
pytest
```

Tests never use the network or real credentials: `requests.Session.request` is replaced by a fake,
and `SCALEINN_CONFIG_DIR` points to a temporary directory. They cover startup/help/version, root and
IAM login, the `configure` flow, project selection, config and token storage (including file
permissions), the API client (HTTP and HTTPS, 401 with/without refresh, 403, 5xx, timeouts and
connection/TLS failures, no-retry guarantees), Object Storage listing, CT registration, output
formatting and log redaction.

## 18. Building the Debian package

```bash
sudo apt install build-essential debhelper dh-python pybuild-plugin-pyproject \
     python3-all python3-setuptools python3-click python3-requests python3-pytest
./scripts/build_deb.sh
# -> dist/scaleinn-cli_1.0.0_amd64.deb
```

`SKIP_TESTS=1 ./scripts/build_deb.sh` skips the test run during the build. The script verifies that
`src/scaleinn/version.py` and `packaging/debian/changelog` carry the same version. To release a new
version, update both.

The package is a standard debhelper/pybuild package: it depends on the system packages
`python3-click` and `python3-requests` (resolved automatically by `apt`), installs the code into the
system Python and provides `/usr/bin/scaleinn`. No virtualenv is needed.

The code is pure Python. `Architecture: amd64` in `packaging/debian/control` is used so the file is
named `scaleinn-cli_1.0.0_amd64.deb` as requested; use `Architecture: all` for a single package that
installs on every architecture.

## 19. APT installation and uninstallation

```bash
sudo apt install ./dist/scaleinn-cli_1.0.0_amd64.deb      # or ./scripts/install.sh
scaleinn --version
scaleinn configure

sudo apt remove scaleinn-cli                              # or ./scripts/uninstall.sh
```

Removing or purging the package never deletes `~/.scaleinn`, so configuration, credentials and logs
survive reinstalls and upgrades. Delete that directory yourself to sign out completely.

## 20. Adding a new resource module

1. Create `src/scaleinn/services/<name>/` with `__init__.py`, `commands.py`, `operations.py`, `models.py`.
2. In `operations.py` add plain functions `def list_things(session, ...)` that build the request and
   call `session.client.get/post/...` and use `session.project_id` when the API needs a project.
3. In `commands.py` define a Click group (e.g. `@click.group("vpc")`) and commands that call the
   operations and `render(...)` the result. Add `@output_option` for `--output`.
4. Register the group in `services/__init__.py` (`root.add_command(vpc)`).
5. Add `tests/services/test_<name>.py`.

All further APIs of a service go into that service's `operations.py`. Do not create a file per API,
and do not use `requests` outside `core/api_client.py`.

## 21. Command execution flow

`scaleinn object-storage list-buckets --search my-bucket`:

1. `main.py` starts the Click root group in `cli.py`.
2. The group sets up logging (`~/.scaleinn/logs`), creates a lazy `Session`, logs "CLI initialized".
3. Click dispatches to `object-storage` -> `list-buckets` (`services/object_storage/commands.py`).
4. The command calls `operations.list_buckets(session, "my-bucket")`.
5. The operation reads `session.project_id` (config loaded and validated on first use; error if no
   project is selected) and builds `{projectId, search}`.
6. `session.client` (the `ApiClient`) loads the access token, refreshes it first if its known expiry
   has passed, attaches `Authorization: Bearer ...`, and sends the GET using the configured URL and
   TLS settings.
7. The client maps the result: 401 -> re-authenticate (after one refresh attempt if possible), 403 ->
   access denied, other errors -> `APIError`, timeouts/connection errors -> `NetworkError`.
8. On success, the parsed JSON goes to `render(...)`, which prints JSON or a table.
9. Any `ScaleinnError` is caught in `cli.py`, shown with its hint and converted to its exit code.

## 22. API contracts

Integrated (all on `apiUrl` unless noted):

| API | Where |
|-----|-------|
| `POST /api/v1/orca/user/login` | `auth/login.py`, `auth/root_auth.py`, `auth/iam_auth.py` |
| `GET /api/v1/orca/projects/list?search=&size=100&sortDir=DESC` | `auth/operations.py` (`list_projects`), used by `configure` |
| `GET /api/v1/orca/organisation/list?size=100&search=` | `auth/operations.py` (`list_organizations`) |
| `GET /api/v1/orca/policies/my-policies?projectId=` | `auth/operations.py` (`get_my_policies`) |
| `GET /api/v1/orca/compute/lxc/get-list-by-projectid?...` | `services/ct/operations.py` |
| `GET /api/v1/object-storage/bucket/get-all-bucket?...` (on `objectStorageUrl`) | `services/object_storage/operations.py` |

The organisation and policies APIs have no CLI command yet; they are available as functions.

Still **not invented**; each is isolated in one place:

| Item | Where | How to provide it |
|------|-------|-------------------|
| Token refresh | `auth/refresh.py` | Set `endpoints.refresh` (and confirm the payload). Without it, expired sessions require `scaleinn configure`. |
| Login / projects response formats | `auth/login.py` (`parse_token_response`), `core/project_manager.py` (`normalize_project`) | Currently tolerant of common key names; adjust if the real responses differ. |
| Root vs IAM discriminator, if any | `auth/root_auth.py`, `auth/iam_auth.py` | Both use the shared login API today. |
| HTTP environment URLs | `core/env.py` | Replace the placeholder `HTTP` block. |
| CT / bucket list response schemas | `services/*/commands.py` | Pass explicit columns to `render`. |

Optional path overrides in `config.json`:

```json
{
    "endpoints": {
        "root_login": "/api/v1/orca/user/login",
        "iam_login": "/api/v1/orca/user/login",
        "refresh": "/api/v1/..."
    }
}
```

`scaleinn configure --with-token` remains available to store an existing bearer token instead of
logging in with a password.
