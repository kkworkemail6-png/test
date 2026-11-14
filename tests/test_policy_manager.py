import json

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core import policy_manager as pm

POLICIES = {"status": "success", "data": [{"policyName": "ProjectAdmin", "actions": ["ct:list"]}]}
URL = "https://app.scaleinn.in:8443/api/v1/orca/policies/my-policies"


def test_policies_response_is_stored_verbatim_next_to_the_token(http, make_client, logged_in):
    http.add(200, POLICIES)
    assert pm.refresh_policies(make_client(), "proj1234ab") == (True, None)
    call = http.calls[0]
    assert call["url"] == URL and call["params"] == {"projectId": "proj1234ab"}
    stored = json.loads(cfg.credentials_path().read_text())
    assert stored["policies"] == POLICIES
    assert stored["access_token"] and stored["project"]["id"] == "proj1234ab"  # nothing else lost
    assert pm.get_stored_policies() == POLICIES


def test_failed_fetch_removes_stale_policies_and_reports_why(http, make_client, logged_in):
    credentials.update_context(policies={"old": "from another project"})
    http.add(500, {"message": "boom"})
    ok, reason = pm.refresh_policies(make_client(), "proj1234ab")
    assert ok is False and reason
    assert pm.get_stored_policies() is None
    assert credentials.get_project()["id"] == "proj1234ab"  # the rest of the file is intact


def test_forbidden_is_not_raised(http, make_client, logged_in):
    http.add(403, {"message": "no"})
    assert pm.refresh_policies(make_client(), "proj1234ab")[0] is False


def test_refreshing_for_another_project_replaces_the_stored_policies(http, make_client, logged_in):
    http.add(200, POLICIES).add(200, {"data": []})
    client = make_client()
    pm.refresh_policies(client, "proj1234ab")
    pm.refresh_policies(client, "other")
    assert http.calls[1]["params"] == {"projectId": "other"}
    assert pm.get_stored_policies() == {"data": []}


def test_policies_are_not_logged_in_full(http, make_client, logged_in):
    from scaleinn.core.logger import setup_logging

    setup_logging()
    http.add(200, {"data": [{"policyName": "SENTINEL-POLICY-NAME"}]})
    pm.refresh_policies(make_client(), "proj1234ab")
    assert "SENTINEL-POLICY-NAME" not in cfg.log_path().read_text()
