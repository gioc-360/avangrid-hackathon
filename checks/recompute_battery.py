"""Recompute battery: rebuild the battery and cold snap facts with separate code and compare them to facts.json.

What: from data/processed and config/ewu.yaml, recomputes the share of transformers home batteries clear
      (moderate and high, peak x 1.15), the Feb 7-8 cold snap flagged share, one- and two-host clear rates and
      the one-host share that hits empty, the fit-score and random-host kW cut per battery in the system's top
      20 hours, and batteries per protected transformer; writes runs/recompute_battery.json (aggregates only)
      and exits 1 when any fact misses its tolerance. --selftest runs toy cases and a planted wrong fact.
Why:  M3's battery numbers were never rerun by code other than the code that made them. A second
      implementation of the same rules that lands on the same numbers is the check; one that does not points
      at the side that is wrong.
How:  only ewu/feeders, ewu/adoption and ewu/stress are imported, for the same transformers, adopters and
      loads. Staggered charging, the fit score and dispatch come from checks/battery_model.py; home loads, host
      choice, the cheapest clearing option and pooling are written here, and every scenario and option of a
      seed runs in one dispatch batch. Tolerance: 1.0 percentage point for a share, 5% relative otherwise.
"""
import argparse, copy, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ewu import adoption, feeders, stress  # noqa: E402  (same synthetic transformers, adopters and loads only)
from checks.battery_model import CFG, HOURS, TOL, battery, dispatch, fit_scores, setting, staggered_rows  # noqa: E402

DATA, OUT = ROOT / "data" / "processed", ROOT / "runs" / "recompute_battery.json"
CS, TH, SN = "ewu.coldsnap.moderate.staggered.margin_115", "ewu.tophours.moderate.staggered.margin_115", "ewu.sensitivity"
CHECKED = {f"{SN}.moderate.random.margin_115.protected_pct": "pct", f"{SN}.high.random.margin_115.protected_pct": "pct",
           f"{CS}.flagged_pct": "pct", f"{CS}.hosts_1.cleared_pct": "pct", f"{CS}.hosts_2.cleared_pct": "pct",
           f"{CS}.hosts_1.ran_empty_pct": "pct", f"{TH}.fit_score.units_1.top_20.kw_per_battery": "rel",
           f"{TH}.random.units_1.top_20.kw_per_battery": "rel",
           f"{SN}.moderate.random.margin_115.batteries_per_protected": "rel",
           "ewu.economics.battery_vs_upgrade.mid.batteries_per_cleared": "rel"}


def one_seed(inputs, seed, sessions, top, days):
    """Counts and sums for one seed: flagged sets, fleet cuts, and dispatch rows (one per transformer and option)."""
    k, count, limit = setting("transformer.homes_per_transformer"), setting("transformer.count"), setting("transformer.overload_limit")
    groups = feeders.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", seed)
    base = stress.base_loading(inputs["load"], groups)
    ceiling = limit * base.max(1) * setting("transformer.base_margin")
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    hp_kw, (first, last), out, rows = adoption.heat_pump_kw(inputs["temp"], CFG).astype(np.float64), top["window"], {}, []
    for i, scenario in enumerate(("moderate", "high")):
        parts = stress.loading_parts(inputs, groups, scenario, seed, CFG, sessions, base)
        home, hour, kw = staggered_rows(parts["ev_sessions"], parts["ev_homes"], owner)
        total = base + parts["hp"] + np.bincount(owner[home] * HOURS + hour, kw, count * HOURS).reshape(count, HOURS)
        flagged = np.flatnonzero(((total - ceiling[:, None]) > TOL).any(1))
        homes, place = groups.homes.reshape(count, k)[flagged].ravel(), np.full(len(owner), -1)
        place[homes] = np.arange(len(homes))
        on = place[home] >= 0
        home_kw = np.asarray(inputs["load"][homes], dtype=np.float64) + np.isin(homes, parts["hp_homes"])[:, None] * hp_kw
        home_kw += np.bincount(place[home[on]] * HOURS + hour[on], kw[on], len(homes) * HOURS).reshape(len(homes), HOURS)
        home_kw = home_kw.reshape(len(flagged), k, HOURS)
        out[f"{scenario}.flagged"], ranked = len(flagged), {}
        for units in setting("battery.units_per_host_options"):
            ranked[units] = np.argsort(-fit_scores(home_kw[:, :, top["season"]], days["season"], units), 1, kind="stable")
            for hosts in setting("battery.coldsnap_hosts_per_transformer"):
                rows.append((scenario, hosts, units, total[flagged], ceiling[flagged], home_kw, ranked[units][:, :hosts]))
        if scenario != "moderate":
            continue
        t = np.arange(len(flagged))[:, None]
        coin = np.argsort(np.random.default_rng((seed, 4, i)).random((len(flagged), k)), 1, kind="stable")
        for name, pick in (("fit_score", ranked[1][:, :1]), ("random", coin[:, :1])):
            out[f"top20.{name}"] = float(fit_scores(home_kw[t, pick][:, :, top["top_20"]], days["top_20"], 1).sum())
        above = total[flagged, first:last] - ceiling[flagged, None]
        cold = np.flatnonzero((above > TOL).any(1))
        out["coldsnap.flagged"], worst = len(cold), first + above[cold].argmax(1)
        order = np.argsort(-home_kw[cold][np.arange(len(cold)), :, worst], 1, kind="stable")
        for hosts in setting("battery.coldsnap_hosts_per_transformer"):
            rows.append(("coldsnap", hosts, setting("battery.units_per_host_max"), total[flagged[cold]],
                         ceiling[flagged[cold]], home_kw[cold], order[:, :hosts]))
    return out, run_rows(rows, top["window"])


def run_rows(rows, window):
    """Stack every row group into one batch (two host slots, unused slot empty), dispatch, split results back."""
    sizes, at = [len(r[3]) for r in rows], 0
    host_kw, spec = np.zeros((sum(sizes), max(r[1] for r in rows), HOURS)), np.zeros((3, sum(sizes), max(r[1] for r in rows)))
    for _, hosts, units, _, _, home_kw, pick in rows:
        host_kw[at:at + len(pick), :hosts] = home_kw[np.arange(len(pick))[:, None], pick]
        spec[:, at:at + len(pick), :hosts] = np.array(battery(units))[:, None, None]
        at += len(pick)
    over, left, empty = dispatch(np.concatenate([r[3] for r in rows]), np.concatenate([r[4] for r in rows]),
                                 host_kw, spec[0], spec[1], spec[2], window)
    edges = np.cumsum([0] + sizes)
    return [(r[0], r[1], r[2], over[a:b], left[a:b], empty[a:b]) for r, a, b in zip(rows, edges[:-1], edges[1:])]


def recompute(seeds):
    """Pool every seed into the checked facts' values."""
    weather, sysload = pd.read_parquet(DATA / "weather.parquet"), np.load(DATA / "sysload.npy")
    inputs = {"load": np.load(DATA / "load_present.npy", mmap_mode="r"), "temp": weather["temp"].to_numpy(),
              "homes": pd.read_parquet(DATA / "segmented.parquet", columns=["segment", "is_ev_l2", "is_electric_heat", "is_other_inactive"])}
    index = weather.index
    season = np.sort(np.concatenate([m[np.argsort(-sysload[m], kind="stable")[:setting("battery.top_hours_per_season")]]
                                     for m in (np.flatnonzero(index.month.isin(setting(f"battery.{s}_months"))) for s in ("winter", "summer"))]))
    first = index.get_loc(pd.Timestamp(setting("demo.cold_snap_start")))
    span = (pd.Timestamp(setting("demo.cold_snap_end")) - pd.Timestamp(setting("demo.cold_snap_start"))).days + 1
    top = {"season": season, "top_20": np.sort(np.argsort(-sysload, kind="stable")[:20]), "window": (first, first + 24 * span)}
    days = {name: np.asarray(index[top[name]].normalize().asi8) for name in ("season", "top_20")}
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], CFG)
    sums, need = {}, {"moderate": [], "high": []}
    add = lambda key, value: sums.__setitem__(key, sums.get(key, 0) + value)
    for seed in seeds:
        out, results = one_seed(inputs, seed, sessions, top, days)
        for key, value in out.items():
            add(key, value)
        for scenario in need:
            options = sorted([r for r in results if r[0] == scenario], key=lambda r: (r[1] * r[2], r[1]))
            batteries = np.zeros(len(options[0][3]), np.int64)
            for _, hosts, units, over, _, _ in options:
                batteries[(over == 0) & (batteries == 0)] = hosts * units
            need[scenario].append(batteries)
        for _, hosts, _, _, left, empty in (r for r in results if r[0] == "coldsnap"):
            add(f"cold.{hosts}.cleared", int((left <= TOL).sum())), add(f"cold.{hosts}.empty", int(empty.sum()))
    whole = len(seeds) * setting("transformer.count")
    pct = lambda part, of: round(100.0 * part / of, 2)
    got = {f"{SN}.{s}.random.margin_115.protected_pct": pct((np.concatenate(need[s]) > 0).sum(), whole) for s in need}
    mod = np.concatenate(need["moderate"])
    for key in (f"{SN}.moderate.random.margin_115.batteries_per_protected", "ewu.economics.battery_vs_upgrade.mid.batteries_per_cleared"):
        got[key] = round(float(mod[mod > 0].mean()), 2)
    cold = sums["coldsnap.flagged"]
    got |= {f"{CS}.flagged_pct": pct(cold, whole), f"{CS}.hosts_1.cleared_pct": pct(sums["cold.1.cleared"], cold),
            f"{CS}.hosts_2.cleared_pct": pct(sums["cold.2.cleared"], cold), f"{CS}.hosts_1.ran_empty_pct": pct(sums["cold.1.empty"], cold)}
    return got | {f"{TH}.{name}.units_1.top_20.kw_per_battery": round(sums[f"top20.{name}"] / sums["moderate.flagged"], 2)
                  for name in ("fit_score", "random")}


def compare(facts, got):
    """One row per checked fact: fact, recomputed, tolerance, match. A share gets 1.0 point, any other number 5%."""
    allowed = {key: 1.0 if kind == "pct" else 0.05 * abs(facts[key]["value"]) for key, kind in CHECKED.items()}
    return [{"fact": key, "fact_value": facts[key]["value"], "recomputed": got[key], "tolerance": round(allowed[key], 4),
             "match": bool(abs(got[key] - facts[key]["value"]) <= allowed[key])} for key in CHECKED]


def run_selftest():
    """Toy cases with known answers, then a planted wrong fact that must fail. No data needed."""
    toy = lambda load, host: dispatch(np.array([load]), np.array([10.0]), np.full((1, 1, 4), host),
                                      *(np.array([[x]]) for x in battery(1)), (0, 4))
    checks = {"a battery that covers the excess clears it": toy([12.0, 12, 12, 5], 4.0)[0][0] == 0,
              "an excess above the battery's power stays over": toy([14.0, 14, 14, 5], 9.0)[0][0] == 3,
              "a host cuts no more than its own load": toy([12.0, 12, 5, 5], 1.0)[0][0] == 2,
              "an excess longer than the energy runs it empty": bool(toy([13.5, 13.5, 13.5, 13.5], 9.0)[2][0])}
    sessions = {"home": np.array([5, 9]), "start": np.array([30, HOURS - 2]), "hours": np.array([3, 4])}
    _, hour, kw = staggered_rows(sessions, np.array([5, 9]), np.zeros(10, np.int64))
    checks["staggering keeps each session's kWh and wraps past the year end"] = (
        abs(kw.sum() - 5 * setting("scenarios.loads.ev_l2_kw")) < 1e-9 and hour.max() < HOURS)
    checks["no code from ewu/dispatch, coldsnap, fitscore, shift, sensitivity or tophours is loaded"] = not any(
        f"ewu.{m}" in sys.modules for m in ("dispatch", "coldsnap", "fitscore", "shift", "sensitivity", "tophours", "economics"))
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    got = {key: facts[key]["value"] for key in CHECKED}
    checks["the recorded facts pass against themselves"] = all(r["match"] for r in compare(facts, got))
    for key, shift in ((f"{SN}.moderate.random.margin_115.protected_pct", 1.5), (f"{TH}.fit_score.units_1.top_20.kw_per_battery", 0.1)):
        planted = copy.deepcopy(facts)
        planted[key]["value"] += shift
        checks[f"caught: {key.split('.', 1)[1]} planted {shift} off"] = not all(r["match"] for r in compare(planted, got))
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return all(checks.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="toy cases and a planted wrong fact; no data")
    parser.add_argument("--seeds", type=int, default=setting("checks.seeds"))
    args = parser.parse_args()
    if args.selftest:
        sys.exit(0 if run_selftest() else 1)
    started = time.time()
    rows = compare(json.loads((ROOT / "facts" / "facts.json").read_text()), recompute(range(args.seeds)))
    seconds = round(time.time() - started, 1)
    OUT.write_text(json.dumps({"seeds": args.seeds, "rows": rows}, indent=1) + "\n")  # no timing, so reruns leave git clean
    for r in rows:
        print(f"{'PASS' if r['match'] else 'FAIL'}  {r['fact']:<70} fact {r['fact_value']:>7} recomputed {r['recomputed']:>7}")
    misses = sum(not r["match"] for r in rows)
    print(f"recompute_battery: {len(rows) - misses} of {len(rows)} reproduce, {seconds} s, aggregates only")
    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
