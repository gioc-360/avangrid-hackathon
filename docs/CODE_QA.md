# Code questions a judge is likely to ask, answered from the code

Each answer cites the lines that do the work as `path:line anchor`. `checks/qa_refs.py docs/CODE_QA.md` opens
every one and fails if the file is missing, the lines are gone, or the anchor text is no longer on them, so a
judge who opens a reference lands on the code the answer describes. Every number here traces to
facts/facts.json or config/ewu.yaml (`checks/trace_numbers.py docs/CODE_QA.md`). Results are for the moderate
2030 scenario, random grouping, transformers rated at today's group peak times 1.15, unless a line says otherwise.

### Q1. How do you know which homes have an EV or a heat pump, with no equipment list?

Each class is one physical rule on the hourly load. A home is a Level 2 EV home when it shows repeated blocks
of high load above its own daily floor on weather-neutral days, mostly starting in the evening or at night. The
organizers' EV and heat pump lists are a random sample of owners, so the rules are scored against them as a
lower bound, not as accuracy: at least 28.9% of flagged Level 2 homes are listed owners, and a
positive-unlabeled model scores EV ownership at an AUC of 0.806 against the labels.

Code: `analysis/classify.py:109 F.ev_l2_night_share` (the rule), `analysis/classify.py:5-8 implied owners in a flagged group`
(how a positive-only label list is turned into a precision floor), `analysis/classify.py:63 def pu_scores` (the owner score).

### Q2. How does a home end up eligible for a program?

`ewu inventory` joins the equipment flags, segment and battery tier into one row per home, then applies each
program's rule from config: the home must have every flag the rule names and none of the excluded flags (vacant
or part-year homes). No rule is typed in Python, and a test changes a rule in config and sees eligibility move.
Across all 33,757 usable homes, 69.07% qualify for at least one program.

Code: `ewu/inventory.py:55 homes[needs].all`, `config/ewu.yaml:142 managed_charging:`,
`tests/test_inventory.py:51 def test_every_program_is_exactly_its_config_rule`,
`tests/test_inventory.py:62 def test_changing_a_config_rule_changes_eligibility`.

### Q3. There is no meter-to-transformer map. How do you know which homes share a transformer?

We do not; we simulate it and say so. `build_transformers` cuts the homes into groups of 8, either at random or
sorted by segment so neighbors are alike (the clustered case), and draws 3,000 groups per seed with no home in
two groups. The real map plugs in through `load_map`, which reads meter_id, transformer_id and kva and refuses a
meter listed under two transformers; `bin/ewu screen --map file.csv` runs the same ladder on it, with uneven
group sizes handled in batches.

Code: `ewu/feeders.py:26 def build_transformers`, `ewu/feeders.py:41 def load_map`,
`ewu/screen.py:28 def groups_by_size`, `ewu/cli.py:136 "--map"`,
`tests/test_screen.py:60 def test_a_real_map_with_uneven_transformers_runs`,
`tests/test_stress.py:76 def test_no_home_sits_in_two_transformers`.

### Q4. How big is each transformer, and what counts as overloaded?

Each rating is today's metered group peak times a sizing margin, and a transformer is overloaded in any hour
its load passes 1.2 times that rating. Sizing is the input we know least, so every result is run at margins of
1.05, 1.15, 1.30 and 1.50 and the headline is reported as a range; a test checks the overloaded share never rises
as the margin rises. Ratings are in kW at unity power factor, which the code labels as an assumption.

Code: `ewu/feeders.py:58-60 dtype=np.float64) * margin`, `ewu/stress.py:74-80 ceiling = (limit * np.asarray(rating_kw))`,
`config/ewu.yaml:43 sizing_margins:`, `config/ewu.yaml:48 overload_limit:`,
`tests/test_stress.py:94 def test_overloaded_share_never_rises_as_margin_rises`.

### Q5. Where does the 2030 load come from?

Adopters are drawn from homes that do not have the device today and are not vacant: 20% of homes add an EV and
15% a heat pump in the moderate scenario. Each new EV charges on the days and at the start hours and lengths
measured from real Level 2 sessions in this data, at 7.2 kW. Each new heat pump adds 0.05 kW for every degree
below the balance point, from the measured cold-weather slope. Transformer load is exactly today's load plus the
two adds, which a test checks. Both devices are drawn off one random order per seed, so 97.91% of new heat pump
homes also get a new EV. That stacking is a labeled assumption in config; with heat pump adopters drawn apart
(20.25% also get an EV), 25.28% of transformers overload instead of 26.18% and staggering fixes 83.83% of them
instead of 78.56%, so the answer does not rest on it.

Code: `ewu/adoption.py:39 def measure_ev_sessions`, `ewu/adoption.py:63 def pick_adopters`,
`ewu/adoption.py:71 adopters_share_one_order`, `config/ewu.yaml:34 adopters_share_one_order:`,
`ewu/adoption.py:103-107 def heat_pump_kw`, `ewu/stress.py:98 total = parts["base"] + parts["ev"] + parts["hp"]`,
`tests/test_stress.py:40 def test_loading_equals_base_plus_ev_plus_heat_pump_adds`.

### Q6. Your teammate says most overloads are heat pump nights, yet EV staggering fixes most of them. Which is it?

Both, once timing is separated from cause. Each overload hour's energy above the limit is split between the EV
and the heat pump by their effect averaged over both orders of arrival (a two-load Shapley value), after today's
load takes only what it would put over alone. Heat pumps are running in 90.52% of overload hours. In 76.0% of
them neither new load alone would cross the limit, so it takes both and the split gives them equal shares; the
EV is strictly the larger cause in 19.42% and the heat pump in 4.57%. What decides the program is that 95.38% of
overload hours stay under the limit with no new EV load, so moving EV charging fixes most overloads. Transformers
that overload on heat pumps alone, 1.97% of all transformers, cannot be fixed by any charging program. (An
earlier answer read the "EV at least as large" count, 95.43%, as "EV larger"; the number review caught it.)

Code: `ewu/attribution.py:35-42 def fair_shares`, `ewu/attribution.py:60 still_over = ((base + hp) > ceiling[:, None])`,
`ewu/attribution.py:61 needs_both = (base[t, h] + ev[t, h] <= limit)`,
`tests/test_attribution.py:44 def test_fair_split_adds_up_to_the_energy_above_the_limit`.

### Q7. What does staggered charging do, and does it lose any energy?

Each EV on a transformer gets its own start slot in the overnight window, ranked among that transformer's EVs
(round robin once a transformer has more EVs than hours in the window),
and charges at half power until the same energy is in. Half power halves the spike and separate slots stop two
cars stacking. The energy each session delivers is computed before it is moved, and a test checks that every
home gets the same energy in every mode. Staggering cuts overloaded transformers from 26.18% to 5.65%.

Code: `ewu/shift.py:60 def stagger_slots`, `ewu/shift.py:76 config_value("shift.stagger_power_share", config) * charger_kw`,
`ewu/shift.py:80 energy = delivered_hours(ev_sessions) * charger_kw`,
`tests/test_attribution.py:83 def test_shifting_moves_ev_energy_and_loses_none`,
`tests/test_attribution.py:114 def test_staggered_evs_on_one_transformer_start_in_different_slots`.

### Q8. Is the battery model physical, or does it just subtract kW?

It carries state of charge hour by hour. In each hour a battery discharges only the load above the limit, capped
by its continuous power, by the charge above its reserve floor, and by its own home's draw (no export to
neighbors, an assumption in config). It recharges only into room under the limit, capped by power and by free
capacity, and loses the round-trip efficiency on the way in. Two units store 20.16 kWh. Tests check charge stays
between floor and capacity, power stays within the challenge spec, and energy balances hour by hour.

Code: `ewu/dispatch.py:82 np.maximum(soc[i] - spec["floor_kwh"]`, `ewu/dispatch.py:84 np.maximum(host_kw[i][:, h]`,
`ewu/dispatch.py:89 room = np.maximum(ceiling_kw - load`, `ewu/dispatch.py:92 soc[i] += inn[i] * spec["efficiency"]`,
`tests/test_dispatch.py:64 def test_state_of_charge_stays_between_floor_and_capacity`,
`tests/test_dispatch.py:79 def test_energy_balance_holds_hour_by_hour_and_over_the_year`,
`tests/test_dispatch.py:91 def test_batteries_charge_only_under_the_limit_and_discharge_only_above`.

### Q9. Does a home battery last a long cold night?

`bin/ewu coldsnap` runs Feb 7-8, the coldest stretch in the data (coldest hour -5.0 F), with staggered charging.
The battery is dispatched over the whole year, so its charge on the first cold night is whatever earlier hours
left it, not assumed full. Of the 2.70% of transformers the cold snap pushes over the limit, one host home with two
battery units clears 89.88% and two such hosts clear 92.84%.

Code: `ewu/coldsnap.py:26 def window_hours`, `ewu/coldsnap.py:49 host_kw = dispatch.own_loading(inputs, parts, hosts.T.ravel(), owner, mode, config)`,
`ewu/coldsnap.py:58 result = dispatch.run_batteries`,
`tests/test_dispatch.py:146 def test_cold_snap_window_is_feb_7_to_8`,
`tests/test_dispatch.py:126 def test_zero_batteries_reproduce_the_m1_numbers`.

### Q10. How do you choose which homes get a battery?

By fit score: the kW a battery in that home could cut in the system's top hours of each season (Feb 7 and Jul 2
are in the set), capped by battery power, by the home's own load and by usable energy per day. On transformers
still over with staggered charging, one fit-score host with one unit clears 66.75% of them against 43.75% for a
random home on the same transformers, and a test requires fit score to win.

Code: `ewu/fitscore.py:32 def system_top_hours`, `ewu/fitscore.py:42-51 def fit_score`,
`ewu/fitscore.py:60 return np.argsort(-scores`,
`tests/test_fitscore.py:40 def test_named_peak_days_are_in_the_top_hour_set`,
`tests/test_fitscore.py:102 def test_fit_score_hosts_clear_more_per_battery_than_random_hosts`.

### Q11. A battery lasts 15 years and a transformer 30. How do you compare their cost?

On equal life: each capital cost becomes a yearly cost at a 7% discount rate, so the battery is bought again
within the transformer's life. Deferral value, what pushing the upgrade back by one battery life is worth, is
reported beside it and never exceeds the upgrade's price. The full ladder costs 51.92% of upgrading every flagged
transformer, from 30.8% to 151.19% across all 16 grid cells and price cases; at placeholder prices batteries tie
the upgrade only below $7,730 a unit, so shifting is where the money is. Every price is read from config.

Code: `ewu/economics.py:26 def capital_recovery_factor`, `ewu/economics.py:43 def deferral_value`,
`ewu/economics.py:63 def cost_the_ladder`, `ewu/economics.py:113 def headline_range`,
`tests/test_economics.py:27 def test_economics_types_no_price`,
`tests/test_economics.py:48 def test_equal_lives_at_zero_rate_give_the_plain_cost_ratio`,
`tests/test_economics.py:69 def test_deferral_value_never_exceeds_the_upgrade_cost`.

### Q12. How do I know a number on the page or in a doc was not typed by hand?

Every number goes through one door, `record()`, which writes it to facts/facts.json with its unit, the script
that made it and the method. `trace_numbers.py` fails a doc when a number matches no fact or config input at the
precision shown. `demo_check.py` renders the demo page in headless Chrome, binds every shown number to its key
and compares it with the stored value. `config_check.py` opens the source of every config input.

Code: `analysis/facts.py:18 def record(key, value`, `checks/trace_numbers.py:59 def matching_key`,
`checks/demo_check.py:102 def audit_dom`, `checks/config_check.py:83 def problem_with_source`.

### Q13. Where does customer data go?

Nowhere off this machine. Per-home and per-transformer values go through `record(..., private=True)` into
outputs/private/, which git ignores, and a test checks git really ignores it. Commands print aggregates only, and
a test checks the inventory printout holds no customer number. The demo page shows no real home: step 1 draws
Composite homes (segment averages) and the cold snap step draws fleet battery charge, never a host's own; a test
checks the page carries neither. The page is built locally and is gitignored.

Code: `analysis/facts.py:19 path = PRIVATE_FACTS if private else FACTS`, `.gitignore:21 outputs/private/`,
`ewu/coldsnap.py:167 private=True`, `tests/test_house_rules.py:82 def test_private_outputs_are_ignored_by_git`,
`tests/test_inventory.py:111 def test_printed_table_holds_aggregates_only`,
`tests/test_inventory.py:97 def test_demo_page_carries_no_single_home_and_no_host_charge`.

### Q14. Does it run fast enough to use live, and does it scale?

`bin/ewu screen` on the full meter data finishes in seconds. `demo_check.py` times it on every run, records the
time as `ewu.cli.screen_seconds` in facts, and fails at 60 s. Loading is
summed per transformer with one sparse matrix product per chunk of homes, and every later step works on arrays
of transformers by hours, so cost grows with the number of transformers, not with loops over homes.

Code: `checks/demo_check.py:132 def time_live_screen`, `checks/demo_check.py:187-188 checks.screen_seconds_max`,
`ewu/stress.py:35-44 out += pick @ rows`.

### Q15. Random groups change with the seed. How stable are the results?

Every random draw takes a seed, so a run is repeatable, and every grid result pools 5 seeds (the live screen
runs one of them). A test requires the seeds to agree on the overloaded share within 1.5 points in every cell;
the widest gap in any cell is 1.37 points. `make prototype`
rebuilds every output and the demo page from the processed data.

Code: `ewu/feeders.py:30 rng = np.random.default_rng((seed`, `config/ewu.yaml:177 seeds:`,
`tests/test_stress.py:115 def test_five_seeds_agree_within_tolerance`, `Makefile:35 prototype:`.
