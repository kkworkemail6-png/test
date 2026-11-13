"""Projects, organisations and policies APIs (auth/operations.py) and per-service URL routing."""

import pytest

from scaleinn.auth import operations as ops
from scaleinn.core import config as cfg
from scaleinn.core.exceptions import AuthenticationError, AuthorizationError, ValidationError

from conftest import TEST_TOKEN

BASE = "https://app.scaleinn.in:8443"


def test_list_projects_request(http, make_client, logged_in):
    http.add(200, {"data": []})
    assert ops.list_projects(make_client()) == {"data": []}
    call = http.calls[0]
    assert call["method"] == "GET" and call["url"] == BASE + "/api/v1/orca/projects/list"
    assert call["params"] == {"search": "", "size": 100, "sortDir": "DESC"}
    assert call["headers"]["Authorization"] == f"Bearer {TEST_TOKEN}"


def test_list_projects_custom_parameters(http, make_client, logged_in):
    http.add(200, [])
    ops.list_projects(make_client(), search=" prod ", size=10, sort_dir="asc")
    assert http.calls[0]["params"] == {"search": "prod", "size": 10, "sortDir": "ASC"}


def test_list_organizations_request(http, make_client, logged_in):
    http.add(200, [])
    ops.list_organizations(make_client())
    call = http.calls[0]
    assert call["url"] == BASE + "/api/v1/orca/organisation/list"
    assert call["params"] == {"size": 100, "search": ""}
    assert call["headers"]["Authorization"] == f"Bearer {TEST_TOKEN}"


def test_my_policies_request_with_and_without_project(http, make_client, logged_in):
    http.add(200, []).add(200, [])
    client = make_client()
    ops.get_my_policies(client, "exch4bt42y")
    ops.get_my_policies(client)
    assert http.calls[0]["url"] == BASE + "/api/v1/orca/policies/my-policies"
    assert http.calls[0]["params"] == {"projectId": "exch4bt42y"}
    assert http.calls[1]["params"] == {"projectId": ""}  # empty, as in the documented call


@pytest.mark.parametrize(
    "call",
    [
        lambda c: ops.list_projects(c, sort_dir="sideways"),
        lambda c: ops.list_projects(c, size=0),
        lambda c: ops.list_organizations(c, size=-1),
        lambda c: ops.list_organizations(c, search="a\x00b"),
    ],
)
def test_invalid_arguments_are_rejected_before_any_request(http, make_client, logged_in, call):
    with pytest.raises(ValidationError):
        call(make_client())
    assert http.calls == []


@pytest.mark.parametrize("status,error", [(401, AuthenticationError), (403, AuthorizationError)])
@pytest.mark.parametrize("call", [ops.list_projects, ops.list_organizations, ops.get_my_policies])
def test_auth_and_permission_errors(http, make_client, logged_in, status, error, call):
    http.add(status, {"message": "nope"})
    with pytest.raises(error):
        call(make_client())


# ----------------------------------------------------- per-service routing
def test_api_service_is_the_default_and_object_storage_has_its_own_url(http, make_client, logged_in):
    client = make_client()
    http.add(200, {}).add(200, {}).add(200, {})
    client.get("/a")                                  # default -> apiUrl
    client.get("/b", service="api")
    client.get("/c", service="object_storage")        # -> objectStorageUrl
    assert http.calls[0]["url"] == "https://app.scaleinn.in:8443/a"
    assert http.calls[1]["url"] == "https://app.scaleinn.in:8443/b"
    assert http.calls[2]["url"] == "https://app.scaleinn.in:8086/c"


def test_http_environment_is_used_when_protocol_is_http(http, make_client, logged_in):
    from scaleinn.core import env

    client = make_client(protocol="http")
    http.add(200, {}).add(200, {})
    client.get("/a")
    client.get("/b", service="object_storage")
    assert http.calls[0]["url"] == env.HTTP["apiUrl"] + "/a"
    assert http.calls[1]["url"] == env.HTTP["objectStorageUrl"] + "/b"


def test_unknown_service_is_a_configuration_error(http, make_client, logged_in):
    from scaleinn.core.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        make_client().get("/x", service="nope")
    assert http.calls == []


def test_401_retry_after_refresh_stays_on_the_same_service(http, make_client, logged_in):
    client = make_client(endpoints={"refresh": "/auth/refresh"})
    http.add(401).add(200, {"access_token": "fresh"}).add(200, {"ok": 1})
    assert client.get("/bucket", service="object_storage") == {"ok": 1}
    assert http.calls[0]["url"].startswith("https://app.scaleinn.in:8086/")
    assert http.calls[1]["url"].startswith("https://app.scaleinn.in:8443/")  # refresh -> api
    assert http.calls[2]["url"].startswith("https://app.scaleinn.in:8086/")  # retry -> same service


def test_connection_error_names_the_service_url(http, make_client, logged_in):
    import requests
    from scaleinn.core.exceptions import NetworkError

    http.add(exc=requests.exceptions.ConnectionError("down"))
    with pytest.raises(NetworkError) as info:
        make_client().get("/x", service="object_storage")
    assert ":8086" in info.value.message
