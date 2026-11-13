"""Charts (data-display rules: zero baselines where bars/areas, direct labels not legends, grey ghost context,
units on every axis, one colour per job, no gridlines beyond a faint ghost grid)."""
import json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUT = '/Users/giocaballero/avangrid-hackathon/runs/skills/'; P = '/Users/giocaballero/avangrid-hackathon/data/processed/'
plt.rcParams.update({'font.family': 'serif', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#888', 'axes.labelcolor': '#333', 'xtick.color': '#555', 'ytick.color': '#555'})
GHOST, INK, ACC, ACC2, ACC3 = '#cfcfcf', '#333333', '#b5462f', '#2f6db5', '#4f8a3a'
C = pd.read_parquet(OUT + 'classes.parquet'); B = pd.read_parquet(OUT + 'battery.parquet')
L = np.load(P + 'load_present.npy', mmap_mode='r'); n = len(C)
t = pd.read_parquet(P + 'weather.parquet').temp.to_numpy()
tday = t.reshape(365, 24).mean(1); daily = np.load(P + 'daily.npy')

# Fig 1: EV list - weather-neutral day hourly profile
neutral = (tday >= 55) & (tday <= 70)
D = np.asarray(L).reshape(n, 365, 24)[:, neutral, :].mean(1)
fig, ax = plt.subplots(figsize=(7, 3.6))
groups = [('All homes', np.ones(n, bool), GHOST, 3),
          ('EV-list homes the L2 rule flags', (C.lab_ev == 1) & C.ev_l2, ACC, 2),
          ('EV-list homes it does not flag', (C.lab_ev == 1) & ~C.ev_l2, ACC2, 2),
          ('Unlisted homes the rule flags', (C.lab_ev == 0) & C.ev_l2, INK, 1.2)]
for name, m, col, lw in groups:
    y = D[np.asarray(m)].mean(0); ax.plot(range(24), y, color=col, lw=lw)
    dy = {'EV-list homes the L2 rule flags': -0.12, 'Unlisted homes the rule flags': 0.08}.get(name, 0)
    ax.text(23.3, y[-1] + dy, f'{name} (n={int(np.sum(m)):,})', color=col, va='center', fontsize=8.5)
ax.set_xlim(0, 23); ax.set_ylim(0, None); ax.set_xticks([0, 6, 12, 18, 23])
ax.set_xlabel('hour of day (local)'); ax.set_ylabel('mean load (kWh per hour)')
ax.set_title('Weather-neutral days (55-70 F): 101 of 140 EV-list homes show no home Level 2 charging', loc='left', fontsize=10.5)
fig.savefig(OUT + 'fig1_ev_profiles.png', dpi=160, bbox_inches='tight'); plt.close(fig)

# Fig 2: temperature response, median daily kWh per 4 F bin
bins = np.arange(-4, 96, 4); mid = (bins[:-1] + bins[1:]) / 2; bi = np.digitize(tday, bins) - 1
fig, ax = plt.subplots(figsize=(7, 3.8))
sets = [('No electric heat', ~C.elec_heat & ~C.dead_meter, GHOST, 3), ('Heat-pump rule', C.heat_pump, ACC3, 2),
        ('Resistance rule', C.resistance_heat, ACC, 2), ('Utility HP list', C.lab_hp == 1, ACC2, 1.5)]
for name, m, col, lw in sets:
    med = np.median(daily[np.asarray(m)], axis=0)
    y = np.array([med[bi == k].mean() if (bi == k).sum() >= 2 else np.nan for k in range(len(mid))])
    ax.plot(mid, y, color=col, lw=lw, marker='o' if name == 'Utility HP list' else None, ms=3)
    j = np.where(~np.isnan(y))[0][0]; ax.text(mid[j] - 1, y[j], f'{name} (n={int(np.sum(m)):,})  ', color=col, ha='right', va='center', fontsize=8.5)
ax.set_xlim(-45, 95); ax.set_ylim(0, None); ax.set_xticks(range(0, 100, 20))
ax.set_xlabel('daily mean temperature (F)'); ax.set_ylabel('median daily use (kWh per day)')
ax.set_title('Electric-heat homes use ~4x more at 0 F; heat-pump and resistance curves barely differ', loc='left', fontsize=10.5)
fig.savefig(OUT + 'fig2_temp_response.png', dpi=160, bbox_inches='tight'); plt.close(fig)

# Fig 3: segment centroids, small multiples, kW, ghost of all homes
cent = np.load(OUT + 'seg_centroid_kw.npy'); prof = np.load(OUT + 'profiles72.npy'); seg = pd.read_parquet(OUT + 'segments.parquet').seg.values
segtab = pd.read_csv(OUT + 'segments.csv', index_col=0)
names = json.load(open(OUT + 'segment_names.json'))

fig, axs = plt.subplots(1, len(cent), figsize=(10, 3.2), sharey=True)
for s, ax in enumerate(axs):
    for k, (lab, col) in enumerate([('winter', ACC2), ('shoulder', '#999'), ('summer', ACC)]):
        for o in range(len(cent)):
            if o != s: ax.plot(range(24), cent[o, 24 * k:24 * k + 24], color=GHOST, lw=0.8)
        ax.plot(range(24), cent[s, 24 * k:24 * k + 24], color=col, lw=2)
        if s == 0: ax.text(23.5, cent[s, 24 * k + 23], lab, color=col, fontsize=8, va='center')
    ax.set_title(f"{names[str(s)]}\n{int(segtab.loc[s,'n']):,} homes, {segtab.loc[s,'share_pct']}%", fontsize=9.5, loc='left')
    ax.set_xticks([0, 12, 23]); ax.set_xlabel('hour'); ax.set_ylim(0, None)
axs[0].set_ylabel('mean load (kW)')
fig.suptitle('Load-shape segments (k-means, k chosen by silhouette); grey = the other segments', x=0.01, y=1.1, ha='left', fontsize=10.5)
fig.savefig(OUT + 'fig3_segments.png', dpi=160, bbox_inches='tight'); plt.close(fig)

# Fig 4: CDF of per-home coincident relief at the summer system peak: load, not battery size, is the limit
fig, ax = plt.subplots(figsize=(7, 3.8)); alive = ~C.dead_meter.values
for col_, name, colr in [('cps_1', '1 unit, no export', ACC2), ('cps_2', '2 units, no export', ACC)]:
    v = np.sort(B[col_].values[alive]); q = np.arange(1, len(v) + 1) / len(v)
    ax.plot(v, q, color=colr, lw=2); yq = 0.8 if '1 unit' in name else 0.3; k = int(yq * len(v))
    ax.text(v[k] + 0.15, yq, f'{name}: median {np.median(v):.2f} kW', color=colr, fontsize=8.5, va='center')
ax.axvline(3.63, color=INK, lw=1, ls='--'); ax.text(3.68, 0.08, '2 units allowed to export:\n3.63 kW every home (energy-limited)', fontsize=8.5, color=INK)
ax.set_xlim(0, 8); ax.set_ylim(0, 1); ax.set_xlabel('relief per home at the 20 summer system-peak hours (kW)')
ax.set_ylabel('share of homes at or below (fraction)')
ax.set_title('A battery can only offset the load a home has: the 2nd unit adds 0.5 kW at the median', loc='left', fontsize=10.5)
fig.savefig(OUT + 'fig4_battery_relief_cdf.png', dpi=160, bbox_inches='tight'); plt.close(fig)
print('charts written')
