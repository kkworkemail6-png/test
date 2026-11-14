import json

import pytest
from click.testing import CliRunner

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core import organisation_manager as om
from scaleinn.core.exceptions import APIError, AuthorizationError, ResponseFormatError

ORGS = [om.Organisation("org-1", "Acme"), om.Organisation("org-2", "Globex")]


def test_parse_organisations_from_list_envelope_and_spelling_variants():
    raw = [{"organisationId": "o1", "organisationName": "One"}, {"id": 2, "name": "Two"},
           {"organizationId": "o3", "organizationName": "Three"}]
    expected = [om.Organisation("o1", "One"), om.Organisation("2", "Two"), om.Organisation("o3", "Three")]
    assert om.parse_organisations(raw) == expected
    assert om.parse_organisations({"data": {"content": raw}}) == expected


def test_name_falls_back_to_the_id():
    assert om.parse_organisations([{"id": "x"}]) == [om.Organisation("x", "x")]


def test_unusable_items_are_skipped_and_unknown_shape_is_a_format_error():
    assert om.parse_organisations([{"nothing": 1}, "x"]) == []
    with pytest.raises(ResponseFormatError) as info:
        om.parse_organisations({"unexpected": "shape"})
    assert isinstance(info.value, APIError)


def test_fetch_organisations_calls_documented_endpoint_with_bearer_token(http, make_client, logged_in):
    http.add(200, [{"organisationId": "o9", "organisationName": "Nine"}])
    assert om.fetch_organisations(make_client()) == [om.Organisation("o9", "Nine")]
    call = http.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://app.scaleinn.in:8443/api/v1/orca/organisation/list"
    assert call["params"] == {"size": 100, "search": ""}
    assert call["headers"]["Authorization"].startswith("Bearer ")


def test_fetch_organisations_surfaces_http_errors(http, make_client, logged_in):
    http.add(403, {"message": "no"})
    with pytest.raises(AuthorizationError):
        om.fetch_organisations(make_client())


def test_render_lists_every_organisation():
    table = om.render_organisations(ORGS)
    for org in ORGS:
        assert org.name in table and org.id in table


def test_choose_organisation_selects_by_number_and_rejects_out_of_range():
    import click

    @click.command()
    def cmd():
        click.echo(om.choose_organisation(ORGS).name)

    result = CliRunner().invoke(cmd, input="7\n2\n")
    assert "Globex" in result.output and "not in the range" in result.output


def test_single_organisation_can_be_accepted_with_enter():
    import click

    @click.command()
    def cmd():
        click.echo(om.choose_organisation(ORGS[:1]).id)

    assert "org-1" in CliRunner().invoke(cmd, input="\n").output


def test_manual_entry_and_skip():
    import click

    @click.command()
    def cmd():
        click.echo(repr(om.prompt_organisation_manually()))

    assert "org-x" in CliRunner().invoke(cmd, input="org-x\nXeno\n").output
    assert "None" in CliRunner().invoke(cmd, input="\n").output


def test_save_selected_organisation_goes_to_credentials_and_none_clears_it(logged_in):
    om.save_selected_organisation(ORGS[1])
    assert json.loads(cfg.credentials_path().read_text())["organisation"] == {"id": "org-2", "name": "Globex"}
    assert credentials.get_organisation()["id"] == "org-2"
    om.save_selected_organisation(None)
    assert credentials.get_organisation() is None
