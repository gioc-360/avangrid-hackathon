"""Adoption: which homes add an EV or a heat pump by 2030, and what each one adds to the wires hour by hour.

What: measure_ev_sessions() reads real Level 2 charging sessions from the meter data; pick_adopters() draws the
      2030 adopters for a scenario; draw_ev_sessions() gives each new EV a year of sessions; heat_pump_kw()
      is the kW one heat pump adds in each hour of the year.
Why:  the stress test is only as good as the load it adds. EV timing comes from measured start hours and
      durations in this data, not a guessed evening block; heat pump kW follows the measured cold-weather slope.
How:  a charging hour is load at least `ev_session_jump_kw` above that day's 25th percentile (the rule
      analysis/classify.py uses to flag Level 2 homes); a session starts when such hours begin and are held
      `ev_session_min_hours`, counted on weather-neutral days so heating cannot pose as a charger. Each new EV
      then charges on a day with the measured probability, at `ev_l2_kw`, with a start and length drawn
      together from the measured sessions. Adopters are drawn without replacement from grouped homes that do
      not have the device today and are not vacant; one random order per seed, so high adopters include moderate.
      With `adopters_share_one_order` true (the recorded runs) EV and heat pump adopters come off the same order,
      so most new heat pump homes also get a new EV; false gives the heat pump its own order (the M8 variant).
"""
import numpy as np
from ewu import config_value

HOURS = 8760


def charging_hours(load_rows, jump_kw):
    """True where a home's load sits at least jump_kw above its own 25th percentile of that day."""
    days = np.asarray(load_rows, dtype=np.float32).reshape(len(load_rows), HOURS // 24, 24)
    floor = np.percentile(days, 25, axis=2, keepdims=True)
    return ((days - floor) >= jump_kw).reshape(len(load_rows), HOURS)


def run_lengths(flags):
    """For every hour, how many hours in a row the flag stays on from that hour forward."""
    runs = np.zeros(flags.shape, dtype=np.int32)
    runs[:, -1] = flags[:, -1]
    for h in range(flags.shape[1] - 2, -1, -1):
        runs[:, h] = np.where(flags[:, h], runs[:, h + 1] + 1, 0)
    return runs


def measure_ev_sessions(load, is_ev_l2, temp, config):
    """Measured Level 2 sessions: start hour of day, length in hours, and sessions per home per day."""
    jump = config_value("scenarios.loads.ev_session_jump_kw", config)
    held = config_value("scenarios.loads.ev_session_min_hours", config)
    low = config_value("scenarios.loads.ev_neutral_day_low_f", config)
    high = config_value("scenarios.loads.ev_neutral_day_high_f", config)
    rows = np.where(np.asarray(is_ev_l2))[0]
    flags = charging_hours(load[rows], jump)
    runs = run_lengths(flags)
    before = np.zeros_like(flags)
    before[:, 1:] = flags[:, :-1]
    day_mean = temp.reshape(-1, 24).mean(1)
    neutral_day = (day_mean >= low) & (day_mean <= high)
    starts = flags & ~before & (runs >= held) & np.repeat(neutral_day, 24)[None, :]
    home, hour = np.nonzero(starts)
    return {
        "start_hour": (hour % 24).astype(np.int32),
        "length_hours": runs[home, hour],
        "per_home_day": len(hour) / (len(rows) * int(neutral_day.sum())),
        "homes": len(rows),
        "neutral_days": int(neutral_day.sum()),
    }


def pick_adopters(group_homes, homes, scenario, seed, config):
    """Return (ev_homes, hp_homes): row numbers of grouped homes that add each device under the scenario."""
    rng = np.random.default_rng((seed, 1))
    grouped = np.asarray(group_homes)
    order = grouped[rng.permutation(len(grouped))]
    vacant = homes["is_other_inactive"].to_numpy()
    picks = []
    for device, has_today in (("ev_share", "is_ev_l2"), ("hp_share", "is_electric_heat")):
        if device == "hp_share" and not config_value("scenarios.loads.adopters_share_one_order", config):
            order = grouped[np.random.default_rng((seed, 3)).permutation(len(grouped))]
        share = config_value(f"scenarios.{scenario}.{device}", config)
        eligible = order[~homes[has_today].to_numpy()[order] & ~vacant[order]]
        wanted = int(round(share * len(grouped)))
        if wanted > len(eligible):
            raise ValueError(f"{scenario} wants {wanted} {device} adopters but only {len(eligible)} homes can add one")
        picks.append(np.sort(eligible[:wanted]))
    return picks[0], picks[1]


def draw_ev_sessions(ev_homes, sessions, seed, scenario_index=0):
    """A year of charging for each new EV: arrays of home row, first absolute hour, and length in hours."""
    rng = np.random.default_rng((seed, 2, scenario_index))
    days = HOURS // 24
    charges = rng.random((len(ev_homes), days)) < sessions["per_home_day"]
    home_pos, day = np.nonzero(charges)
    pick = rng.integers(0, len(sessions["start_hour"]), size=len(day))
    start = day * 24 + sessions["start_hour"][pick]
    return {"home": np.asarray(ev_homes)[home_pos], "start": start, "hours": sessions["length_hours"][pick]}


def session_hours(ev_sessions):
    """Expand sessions into (home row, absolute hour) pairs; hours past the end of the year are dropped."""
    lengths = ev_sessions["hours"]
    first = np.repeat(ev_sessions["start"], lengths)
    offset = np.arange(lengths.sum()) - np.repeat(np.cumsum(lengths) - lengths, lengths)
    hour = first + offset
    keep = hour < HOURS
    return np.repeat(ev_sessions["home"], lengths)[keep], hour[keep]


def heat_pump_kw(temp, config):
    """kW one new heat pump adds in each hour: the measured slope times degrees below the balance point."""
    slope = config_value("scenarios.loads.hp_kw_per_degf", config)
    balance = config_value("scenarios.loads.hp_balance_temp_f", config)
    return (slope * np.maximum(0.0, balance - np.asarray(temp, dtype=np.float64))).astype(np.float32)
