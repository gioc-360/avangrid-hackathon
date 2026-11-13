# Demo video script (for the teammate's voice)

About two and a half minutes at an easy reading pace. Numbers and terms are deck v3's.

| # | Time | On screen | Say |
|---|---|---|---|
| 1 | 0:00-0:12 | Summary view | Every home in New York that adds an EV or a heat pump puts more load on the transformer outside. Avangrid needs to know which transformers will overload before they do. |
| 2 | 0:12-0:25 | Network view, Today | This is the tool we built for the distribution planner. Each mark is one transformer serving eight real homes, built from the hourly meter data Avangrid already collects. |
| 3 | 0:25-0:36 | Network view, Synthetic network tag | The data came without a transformer map, so the network is simulated from real homes. Load Avangrid's map, and the same model runs on the real grid. |
| 4 | 0:36-0:55 | Click 2030: Flag | Now jump to 2030, when 20% of homes have added an EV and 15% a heat pump. In the moderate case, 292 of 3,000 transformers go over their limit, most of them on winter nights when heat pumps run hardest. |
| 5 | 0:52-1:09 | Click Place (batteries) | The cheapest fix comes first. For each overloaded transformer, our model works out how many leased battery units it needs on its worst day, one to four, placed in priority homes behind it. |
| 6 | 1:07-1:20 | Click Upgrade | Only 5 transformers are left that batteries cannot fix. That is the only place a new transformer is needed. Across both scenarios, batteries fix 92% to 98% of overloaded transformers. |
| 7 | 1:20-1:33 | Click one transformer: its worst day | Click any transformer and the planner sees why: its load hour by hour against its limit, and how much the battery units must cover on its worst day. |
| 8 | 1:33-1:50 | Money view | Across NYSEG, that is a net cost of $34M instead of $111M in the moderate case, after lease payments and NYSERDA incentives: 58% to 69% less than upgrading every overloaded transformer. |
| 9 | 1:50-2:05 | Terminal: bin/ewu screen runs live | And this is not a slide. Our model runs on all 33,757 homes in seconds, and every number on screen is written by the code, never typed. A check fails if one does not match. |
| 10 | 2:05-2:18 | Back to the Network view, Upgrade | So the planner gets one list: which transformers will overload, where to place batteries, and the few that need an upgrade. Customers electrify sooner, without waiting for a new transformer. |
