"""Shift: where new EV charging lands under a simple timer and under smart staggered charging.

What: delivered_hours() is how many full-power hours each session charges inside the year when unmanaged;
      timer_loading() starts every session at `shift.timer_start_hour` on its plug-in day at full power;
      staggered_loading() starts each EV on a transformer in its own slot of the window
      `shift.stagger_start_hour` to `shift.stagger_end_hour` and charges at `shift.stagger_power_share` of the
      charger rating until the same energy is in the car. ev_loading_by_mode() picks one of the three.
Why:  the teammate's case says a timer raises overloads and staggering fixes most of them, while also saying
      most overloads are heat pump nights. Moving the same EV energy to new hours and rerunning the stress
      test is the direct way to see which claim holds.
How:  every session keeps the kWh it delivered unmanaged (the M1 loading), so shifting moves energy and never
      adds or drops any. Shifted hours that pass the last hour of the year wrap to its first hours, which
      keeps the year's energy whole. Slots go round robin by each EV home's rank on its transformer, so two
      EVs on one transformer never share a slot until the window's slots are used up.
"""
import numpy as np
from ewu import config_value
from ewu.adoption import HOURS

EV_MODES = ("unmanaged", "timer", "staggered")


def delivered_hours(ev_sessions):
    """Full-power hours each session charges before the year ends (the unmanaged M1 placement)."""
    start = np.asarray(ev_sessions["start"])
    return np.minimum(start + np.asarray(ev_sessions["hours"]), HOURS) - start


def spread_energy(home, first_hour, energy_kwh, power_kw):
    """Expand sessions into (home, hour, kW) rows: full power hours, then one last hour with what is left."""
    length = np.ceil(energy_kwh / power_kw - 1e-9).astype(np.int64)
    offset = np.arange(length.sum()) - np.repeat(np.cumsum(length) - length, length)
    kw = np.full(length.sum(), power_kw, dtype=np.float64)
    last = np.cumsum(length) - 1
    kw[last] = energy_kwh - (length - 1) * power_kw
    hour = (np.repeat(first_hour, length) + offset) % HOURS
    return np.repeat(home, length), hour, kw


def bin_by_transformer(home, hour, kw, owner, count):
    """kW by transformer and hour from (home, hour, kW) rows."""
    cell = owner[home] * HOURS + hour
    return np.bincount(cell, weights=kw, minlength=count * HOURS).reshape(count, HOURS)


def timer_loading(ev_sessions, owner, count, charger_kw, config):
    """Every session starts at the timer hour of its plug-in day, full power, same energy."""
    start_hour = config_value("shift.timer_start_hour", config)
    first = (np.asarray(ev_sessions["start"]) // 24) * 24 + start_hour
    energy = delivered_hours(ev_sessions) * charger_kw
    return bin_by_transformer(*spread_energy(ev_sessions["home"], first, energy, charger_kw), owner, count)


def stagger_slots(ev_homes, owner, window_hours):
    """Slot for each EV home: its rank among the EV homes on its transformer, round robin over the window."""
    homes = np.asarray(ev_homes)
    order = np.lexsort((homes, owner[homes]))
    ranked_owner = owner[homes][order]
    first_of_group = np.r_[0, np.flatnonzero(np.diff(ranked_owner)) + 1]
    group_start = np.repeat(first_of_group, np.diff(np.r_[first_of_group, len(homes)]))
    slots = np.empty(len(homes), dtype=np.int64)
    slots[order] = (np.arange(len(homes)) - group_start) % window_hours
    return dict(zip(homes.tolist(), slots.tolist()))


def staggered_loading(ev_sessions, ev_homes, owner, count, charger_kw, config):
    """Each EV starts in its own slot of the stagger window at reduced power until the same energy is in."""
    start_hour = config_value("shift.stagger_start_hour", config)
    window = (config_value("shift.stagger_end_hour", config) - start_hour) % 24
    power = config_value("shift.stagger_power_share", config) * charger_kw
    slot_of = stagger_slots(ev_homes, owner, window)
    slot = np.array([slot_of[h] for h in np.asarray(ev_sessions["home"]).tolist()], dtype=np.int64)
    first = (np.asarray(ev_sessions["start"]) // 24) * 24 + start_hour + slot
    energy = delivered_hours(ev_sessions) * charger_kw
    return bin_by_transformer(*spread_energy(ev_sessions["home"], first, energy, power), owner, count)


def ev_loading_by_mode(mode, parts, owner, count, config):
    """EV kW by transformer and hour for one charging mode; 'unmanaged' is the M1 loading unchanged."""
    charger_kw = config_value("scenarios.loads.ev_l2_kw", config)
    if mode == "unmanaged":
        return parts["ev"]
    if mode == "timer":
        return timer_loading(parts["ev_sessions"], owner, count, charger_kw, config)
    if mode == "staggered":
        return staggered_loading(parts["ev_sessions"], parts["ev_homes"], owner, count, charger_kw, config)
    raise ValueError(f"mode must be one of {EV_MODES}, not {mode}")
