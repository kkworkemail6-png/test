"""Every service and sub-service: registration, help text, extra category layer, file layout."""

import importlib
import re

import click
import pytest
from click.testing import CliRunner

from scaleinn.cli import cli
from scaleinn.core.command_groups import OrderedGroup, SectionedGroup

runner = CliRunner()

# Root --help sections, in order.
SECTIONS = {
    "General": ["configure", "version"],
    "Compute": ["ice", "ct"],
    "Network": ["network", "vpc", "shared-vpc", "ipam", "router", "security-group", "reserved-ip", "cloud-dns"],
    "Storage": ["object-storage", "block-storage", "network-storage", "additional-disks", "snapshot", "os-disks"],
    "Images": ["images", "marketplace-images", "project-images"],
    "Managed Services": ["managed-services", "database", "docker", "load-balancer", "waf", "vps", "alert-manager"],
}

# category -> its services, in listing order
CATEGORIES = {
    "network": ["vpc", "shared-vpc", "ipam", "router", "security-group", "reserved-ip", "cloud-dns"],
    "block-storage": ["network-storage", "additional-disks", "snapshot", "os-disks"],
    "images": ["marketplace-images", "project-images"],
    "managed-services": ["database", "docker", "load-balancer", "waf", "vps", "alert-manager"],
}

# the new, still empty services (ct and object-storage already have commands)
SKELETONS = ["ice"] + [sub for subs in CATEGORIES.values() for sub in subs]
ALL_SERVICES = SKELETONS + list(CATEGORIES) + ["ct", "object-storage"]


def pkg_of(category: str | None, name: str) -> str:
    leaf = name.replace("-", "_")
    return f"scaleinn.services.{category.replace('-', '_')}.{leaf}" if category else f"scaleinn.services.{leaf}"


def help_of(*args: str) -> str:
    result = runner.invoke(cli, [*args, "--help"], prog_name="scaleinn")  # as main.py does
    assert result.exit_code == 0, result.output
    return result.output


# ------------------------------------------------------------- root help
def test_root_help_lists_every_service_under_its_section_in_order():
    output = help_of()
    positions = []
    for title, names in SECTIONS.items():
        match = re.search(rf"^{re.escape(title)}:$", output, re.MULTILINE)
        assert match, f"section {title!r} missing"
        positions.append(match.start())
        block = output[match.end():].split("\n\n")[0]
        listed = [line.split()[0] for line in block.splitlines() if line.startswith("  ") and line[2] != " "]
        assert listed == names, title
    assert positions == sorted(positions)  # sections appear in the documented order


def test_root_help_has_no_unsectioned_commands():
    """A new service that is not added to a section would show up under a bare 'Commands:'."""
    assert not re.search(r"^Commands:$", help_of(), re.MULTILINE)


def test_root_help_shows_each_services_info():
    output = help_of()
    for text in ("Manage ICE virtual machines (VM).", "Manage Cloud DNS.", "Manage Database as a Service (DBaaS).",
                 "Manage Web Application Firewalls (WAF).", "Manage CTs (Linux Containers).",
                 "Manage Object Storage buckets."):
        assert text in output


def test_every_root_command_is_in_a_section():
    sectioned = {name for names in SECTIONS.values() for name in names}
    assert set(cli.commands) == sectioned


# --------------------------------------------------- every service's help
@pytest.mark.parametrize("name", ALL_SERVICES)
def test_each_service_has_a_top_level_help_command(name):
    output = help_of(name)
    assert f"Usage: scaleinn {name} " in output
    assert cli.commands[name].help and cli.commands[name].help in output.replace("\n  ", " ")


@pytest.mark.parametrize("name", SKELETONS)
def test_skeleton_services_say_that_no_commands_exist_yet(name):
    assert "No API commands are available yet" in help_of(name)


@pytest.mark.parametrize("name", SKELETONS)
def test_unknown_subcommand_of_a_skeleton_is_a_usage_error(name):
    result = runner.invoke(cli, [name, "list"])
    assert result.exit_code == 2 and "No such command 'list'" in result.output


# ------------------------------------------------- the extra category layer
@pytest.mark.parametrize("category,services", CATEGORIES.items())
def test_category_help_lists_its_services_in_listing_order(category, services):
    output = help_of(category)
    positions = [output.index(f"\n  {name} ") for name in services]
    assert positions == sorted(positions)
    assert list(cli.commands[category].commands) == services


@pytest.mark.parametrize(
    "category,service", [(c, s) for c, services in CATEGORIES.items() for s in services]
)
def test_services_work_under_their_category_and_at_top_level(category, service):
    nested = help_of(category, service)
    assert f"Usage: scaleinn {category} {service} " in nested
    assert f"Usage: scaleinn {service} " in help_of(service)
    # the very same command object is registered in both places
    assert cli.commands[service] is cli.commands[category].commands[service]


def test_documented_example_commands():
    for args in (["ice"], ["cloud-dns"], ["ct"], ["object-storage"], ["network", "cloud-dns"]):
        assert runner.invoke(cli, [*args, "--help"]).exit_code == 0


def test_requested_service_names_are_all_present():
    # ICE; Network (7); Block storage (4); Images (2); Managed services (6)
    wanted = {"ice", "network", "vpc", "shared-vpc", "ipam", "router", "security-group", "reserved-ip",
              "cloud-dns", "block-storage", "network-storage", "additional-disks", "snapshot", "os-disks",
              "images", "marketplace-images", "project-images", "managed-services", "database", "docker",
              "load-balancer", "waf", "vps", "alert-manager"}
    assert wanted <= set(cli.commands)


def test_help_for_services_needs_no_network_and_no_login(http):
    for name in ALL_SERVICES:
        help_of(name)
    assert http.calls == []


# --------------------------------------------------------- file layout
@pytest.mark.parametrize("name", SKELETONS + ["ct", "object-storage"])
def test_each_service_has_commands_operations_and_models(name):
    category = next((c for c, subs in CATEGORIES.items() if name in subs), None)
    package = pkg_of(category, name)
    for module in ("commands", "operations", "models"):
        assert importlib.import_module(f"{package}.{module}")


@pytest.mark.parametrize("category", CATEGORIES)
def test_categories_only_group_services(category):
    package = category.replace("-", "_")
    module = importlib.import_module(f"scaleinn.services.{package}.commands")
    assert [c.name for c in module.SUBMODULES] == CATEGORIES[category]
    with pytest.raises(ImportError):  # operations/models live in the services, not the category
        importlib.import_module(f"scaleinn.services.{package}.operations")


@pytest.mark.parametrize("name", SKELETONS)
def test_skeleton_operations_do_not_invent_apis(name):
    category = next((c for c, subs in CATEGORIES.items() if name in subs), None)
    module = importlib.import_module(f"{pkg_of(category, name)}.operations")
    public = [n for n in vars(module) if not n.startswith("_") and callable(getattr(module, n))
              and getattr(getattr(module, n), "__module__", "") == module.__name__]
    assert public == []  # no functions yet: nothing sends requests


# ------------------------------------------------------ group classes
def test_ordered_group_keeps_registration_order():
    group = OrderedGroup("g")
    for name in ("zeta", "alpha", "mid"):
        group.add_command(click.Command(name))
    assert group.list_commands(None) == ["zeta", "alpha", "mid"]


def test_sectioned_group_shows_unlisted_commands_last_under_commands():
    group = SectionedGroup("g", help="demo")
    group.add_section("First", click.Command("a", short_help="A cmd"), click.Command("b", short_help="B cmd"))
    group.add_command(click.Command("stray", short_help="Not in a section"))
    result = runner.invoke(group, ["--help"])
    out = result.output
    assert out.index("First:") < out.index("Commands:")
    assert "A cmd" in out and "Not in a section" in out
    assert out.index("  stray") > out.index("  b ")
