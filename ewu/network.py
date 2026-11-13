"""Network: the live screen's own synthetic network, transformer by transformer, for the demo page's Network view.

What: run_network() runs the demo screen case (config demo.scenario, demo.margin, random grouping, seed
      demo.screen_seed) and returns, per synthetic transformer, its feeder, its final rung (within limit,
      shifted, protected, upgrade), whether unmanaged charging flags it, the batteries that clear it, and its
      worst 2030 day: base, EV and heat pump kW by hour against its limit, with the load after its fix.
      view_counts() counts the transformers in each state at every step of the ladder; record_network()
      writes those counts to facts (aggregates) and the per-transformer arrays to private facts.
Why:  judges see a grid planning tool when they see the network itself: one substation, its feeders, every
      transformer, recolored as each rung of the ladder is applied. The counts must equal `bin/ewu screen`.
How:  the same setup as ewu/screen.py (screen_setup, batch_loading) and the same ladder states as the
      sensitivity grid (sensitivity.ladder_states_for_one_run), so nothing in the model is rewritten here.
      Feeders are an illustrative split: transformer ids cut into `network.feeders` equal blocks. A protected
      transformer's battery effect is its cheapest clearing option, fit-score hosts, dispatched all year.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
from ewu import config_value, read_config, read_inputs
from ewu import dispatch, fitscore, screen, sensitivity, shift, stress
from ewu.adoption import HOURS

STATES = ("within", "shifted", "protected", "upgrade")
VIEWS = ("today", "flag", "shift", "protect", "upgrade")


def feeder_of(count, feeders):
    """Feeder number per transformer id: equal blocks by id, an illustrative split."""
    return (np.arange(count) * feeders) // count


def final_state(flag, protect, batteries):
    """0 within limit all year, 1 fixed by staggered charging, 2 cleared by batteries, 3 left for an upgrade."""
    state = np.where(flag & ~protect, 1, 0)
    state = np.where(protect & (batteries > 0), 2, state)
    return np.where(protect & (batteries == 0), 3, state)


def looks(view, state, flag, over_today):
    """State word per transformer at one step of the ladder; the page's look() in demo_template.html is the same rule."""
    if view == "today":
        return np.where(over_today, "over", "within")
    if view == "flag":
        return np.where(flag, "over", "within")
    late = {"shift": ("over", "over"), "protect": ("protected", "over"), "upgrade": ("protected", "upgrade")}[view]
    return np.select([state == 0, state == 1, state == 2], ["within", "shifted", late[0]], late[1])


def view_counts(state, flag, over_today):
    """{view: {state word: transformers}} for every step of the ladder, from the final states and flags."""
    out = {}
    for view in VIEWS:
        words, n = np.unique(looks(view, state, flag, over_today), return_counts=True)
        out[view] = {"within": 0} | {str(w): int(c) for w, c in zip(words, n)}
    return out


def chosen_option(placed, need, config):
    """Per Protect row: (hosts, units) of the cheapest option that clears it, as cheapest_clear picks, else (0, 0)."""
    hosts, units = np.zeros(len(need), dtype=np.int64), np.zeros(len(need), dtype=np.int64)
    for h, u in sorted(sensitivity.options_from_config(config), key=lambda o: (o[0] * o[1], o[0])):
        hit = placed[(h, u)] & (hosts == 0)
        hosts[hit], units[hit] = h, u
    return hosts, units


def battery_net_load(st, top, top_day, config):
    """Per Protect row: load after its chosen batteries, all year (rows no option clears stay as they are)."""
    setup, rows = st["setup"], st["rows"]
    hosts, units = chosen_option(st["placed"], st["need"], config)
    total = setup["total"][rows]
    net = total.copy()
    ceiling = st["ceiling"][setup["flagged"][rows]]
    for h, u in sorted({(int(a), int(b)) for a, b in zip(hosts, units) if a}):
        pick = np.flatnonzero((hosts == h) & (units == u))
        spec = dispatch.battery_spec(u, config)
        scores = fitscore.fit_score(setup["home_kw"][:, :, top], top_day, spec)
        hosts_at = fitscore.choose_hosts("fit_score", scores, None, None, h, None)[rows[pick]]
        host_kw = setup["home_kw"][rows[pick][:, None], hosts_at].transpose(1, 0, 2)
        run = dispatch.run_batteries(total[pick], ceiling[pick], host_kw, spec, keep=(0, HOURS))
        net[pick] = run["net_kw"]
    return net, hosts, units


def day_rows(series, day, decimals=2):
    """(T, 24) slice of a (T, 8760) series at each transformer's day, rounded for the page (None keeps it raw)."""
    hours = day[:, None] * 24 + np.arange(24)[None, :]
    rows = np.take_along_axis(series, hours, axis=1)
    return rows if decimals is None else np.round(rows, decimals)


def run_network(inputs, config):
    """Per-transformer states and worst-day loads for the demo screen case, plus the screen-equal counts."""
    scenario, margin = config_value("demo.scenario", config), float(config_value("demo.margin", config))
    run = screen.screen_setup(inputs, config, scenario, margin, "random")
    groups = run["batches"][0]
    base, parts = screen.batch_loading(inputs, run, groups, scenario)
    one = run["config"]
    st = sensitivity.ladder_states_for_one_run(inputs, groups, base, parts, one, run["top"], run["top_day"])[margin]
    flag, protect, batteries, ceiling = st["flag"], st["protect"], st["batteries"], st["ceiling"]
    state = final_state(flag, protect, batteries)
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    ev_staggered = shift.ev_loading_by_mode("staggered", parts, owner, groups.count, one)
    unmanaged = base + parts["ev"] + parts["hp"]
    staggered = base + ev_staggered + parts["hp"]
    after = staggered.copy()
    net, hosts_rows, units_rows = battery_net_load(st, run["top"], run["top_day"], one)
    ids = st["setup"]["flagged"][st["rows"]]
    after[ids] = net
    worse = np.where(protect[:, None], staggered, unmanaged)
    day = (worse - ceiling[:, None]).argmax(1) // 24
    hosts, units = np.zeros(groups.count, dtype=np.int64), np.zeros(groups.count, dtype=np.int64)
    hosts[ids], units[ids] = hosts_rows, units_rows
    over_today = (base > ceiling[:, None]).any(1)
    today_over = int(over_today.sum())
    peak_hour = day * 24 + day_rows(worse, day).argmax(1)
    at = lambda series: np.round(series[np.arange(groups.count), peak_hour], 1)
    return {"state": state, "flag": flag, "over_today": over_today, "batteries": batteries, "hosts": hosts, "units": units,
            "feeder": feeder_of(groups.count, config_value("network.feeders", config)),
            "limit_kw": np.round(ceiling, 1), "day": day, "peak_hour_of_day": peak_hour % 24,
            "base_kw": day_rows(base, day), "ev_kw": day_rows(parts["ev"], day), "hp_kw": day_rows(parts["hp"], day),
            "ev_staggered_kw": day_rows(ev_staggered, day), "after_kw": day_rows(after, day),
            "peak_base_kw": at(base), "peak_ev_kw": at(np.where(protect[:, None], ev_staggered, parts["ev"])),
            "peak_hp_kw": at(parts["hp"]), "peak_kw": at(worse), "peak_after_kw": np.round(day_rows(after, day, None).max(1), 1),
            "counts": view_counts(state, flag, over_today), "homes": int(len(groups.homes)), "seed": run["seed"],
            "transformers": int(groups.count), "today_over": today_over}


def record_network(net, config, seconds):
    """Aggregate counts to facts/facts.json; per-transformer arrays to the private facts file only."""
    from analysis.facts import forget, record
    how = (f"demo screen case: {config_value('demo.scenario', config)} 2030, rating = today's peak x "
           f"{config_value('demo.margin', config)}, random grouping, seed {net['seed']}; same states as bin/ewu screen")
    forget("ewu.network.")
    for view, counts in net["counts"].items():
        for word, n in counts.items():
            record(f"ewu.network.{view}.{word}", n, "transformers", how)
    record("ewu.network.transformers_drawn", net["transformers"], "transformers", how)
    record("ewu.network.homes", net["homes"], "homes", "homes in the drawn transformers, 8 each")
    record("ewu.network.feeders", int(net["feeder"].max()) + 1, "feeders", "illustrative split, equal blocks by id")
    record("ewu.network.today_over", net["today_over"], "transformers", "over the limit with today's metered load")
    record("ewu.network.seconds", round(seconds, 1), "s", "whole network run, data load included")
    forget("ewu.network.", private=True)
    for name in ("state", "flag", "over_today", "batteries", "hosts", "units", "feeder", "limit_kw", "day", "peak_hour_of_day",
                 "base_kw", "ev_kw", "hp_kw", "ev_staggered_kw", "after_kw", "peak_base_kw", "peak_ev_kw",
                 "peak_hp_kw", "peak_kw", "peak_after_kw"):
        record(f"ewu.network.t.{name}", np.asarray(net[name]).astype(int if name in ("state", "flag", "over_today", "batteries",
               "hosts", "units", "feeder", "day", "peak_hour_of_day") else float).tolist(),
               "kW" if name.endswith("_kw") else "", "per synthetic transformer, 8 homes summed; " + how, private=True)


def main():
    config = read_config()
    started = time.time()
    net = run_network(read_inputs(), config)
    record_network(net, config, time.time() - started)
    print(f"Network: {net['transformers']:,} synthetic transformers on {int(net['feeder'].max()) + 1} feeders, "
          f"{net['homes']:,} homes, seed {net['seed']}")
    for view in VIEWS:
        print(f"  {view:<8} " + ", ".join(f"{word} {n:,}" for word, n in net["counts"][view].items()))
    print(f"{time.time() - started:.1f} s, aggregates only")


if __name__ == "__main__":
    main()
