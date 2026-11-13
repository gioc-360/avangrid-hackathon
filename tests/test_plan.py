"""Plan tests: `bin/ewu plan` lists match the screen, the showcase names no real home, private lists stay private.

What: transformer_actions.csv counts per action equal `bin/ewu screen` for the demo seed (and the filmed
      docs/demo/cli_output.txt); the cost column adds up to the capital plan's ladder row; the simulated files
      line up with the transformer file; no showcase file holds a real customer number or a row equal to a
      real home's (segment, annual kWh, peak kW) or a real host's row; every showcase file says what it is;
      home-level files are written only with --private; the whole run works with the network switched off.
Why:  the engine's files are the product. A wrong count, a leaked customer or a silent network call would
      each break a promise the page and the video make.
How:  one plan run on the full data into temporary folders with socket connections made to fail, then plain
      pandas comparisons against bin/ewu screen and the processed home index.
"""
import re
import socket
import pandas as pd
import pytest
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import inventory, plan, plan_output, screen, showcase

CONFIG = read_config()
SCENARIO, MARGIN = config_value("demo.scenario", CONFIG), config_value("demo.margin", CONFIG)


def no_network(*args, **kwargs):
    raise AssertionError("bin/ewu plan tried to open a network connection")


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def made(inputs, tmp_path_factory):
    dirs = {name: tmp_path_factory.mktemp(name) / "files" for name in ("out", "private", "showcase")}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, "connect", no_network)
        patch.setattr(socket, "create_connection", no_network)
        result = plan_output.execute(SCENARIO, MARGIN, show=True, dirs=dirs, inputs=inputs)
    return result | {"dirs": dirs}


def read(made, group, name):
    return pd.read_csv(made[group][name][0], comment="#")


def test_actions_equal_the_screen_for_the_demo_seed(inputs, made):
    live = screen.run_screen(inputs, CONFIG, SCENARIO, MARGIN)
    actions = read(made, "written", "transformer_actions").action.value_counts().to_dict()
    assert actions == {"none": live["transformers"] - live["flagged"] - live["new_from_stagger"],
                       "shift": live["shift_fixed"], "protect": live["protected"], "upgrade": live["upgrade_left"]}
    table = read(made, "written", "transformer_actions")
    assert int(table.batteries_needed.sum()) == live["batteries"] and int(table.over_limit.sum()) == live["flagged"]
    assert {k: made["counts"][k] for k in made["counts"]} == {k: live[k] for k in made["counts"]}


def test_actions_equal_the_filmed_cli_output(made):
    text = (ROOT / "docs" / "demo" / "cli_output.txt").read_text()
    filmed = {step.lower(): int(n.replace(",", "")) for step, n in re.findall(r"^(Shift|Protect|Upgrade)\s.*\s([\d,]+)$", text, re.M)}
    actions = read(made, "written", "transformer_actions").action.value_counts().to_dict()
    assert {k: actions[k] for k in filmed} == filmed


def test_cost_column_adds_up_to_the_ladder_row(made):
    table, capital = read(made, "written", "transformer_actions"), read(made, "written", "capital_plan")
    ladder = capital.set_index("option").loc["ladder", "pv_usd_mid"]
    assert abs(table.est_cost_usd.sum() - ladder) <= len(table) * 0.5 + 1
    assert (capital.prices == "placeholder").all() and set(capital.option) == {"upgrade_all", "shift_then_upgrade", "ladder"}
    assert sorted(table.priority) == list(range(1, len(table) + 1))


def test_showcase_lines_up_with_the_transformer_file(made):
    table = read(made, "showcase", "transformer_actions").set_index("transformer_id")
    hosts, targets = read(made, "showcase", "battery_hosts"), read(made, "showcase", "program_targets")
    homes = read(made, "showcase", "simulated_homes")
    assert (homes.groupby("transformer_id").size().reindex(table.index) == table.homes).all()
    per = hosts.groupby("transformer_id").agg(n=("rank", "size"), units=("units", "first"))
    protect = table[table.action == "protect"]
    assert per.n.reindex(protect.index).tolist() == protect.battery_hosts.tolist()
    assert per.units.reindex(protect.index).tolist() == protect.units_per_host.tolist()
    assert set(targets.transformer_id) <= set(table.index[table.action != "none"])
    assert set(hosts.home_id) <= set(targets.home_id) and set(targets.home_id) <= set(homes.home_id)


def test_showcase_holds_no_real_home_id(made):
    real = set(pd.read_parquet(ROOT / "data" / "processed" / "segmented.parquet", columns=["CUSTOMER_NUMBER"])
               .CUSTOMER_NUMBER.astype(str))
    for name in ("battery_hosts", "program_targets", "simulated_homes"):
        ids = read(made, "showcase", name).home_id.astype(str)
        assert ids.str.match(r"^SIM-\d{5}$").all() and not (set(ids) & real)


def test_no_showcase_row_equals_a_real_row(inputs, made):
    real_homes = inventory.build_inventory(CONFIG)
    homes = read(made, "showcase", "simulated_homes")
    assert not (showcase.home_keys(homes) & showcase.home_keys(real_homes))
    run = plan.run_plan(inputs, CONFIG, SCENARIO, MARGIN)
    real_hosts = plan.host_table(run, inputs, CONFIG)
    assert not (showcase.host_keys(read(made, "showcase", "battery_hosts")) & showcase.host_keys(real_hosts))


def test_every_showcase_file_says_what_it_is(made):
    folder = made["dirs"]["showcase"]
    assert showcase.NOTE in (folder / "README.md").read_text()
    for name in plan_output.FILES:
        assert showcase.NOTE in (folder / f"{name}.csv").read_text().splitlines()[0]


def test_private_files_need_the_private_flag(inputs, made, tmp_path):
    assert not made["dirs"]["private"].exists() and made["private"] == {}
    args = plan_output_parser().parse_args(["plan"])
    assert args.private is False and args.showcase is False
    dirs = {"out": tmp_path / "out", "private": tmp_path / "private", "showcase": tmp_path / "showcase"}
    result = plan_output.execute(SCENARIO, MARGIN, private=True, dirs=dirs, inputs=inputs)
    assert sorted(p.name for p in dirs["private"].iterdir()) == ["battery_hosts.csv", "program_targets.csv"]
    assert sorted(p.name for p in dirs["out"].iterdir()) == ["capital_plan.csv", "transformer_actions.csv"]
    assert not dirs["showcase"].exists() and len(result["private"]) == 2


def plan_output_parser():
    import argparse
    parser = argparse.ArgumentParser(prog="ewu")
    plan_output.add_command(parser.add_subparsers(dest="command", required=True))
    return parser
