"""Plan output: `bin/ewu plan` writes the engine's action lists, says where they went and records the counts.

What: add_command() registers `plan` on the CLI; execute() runs ewu/plan.py for one scenario and sizing and
      writes transformer_actions.csv and capital_plan.csv to outputs/plan/; with --private the real
      battery_hosts.csv and program_targets.csv go to outputs/private/plan/ (gitignored); with --showcase a
      full simulated set and its README go to outputs/showcase/. record_plan() writes the counts to facts;
      print_plan() prints counts per action and every file path.
Why:  a planner and a programs team act on files, not on a page. Home-level files name customers, so they are
      written only when asked, and only to the private folder; the showcase shows their shape with SIM homes.
How:  the default run (config demo scenario, margin and seed, random grouping) records facts, as `bin/ewu
      screen` does; any other run is a what-if and records nothing. The README is filled from
      ewu/plan_readme_template.md with this run's counts.
"""
import time
import numpy as np
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import inventory, plan, showcase, stress

TRANSFORMER_NOTE = ("Transformer level: 8-home sums of metered load on synthetic groups, no home named. "
                    "est_cost_usd uses placeholder prices. In the showcase set the home-level files are " + showcase.NOTE)
FILES = ("transformer_actions", "capital_plan", "battery_hosts", "program_targets", "simulated_homes")


def real_homes(plan_run, config):
    """Inventory rows (equipment, segment, program flags) with home_id and the synthetic transformer each sits on."""
    homes = inventory.build_inventory(config)
    groups = plan_run["groups"]
    where = np.full(len(homes), "", dtype=object)
    where[groups.homes] = [f"T-{t + 1:04d}" for t in groups.transformer]
    return homes.assign(home_id=homes.CUSTOMER_NUMBER.astype(str), transformer_id=where)


def execute(scenario, margin, grouping="random", seed=None, private=False, show=False, dirs=None, inputs=None):
    """Run the plan and write its files. dirs = {"out", "private", "showcase"} folders (tests pass temporary ones)."""
    started = time.time()
    config = read_config()
    dirs = {"out": plan.OUT, "private": plan.PRIVATE, "showcase": plan.SHOWCASE} | (dirs or {})
    inputs = inputs or read_inputs()
    run = plan.run_plan(inputs, config, scenario, margin, grouping, seed)
    counts = plan.ladder_counts(run)
    table, capital = plan.transformer_table(run, config), plan.capital_table(counts, config)
    written = {"transformer_actions": (plan.write_csv(table, dirs["out"] / "transformer_actions.csv", TRANSFORMER_NOTE), len(table)),
               "capital_plan": (plan.write_csv(capital, dirs["out"] / "capital_plan.csv", TRANSFORMER_NOTE), len(capital))}
    result = {"counts": counts, "table": table, "capital": capital, "written": written, "seed": run["run"]["seed"],
              "scenario": scenario, "margin": float(margin), "grouping": grouping, "private": {}, "showcase": {}}
    if private or show:
        hosts, homes = plan.host_table(run, inputs, config), real_homes(run, config)
        targets = plan.program_rows(homes, hosts, table)
    if private:
        note = "PRIVATE: real customer numbers, never share; written by bin/ewu plan --private"
        result["private"] = {"battery_hosts": (plan.write_csv(hosts, dirs["private"] / "battery_hosts.csv", note), len(hosts)),
                             "program_targets": (plan.write_csv(targets, dirs["private"] / "program_targets.csv", note), len(targets))}
    if show:
        hosts_seg = hosts.assign(segment=hosts.home_id.map(homes.set_index("home_id").segment))
        stats = showcase.segment_stats(homes, hosts_seg)
        sim_homes, sim_hosts, changed = showcase.simulate(stats, table, homes, hosts, config, result["seed"])
        sim_targets = plan.program_rows(sim_homes, sim_hosts, table)
        out = dirs["showcase"]
        result["showcase"] = {
            "transformer_actions": (plan.write_csv(table, out / "transformer_actions.csv", TRANSFORMER_NOTE), len(table)),
            "capital_plan": (plan.write_csv(capital, out / "capital_plan.csv", TRANSFORMER_NOTE), len(capital)),
            "battery_hosts": (plan.write_csv(sim_hosts, out / "battery_hosts.csv", showcase.NOTE), len(sim_hosts)),
            "program_targets": (plan.write_csv(sim_targets, out / "program_targets.csv", showcase.NOTE), len(sim_targets)),
            "simulated_homes": (plan.write_csv(sim_homes, out / "simulated_homes.csv", showcase.NOTE), len(sim_homes))}
        result |= {"stats": stats, "redrawn": changed, "real_host_count": len(hosts), "real_target_count": len(targets)}
        write_readme(result, out / "README.md", config)
    result["seconds"] = round(time.time() - started, 1)
    return result


def write_readme(result, path, config):
    """outputs/showcase/README.md from the template, filled with this run's counts."""
    actions = result["table"].action.value_counts()
    rows = {name: n for name, (_, n) in result["showcase"].items()}
    fill = {"scenario": result["scenario"], "margin": f"{result['margin']:.2f}", "seed": result["seed"],
            "grouping": result["grouping"], "note": showcase.NOTE, "redrawn": f"{result['redrawn']:,}",
            "segments": len(result["stats"]["segments"]), "feeders": config_value("network.feeders", config),
            **{f"rows_{k}": f"{v:,}" for k, v in rows.items()},
            **{f"n_{a}": f"{int(actions.get(a, 0)):,}" for a in plan.ACTIONS}}
    template = (ROOT / "ewu" / "plan_readme_template.md").read_text()
    path.write_text(template.format(**fill))


def record_plan(result):
    """Counts per action, rows per file and runtime to facts/facts.json (aggregates only)."""
    from analysis.facts import record
    key = f"ewu.plan.{result['scenario']}.{result['grouping']}.{stress.margin_label(result['margin'])}"
    how = f"bin/ewu plan, seed {result['seed']}, {result['counts']['transformers']} synthetic transformers, same states as bin/ewu screen"
    for action, n in result["table"].action.value_counts().items():
        record(f"{key}.actions.{action}", int(n), "transformers", how)
    record(f"{key}.est_cost_total_usd", int(result["table"].est_cost_usd.sum()), "$ present value, mid placeholder prices", how)
    for group in ("written", "showcase"):
        for name, (_, n) in result[group].items():
            record(f"ewu.plan.rows.{group}.{name}", n, "rows", how)
    if result["showcase"]:
        record("ewu.plan.showcase.redrawn", result["redrawn"], "simulated values redrawn", "privacy guard: equal to a real row")
        for segment, s in result["stats"]["segments"].items():
            for name, value in s.items():
                record(f"ewu.plan.showcase.segment.{segment}.{name}", round(value, 4) if isinstance(value, float) else value,
                       "share" if name.endswith("share") else "kWh" if "kwh" in name else "kW" if "kw" in name else "homes",
                       "segment aggregate the simulator samples from, all inventory homes")
        for units, s in result["stats"]["hosts"].items():
            for name, value in s.items():
                record(f"ewu.plan.showcase.host_units_{units}.{name}", round(value, 4), "kW" if "kw" in name else "hosts",
                       "real fit-score hosts of this run, aggregate the simulator samples from")
    record("ewu.plan.seconds", result["seconds"], "s", "whole bin/ewu plan run, data load and writing included")


def print_plan(result):
    t, c = result["table"], result["counts"]
    print(f"EWU plan: {result['scenario']} 2030, rating = today's peak x {result['margin']:.2f}, "
          f"{result['grouping']} grouping, seed {result['seed']}")
    print(f"{c['transformers']:,} transformers, {int(t.homes.sum()):,} homes; cost at mid placeholder prices\n")
    print(f"{'action':<8} {'transformers':>12} {'batteries':>9} {'est. cost $':>13}")
    for action in plan.ACTIONS:
        on = t.action == action
        print(f"{action:<8} {int(on.sum()):>12,} {int(t.batteries_needed[on].sum()):>9,} {int(t.est_cost_usd[on].sum()):>13,}")
    print()
    for group in ("written", "private", "showcase"):
        for name, (path, n) in result[group].items():
            print(f"{group:<9} {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}  {n:,} rows")
    if not result["private"]:
        print("private   not written (real home lists need --private; they stay in outputs/private)")
    print(f"\n{result['seconds']:.1f} s, offline, home-level files only with --private or simulated with --showcase")


def run_command(args):
    result = execute(args.scenario, args.margin, args.grouping, args.seed, args.private, args.showcase)
    official = (args.scenario, args.margin, args.grouping, args.seed) == (
        config_value("demo.scenario"), config_value("demo.margin"), "random", None)
    if official:
        record_plan(result)
    print_plan(result)
    print("facts recorded" if official else "what-if run: facts not recorded")
    return 0


def add_command(commands):
    """Register `bin/ewu plan` on the CLI's subcommands."""
    cmd = commands.add_parser("plan", help="action lists: transformers, capital plan; homes with --private or --showcase")
    cmd.add_argument("--scenario", default=config_value("demo.scenario"), choices=stress.SCENARIOS)
    cmd.add_argument("--margin", type=float, default=config_value("demo.margin"), help="rating = today's peak x this")
    cmd.add_argument("--grouping", default="random", choices=("random", "same_segment"))
    cmd.add_argument("--seed", type=int, default=None, help="grouping seed; default config demo.screen_seed")
    cmd.add_argument("--private", action="store_true", help="also write real home lists to outputs/private/plan")
    cmd.add_argument("--showcase", action="store_true", help="also write a simulated home-level set to outputs/showcase")
    cmd.set_defaults(run=run_command)
