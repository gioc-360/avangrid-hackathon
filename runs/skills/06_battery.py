"""Part 3: BTM battery + demand flexibility.
Battery unit (challenge statement): Enphase IQ 10C, 10.08 kWh, 3.84 kW continuous per unit, 89.4% round trip; 1 or 2 units.
ASSUMPTIONS (labelled in REPORT.md): full 10.08 kWh usable; AC energy out per full cycle = 10.08 * sqrt(0.894);
no export (discharge never exceeds the home's own load) unless the 'export' variant is named; kW ~= kVA (pf 1).

Formulas
  coincident relief, event day d with system-top hours H_d:  r_h = min(L_h, P, E_ac / |H_d|)      (flat, energy-limited)
  CP relief (season) = mean of r_h over that season's 20 system-top hours
  own-peak shave: smallest T with, for every day, sum_h max(L_h - T, 0) <= E_ac and max_h (L_h - T) <= P  (binary search)
  daily shift 16:00-20:59: s_d = min( sum_h min(L_h, P), E_ac );  grid losses = s_d * (1/0.894 - 1)
  EV enablement test: add a 7.2 kW Level 2 charger for 2 hours/day; passes if new peak <= old peak + 3 kVA.
"""
import json, numpy as np, pandas as pd
OUT = '/Users/giocaballero/avangrid-hackathon/runs/skills/'
P_ = '/Users/giocaballero/avangrid-hackathon/data/processed/'
L = np.load(P_ + 'load_present.npy')
C = pd.read_parquet(OUT + 'classes.parquet'); S = pd.read_parquet(OUT + 'segments.parquet')
n = L.shape[0]
hours = pd.date_range('2025-09-01', periods=8760, freq='h'); hod = hours.hour.to_numpy()
RTE = 0.894; E1 = 10.08; P1 = 3.84
EAC = lambda u: u * E1 * np.sqrt(RTE)
sysload = np.load(P_ + 'sysload.npy')
pk = json.load(open(P_ + 'system_peaks.json'))
top = {s: np.array([hours.get_loc(pd.Timestamp(h)) for h in pk[f'top_{s}_hours']]) for s in ['winter', 'summer']}

def cp_relief(u, export=False):
    out = {}
    for s, idx in top.items():
        r = np.zeros((n, len(idx)), np.float32)
        day = idx // 24
        for d in np.unique(day):
            cols = np.where(day == d)[0]
            cap = min(P1 * u, EAC(u) / len(cols))
            r[:, cols] = cap if export else np.minimum(L[:, idx[cols]], cap)
        out[s] = r.mean(1)
    return out

def own_shave(u, X=None, target=None):
    """Return the lowest feasible threshold T (kW) per customer; if target given, return feasibility at that T."""
    X = L if X is None else X
    D = X.reshape(n, 365, 24); E, Pm = EAC(u), P1 * u
    def feas(T):
        ex = np.maximum(D - T[:, None, None], 0)
        return (ex.sum(2).max(1) <= E) & (ex.max((1, 2)) <= Pm)
    if target is not None:
        return feas(target)
    lo = np.zeros(n, np.float32); hi = X.max(1).astype(np.float32)
    for _ in range(18):
        mid = (lo + hi) / 2; f = feas(mid)
        hi = np.where(f, mid, hi); lo = np.where(f, lo, mid)
    return hi

R = pd.DataFrame({'CUSTOMER_NUMBER': C.CUSTOMER_NUMBER, 'seg': S.seg.values})
R['peak_kw'] = L.max(1)
for u in (1, 2):
    cp = cp_relief(u); R[f'cpw_{u}'] = cp['winter']; R[f'cps_{u}'] = cp['summer']
    R[f'shave_{u}'] = R.peak_kw - own_shave(u)
cpx = cp_relief(2, export=True)
D = L.reshape(n, 365, 24)
for u in (1, 2):
    s_d = np.minimum(np.minimum(D[:, :, 16:21], P1 * u).sum(2), EAC(u))
    R[f'shift_kwh_{u}'] = s_d.sum(1); R[f'loss_kwh_{u}'] = R[f'shift_kwh_{u}'] * (1 / RTE - 1)
# solar charging: days with >= 3 midday hours netted to zero (surplus exists), evening covered from stored solar
zero_mid = (D[:, :, 10:16] == 0).sum(2) >= 3
eve = np.minimum(np.minimum(D[:, :, 16:23], P1).sum(2), EAC(1))
R['solar_days'] = zero_mid.sum(1); R['solar_eve_kwh_1'] = np.where(zero_mid, eve, 0).sum(1)
# persistence: share of the 40 system-top hours in which the home sits in its own top 10% of hours
p90 = np.percentile(L, 90, axis=1)
allt = np.concatenate([top['winter'], top['summer']])
R['persist'] = (L[:, allt] >= p90[:, None]).mean(1)

# electrification enablement: 7.2 kW Level 2 for 2 h/day, unmanaged 18-19 h vs managed 01-02 h
alive = ~C.dead_meter.values; cand_ev = alive & ~C.ev_l2.values & ~C.ev_l1.values
add_un = np.zeros(24, np.float32); add_un[[18, 19]] = 7.2
add_mg = np.zeros(24, np.float32); add_mg[[1, 2]] = 7.2
old = R.peak_kw.to_numpy(np.float32); lim = old + 3.0
Xun = (D + add_un).reshape(n, -1); Xmg = (D + add_mg).reshape(n, -1)
R['ev_unmanaged_ok'] = Xun.max(1) <= lim
R['ev_managed_ok'] = Xmg.max(1) <= lim
R['ev_unmanaged_bat1_ok'] = own_shave(1, Xun, lim)
R['ev_unmanaged_bat2_ok'] = own_shave(2, Xun, lim)
del Xun, Xmg
ev_tab = pd.Series({k: int(R.loc[cand_ev, k].sum()) for k in ['ev_unmanaged_ok', 'ev_managed_ok', 'ev_unmanaged_bat1_ok', 'ev_unmanaged_bat2_ok']})
print('EV enablement among', int(cand_ev.sum()), 'homes with no EV signature:\n', ev_tab, '\n', (100 * ev_tab / cand_ev.sum()).round(1))

# sizing: second unit only if it adds >= 1.0 kW of coincident relief in the binding season (assumption)
R['cp1'] = np.maximum(R.cpw_1, R.cps_1); R['cp2'] = np.maximum(R.cpw_2, R.cps_2)
R['units'] = np.where(R.cp2 - R.cp1 >= 1.0, 2, 1)
R['cp_relief'] = np.where(R.units == 2, R.cp2, R.cp1)
R['shave'] = np.where(R.units == 2, R.shave_2, R.shave_1)
R['shift_kwh'] = np.where(R.units == 2, R.shift_kwh_2, R.shift_kwh_1)

# tiers (program segments)
cols = ['elec_heat', 'heat_pump', 'resistance_heat', 'ev_l2', 'ev_l1', 'solar', 'ac_central', 'pool', 'seasonal_home', 'dead_meter']
R[cols] = C[cols].values
R['cp_kw'] = C.cp_kw.values
cand = alive & (R.cp_kw >= 3.0) & (R.persist >= 0.5) & ~R.seasonal_home
R['tier'] = 'none'
R.loc[cand & (R.elec_heat | R.ev_l2), 'tier'] = 'T1 electrified peaker'
R.loc[(R.tier == 'none') & R.solar & alive, 'tier'] = 'T2 solar + storage'
R.loc[(R.tier == 'none') & cand & (R.ac_central | R.pool), 'tier'] = 'T3 summer peaker (DR first)'
R.loc[(R.tier == 'none') & cand, 'tier'] = 'T3 summer peaker (DR first)'
# ASSUMPTIONS for $: $100/kW-yr avoided capacity, $0.10/kWh peak/off-peak spread (both unverified placeholders)
CAP, SPREAD, FLAT = 100.0, 0.10, 0.20
R['value_cap_usd'] = R.cp_relief * CAP
R['value_tou_usd'] = R.shift_kwh * SPREAD - np.where(R.units == 2, R.loss_kwh_2, R.loss_kwh_1) * FLAT * 0  # losses priced off-peak below
R['loss_cost_usd'] = np.where(R.units == 2, R.loss_kwh_2, R.loss_kwh_1) * (FLAT - SPREAD / 2)
R['value_tou_usd'] = R.shift_kwh * SPREAD - R.loss_cost_usd
R['value_total_usd'] = R.value_cap_usd + R.value_tou_usd
R['value_per_unit'] = R.value_total_usd / R.units

g = R[R.tier != 'none'].groupby('tier')
T = pd.DataFrame({'homes': g.size(), 'units_2_pct': (100 * g.units.apply(lambda x: (x == 2).mean())).round(0),
    'med_cp_kw_now': g.cp_kw.median().round(2), 'med_cp_relief_kw': g.cp_relief.median().round(2),
    'sum_cp_relief_MW': (g.cp_relief.sum() / 1000).round(2), 'med_own_peak_shave_kw': g.shave.median().round(2),
    'med_shift_kwh_yr': g.shift_kwh.median().round(0), 'med_value_usd_yr': g.value_total_usd.median().round(0),
    'persist_med': g.persist.median().round(2)})
print(T.to_string())
T.to_csv(OUT + 'tiers.csv')

# whole-population view
sys_w = sysload[top['winter']].mean(); sys_s = sysload[top['summer']].mean()
print(f'system top-20 mean: winter {sys_w/1000:.1f} MW, summer {sys_s/1000:.1f} MW (25,653 homes)')
print('median home load at system peak: winter %.2f kW, summer %.2f kW' % (np.median(C.cp_winter_kw), np.median(C.cp_summer_kw)))
for u in (1, 2):
    print(f'{u} unit(s), no export: median CP relief winter {np.median(R[f"cpw_{u}"]):.2f} kW, summer {np.median(R[f"cps_{u}"]):.2f} kW; '
          f'P(power-limited) share = {(R[f"cpw_{u}"] >= 0.99*min(P1*u, EAC(u)/8)).mean():.2f}')
print('2 units WITH export: winter %.2f kW, summer %.2f kW per home' % (cpx['winter'].mean(), cpx['summer'].mean()))
print('share of homes where 2nd unit adds >= 1 kW CP relief: %.3f' % (R.units == 2).mean())
print('own-peak shave median: 1 unit %.2f kW, 2 units %.2f kW' % (R.shave_1.median(), R.shave_2.median()))
# supply curve: rank candidates by CP relief per unit installed
cands = R[R.tier != 'none'].sort_values('value_per_unit', ascending=False)
cands['cum_units'] = cands.units.cumsum(); cands['cum_cp_MW'] = cands.cp_relief.cumsum() / 1000
for k in [100, 500, 1000, 2000]:
    sub = cands[cands.cum_units <= k]
    print(f'first {k} units -> {len(sub)} homes, {sub.cp_relief.sum()/1000:.2f} MW coincident relief = '
          f'{100*sub.cp_relief.sum()/min(sys_w, sys_s):.2f}% of the smaller seasonal system peak')
R.to_parquet(OUT + 'battery.parquet')
cands.head(25)[['CUSTOMER_NUMBER', 'tier', 'units', 'cp_kw', 'cp_relief', 'shave', 'persist', 'value_total_usd']].round(2).to_csv(OUT + 'top25_candidates.csv', index=False)
