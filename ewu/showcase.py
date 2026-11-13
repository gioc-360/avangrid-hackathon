"""Showcase: simulated homes that make the engine's home-level lists showable without naming a real customer.

What: segment_stats() reduces the real homes to aggregates (per segment: share of homes, mean and spread of
      annual kWh and peak kW, share eligible for each program; per battery size: mean and spread of a host's kW
      cut; host segment shares). simulate() draws SIM-00001... homes from those aggregates alone, places them on
      the synthetic transformers (8 each, as in transformer_actions.csv), gives every protected transformer as
      many simulated hosts and units as the real run chose, and redraws any value that happens to equal a real
      home's or a real host's row (privacy_guard).
Why:  the programs team's lists name homes, so the real ones never leave outputs/private. A judge still needs
      to see what the engine hands over; simulated rows show the shape and the counts without copying a row.
How:  numpy draws with a fixed seed: segment by its share, annual kWh and peak kW lognormal with the segment's
      mean and standard deviation, each program flag a coin with the segment's eligible share, host kW cut
      normal with its size's mean and spread, clipped to the battery's power. The sampler reads only the stats
      dict; the guard alone compares to real rows, and only to change a simulated value that matches one.
"""
import numpy as np
import pandas as pd
from ewu import dispatch
from ewu.plan import PROGRAMS

NOTE = "Simulated data for demonstration; generated from segment-level statistics, no real customer rows"
FLAGS = [flag for flag, _ in PROGRAMS.values() if flag != "is_host"]


def spread(series):
    return float(series.std(ddof=0)) if len(series) > 1 else 0.0


def segment_stats(homes, hosts):
    """Aggregates only. `homes` has segment, annual_kwh, peak_kw and the program flags; `hosts` has units,
    kw_cut_top_hours and the host's segment."""
    homes = homes[homes.segment.fillna("") != ""]
    out = {"segments": {}, "hosts": {}, "host_segments": {}}
    for segment, g in homes.groupby("segment"):
        out["segments"][segment] = {"homes": len(g), "share": len(g) / len(homes),
                                    "annual_kwh_mean": float(g.annual_kwh.mean()), "annual_kwh_sd": spread(g.annual_kwh),
                                    "peak_kw_mean": float(g.peak_kw.mean()), "peak_kw_sd": spread(g.peak_kw),
                                    **{f"{flag}_share": float(g[flag].mean()) for flag in FLAGS}}
    for units, g in hosts.groupby("units"):
        out["hosts"][int(units)] = {"hosts": len(g), "kw_cut_mean": float(g.kw_cut_top_hours.mean()),
                                    "kw_cut_sd": spread(g.kw_cut_top_hours)}
    for segment, share in hosts.segment.value_counts(normalize=True).items():
        out["host_segments"][segment] = float(share)
    return out


def lognormal(rng, mean, sd, size):
    """Positive draws with the given mean and standard deviation."""
    mean = max(mean, 1e-3)
    sigma2 = np.log1p((sd / mean) ** 2)
    return rng.lognormal(np.log(mean) - sigma2 / 2, np.sqrt(sigma2), size)


def draw_attributes(rng, stats, segments):
    """Annual kWh, peak kW and program flags for homes of the given segments, from that segment's stats."""
    n = len(segments)
    out = {"annual_kwh": np.zeros(n, dtype=int), "peak_kw": np.zeros(n)} | {flag: np.zeros(n, dtype=bool) for flag in FLAGS}
    for segment in np.unique(segments):
        on, s = segments == segment, stats["segments"][segment]
        out["annual_kwh"][on] = lognormal(rng, s["annual_kwh_mean"], s["annual_kwh_sd"], on.sum()).round(0)
        out["peak_kw"][on] = lognormal(rng, s["peak_kw_mean"], s["peak_kw_sd"], on.sum()).round(2)
        for flag in FLAGS:
            out[flag][on] = rng.random(on.sum()) < s[f"{flag}_share"]
    return out


def pick(rng, shares, size):
    names = list(shares)
    weights = np.array([shares[n] for n in names], dtype=float)
    return rng.choice(names, size=size, p=weights / weights.sum())


def simulate_homes(rng, stats, transformers):
    """SIM homes, as many per transformer as transformer_actions.csv says, segment drawn by its share."""
    ids = np.repeat(transformers.transformer_id.to_numpy(), transformers.homes.to_numpy())
    segments = pick(rng, {k: v["share"] for k, v in stats["segments"].items()}, len(ids))
    homes = pd.DataFrame({"home_id": [f"SIM-{i + 1:05d}" for i in range(len(ids))], "transformer_id": ids,
                          "segment": segments})
    return homes.assign(**draw_attributes(rng, stats, segments))


def simulate_hosts(rng, stats, transformers, homes, config):
    """Per protected transformer: as many simulated hosts and units as the real run chose, ranked by kW cut."""
    where = homes.groupby("transformer_id").indices
    rows, hosts_at = [], []
    for t in transformers[transformers.battery_hosts > 0].itertuples():
        at = rng.choice(where[t.transformer_id], size=t.battery_hosts, replace=False)
        power = dispatch.battery_spec(t.units_per_host, config)["power_kw"]
        s = stats["hosts"].get(t.units_per_host) or next(iter(stats["hosts"].values()))
        cut = np.sort(np.clip(rng.normal(s["kw_cut_mean"], s["kw_cut_sd"], t.battery_hosts), 0.01, power))[::-1]
        hosts_at.extend(at)
        rows += [{"transformer_id": t.transformer_id, "rank": r + 1, "home_id": homes.home_id[a],
                  "fit_score": round(c / power, 3), "kw_cut_top_hours": round(c, 2), "units": t.units_per_host}
                 for r, (a, c) in enumerate(zip(at, cut))]
    hosts_at = np.array(hosts_at, dtype=int)
    if len(hosts_at):
        segments = pick(rng, stats["host_segments"], len(hosts_at))
        homes.loc[hosts_at, "segment"] = segments
        for name, values in draw_attributes(rng, stats, segments).items():
            homes.loc[hosts_at, name] = values
    return pd.DataFrame(rows, columns=["transformer_id", "rank", "home_id", "fit_score", "kw_cut_top_hours", "units"])


def home_keys(homes):
    return set(zip(homes.segment.astype(str), np.asarray(homes.annual_kwh).round(0).astype(int),
                   np.asarray(homes.peak_kw, dtype=float).round(2)))


def host_keys(hosts):
    return set(zip(hosts.transformer_id, hosts["rank"].astype(int), hosts.units.astype(int),
                   np.asarray(hosts.kw_cut_top_hours, dtype=float).round(2)))


def privacy_guard(rng, stats, homes, hosts, real_homes, real_hosts, config):
    """Redraw any simulated home or host whose values equal a real row; returns the hosts and how many changed."""
    real_h, real_b, changed = home_keys(real_homes), host_keys(real_hosts), 0
    for _ in range(100):
        hit = np.array([k in real_h for k in zip(homes.segment.astype(str), homes.annual_kwh.astype(int),
                                                 homes.peak_kw.astype(float).round(2))], dtype=bool)
        if not hit.any():
            break
        changed += int(hit.sum())
        for name, values in draw_attributes(rng, stats, homes.segment.to_numpy()[hit]).items():
            homes.loc[hit, name] = values
    for _ in range(100):
        hit = np.array([k in real_b for k in zip(hosts.transformer_id, hosts["rank"], hosts.units,
                                                 hosts.kw_cut_top_hours.round(2))], dtype=bool)
        if not hit.any():
            break
        changed += int(hit.sum())
        power = np.array([dispatch.battery_spec(int(u), config)["power_kw"] for u in hosts.units])
        now = hosts.kw_cut_top_hours.to_numpy()
        cut = (now + np.where(hit, np.where(now + 0.01 > power, -0.01, 0.01), 0.0)).round(2)
        hosts["kw_cut_top_hours"], hosts["fit_score"] = cut, (cut / power).round(3)
        hosts = hosts.sort_values(["transformer_id", "kw_cut_top_hours"], ascending=[True, False])
        hosts["rank"] = hosts.groupby("transformer_id").cumcount() + 1
    return hosts, changed


def simulate(stats, transformers, real_homes, real_hosts, config, seed):
    """The whole simulated set: homes and hosts lined up with transformer_actions.csv, guarded against real rows."""
    rng = np.random.default_rng((seed, 77))
    homes = simulate_homes(rng, stats, transformers)
    hosts = simulate_hosts(rng, stats, transformers, homes, config)
    hosts, changed = privacy_guard(rng, stats, homes, hosts, real_homes, real_hosts, config)
    return homes, hosts.sort_values(["transformer_id", "rank"]).reset_index(drop=True), changed
