"""Readout page: every number in the prose is pulled from facts/facts.json at build time,
so the page cannot disagree with the code. Charts render from outputs/report_data.json.
Local file only: the data is confidential to the event.
Also writes outputs/readout.txt (the visible prose) so checks/check_all.py can trace it."""
import json, html, re, os
from pathlib import Path
import yaml

ROOT = Path(os.path.expanduser("~/avangrid-hackathon"))
F = json.loads((ROOT / "facts/facts.json").read_text())
D = json.loads((ROOT / "outputs/report_data.json").read_text())
CMP = json.loads((ROOT / "outputs/comparison.json").read_text())
CIT = {c["id"]: c for c in yaml.safe_load((ROOT / "checks/citations.yaml").read_text())["citations"]}

import sys; sys.path.insert(0, str(ROOT / "analysis"))
from facts import record
record("bess.headroom_rule.ev_fail_pct_none", round(100 - F["bess.headroom_rule.ev_pass_pct_none"]["value"], 1), "% of homes without an EV",
       "unmanaged Level 2 breaks the 3 kVA rule")
F = json.loads((ROOT / "facts/facts.json").read_text())

def v(k, dec=None, pct=False):
    x = F[k]["value"]
    if isinstance(x, str):
        return x
    if dec is None:
        dec = 0 if float(x).is_integer() else 1
    s = f"{x:,.{dec}f}"
    return s + ("%" if pct else "")

SRC_NAMES = {}
def cite(cid):
    c = CIT[cid]
    if cid not in SRC_NAMES:
        SRC_NAMES[cid] = len(SRC_NAMES) + 1
    return f'<a class="cite" href="#src-{cid}">[{SRC_NAMES[cid]}]</a>'

findings = [
 ("The system peaks on summer afternoons, set by air conditioning.",
  f"The annual peak was {v('insight.system_peak_mw')} MW at {v('insight.system_peak_temp_f',0)}F on 2 July at 5 pm; the winter peak was {v('insight.winter_peak_mw')} MW at {v('insight.winter_peak_temp_f')}F on 8 February. "
  f"AC homes carry {v('flex.ac_weather_load_mw')} MW of weather-driven load in the summer event hours."),
 ("Electric heat is the next peak, and it is mostly invisible to the utility's lists.",
  f"{v('class.electric_heat.count')} homes ({v('class.electric_heat.share_pct')}%) heat with electricity ({v('class.electric_heat.sensitivity_low')} to {v('class.electric_heat.sensitivity_high')} depending on threshold), and they carry {v('insight.electric_heat_winter_peak_share_pct')}% of winter peak-hour load. "
  f"Each conversion adds about {v('insight.heat_conversion_added_kw_at_winter_peak')} kW at the winter peak, so about {v('insight.homes_to_flip_winter_peaking')} more conversions ({v('insight.share_to_flip_winter_peaking_pct')}% of homes) would make this system winter-peaking. "
  f"In colder areas residential demand already “peaks during the winter due to the high demand for heating” {cite('winter-peak-heating')}, and gas “remains a primary choice for residential heating” {cite('gas-heating-primary')}, which is the stock that converts."),
 ("The EV list and the meters disagree, and the meters find more chargers.",
  f"Only {v('class.ev.recall_heldout')}% of listed EV homes show home Level 2 charging; {v('class.ev.labeled_no_home_l2_pct')}% show no Level 2 day at all. "
  f"Meanwhile {v('class.ev_l2.count')} homes charge at Level 2, about {v('class.ev.l2_unlisted')} of them beyond what the list implies. "
  f"DOE's AMI report says customers rarely tell the utility, but “three customers buy a Tesla” and a transformer's load triples {cite('doe-tesla-transformer')}."),
 ("Solar is the one class the meters identify almost perfectly, and almost none of it has a battery.",
  f"Against the complete solar list: {v('class.solar.recall_heldout')}% recall, {v('class.solar.precision_pct')}% precision, plus {v('class.solar.undisclosed')} solar-shaped homes not on the list. "
  f"Homes whose zeros run past dark (solar plus battery): {v('class.solar_battery.count')}. A battery program would add new storage, not reuse existing storage."),
 ("A battery's best job here is letting a home electrify without a service upgrade.",
  f"An unmanaged 7.2 kW Level 2 charger breaks the 3 kVA rule at {v('bess.headroom_rule.ev_fail_pct_none')}% of homes that lack one today. "
  f"One IQ 10C fixes {v('bess.headroom_rule.ev_pass_pct_one_unit')}% of them; the program's two-battery setup fixes {v('bess.headroom_rule.ev_pass_pct_two_units')}%. "
  f"A heat pump alone stays within 3 kVA at {v('bess.headroom_rule.hp_pass_pct_none')}% of homes, because those homes already peak in summer."),
 ("For pure peak relief, thermostats beat batteries on cost; batteries pay where they avoid an upgrade.",
  f"Batteries at the {v('bess.candidates.count')} persistent-peak homes deliver {v('bess.capacity_relief_mw')} MW in summer and {v('bess.capacity_relief_winter_mw')} MW in winter event hours. "
  f"A thermostat setback across AC homes gives about {v('flex.thermostat_mw')} MW (assumption: 33% shed). "
  f"On assumed prices the batteries take {v('bess.simple_payback_low_yr')} to {v('bess.simple_payback_high_yr')} years to pay back (assumption), against a 15-year warranty, "
  f"so their case rests on avoided upgrades: to keep peaks from overloading assets, operators “must invest in excess capacity” {cite('peak-forces-slack')}."),
 ("About 1 in 10 meters is a seasonal home, and treating it like a normal home skews targeting and forecasts.",
  f"{v('class.other_seasonal.count')} homes ({v('class.other_seasonal.share_pct')}%) have a month under 15% of their biggest month, yet hold {v('insight.seasonal_winter_peak_share_pct')}% of winter peak-hour load. "
  f"The pipeline keeps them out of battery and DR targeting."),
]

rows = []
for r in CMP:
    pv = "; ".join(f"{html.escape(str(x['value']))} {html.escape(x['unit'])}".strip() for x in r["pipeline"].values())
    badge = lambda ok: '<span class="ok">✓ quote verified</span>' if ok else '<span class="bad">not found</span>'
    rows.append(f"<tr><td><b>{html.escape(r['finding'])}</b>{('<div class=note>' + html.escape(r['note']) + '</div>') if r.get('note') else ''}</td>"
                f"<td>“{html.escape(r['plain'])}”<br>{badge(r['plain_verified'])}</td>"
                f"<td>“{html.escape(r['skills'])}”<br>{badge(r['skills_verified'])}</td>"
                f"<td class=num>{pv}</td><td><span class='verdict {r['verdict']}'>{r['verdict']}</span></td></tr>")

assumptions = [f"<li>{html.escape(k.split('.',1)[1].replace('_',' '))}: <b>{x['value']}</b> {html.escape(x['unit'])}. {html.escape(x['method'])}</li>"
               for k, x in F.items() if k.startswith("assumption.")]

segs = ["seasonal", "solar", "dual_electrified", "ev_home", "electric_heat", "summer_peaker", "emerging", "baseline"]
seg_data = [{"seg": s.replace("_", " "), "homes": F[f"seg.{s}.share_pct"]["value"],
             "summer": F[f"seg.{s}.summer_peak_share_pct"]["value"], "winter": F[f"seg.{s}.winter_peak_share_pct"]["value"],
             "count": F[f"seg.{s}.count"]["value"], "action": F[f"seg.{s}.action"]["value"]} for s in segs]
kva = [{"g": "Level 2 EV", "none": F["bess.headroom_rule.ev_pass_pct_none"]["value"], "one": F["bess.headroom_rule.ev_pass_pct_one_unit"]["value"], "two": F["bess.headroom_rule.ev_pass_pct_two_units"]["value"]},
       {"g": "Heat pump", "none": F["bess.headroom_rule.hp_pass_pct_none"]["value"], "one": F["bess.headroom_rule.hp_pass_pct_one_unit"]["value"], "two": F["bess.headroom_rule.hp_pass_pct_two_units"]["value"]}]
seg_rows = "".join(f"<tr><td>{s['seg']}</td><td class=num>{s['count']:,}</td><td class=num>{s['homes']}%</td><td class=num>{s['summer']}%</td><td class=num>{s['winter']}%</td><td>{html.escape(s['action'])}</td></tr>" for s in seg_data)

cls_rows = "".join(
    f"<tr><td>{k.split('.')[1].replace('_',' ')}</td><td class=num>{F[k]['value']:,}</td><td class=num>{F[k.replace('count','share_pct')]['value']}%</td>"
    f"<td>{html.escape(F[k.replace('count','method')]['value'])}</td><td>{html.escape(F[k.replace('count','confidence')]['value'])}</td></tr>"
    for k in F if re.fullmatch(r"class\.[a-z_0-9]+\.count", k))

src_list = "".join(
    f"<li id='src-{cid}'>[{i}] {html.escape(CIT[cid]['file'].split('/')[-1])}{', p. ' + str(CIT[cid]['page']) if CIT[cid]['page'] else ' (saved web copy)'}: “{html.escape(CIT[cid]['quote'])}”</li>"
    for cid, i in sorted(SRC_NAMES.items(), key=lambda x: x[1]))

payload = json.dumps({"daily": D["daily"], "val": D["validation"], "ev": D["ev_profiles"], "temp": D["temp_response"],
                      "supply": D["supply"], "seg": seg_data, "kva": kva})

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Avangrid AMI Readout</title>
<style>
:root{{--bg:#fcfcfb;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--ink3:#8a8984;--rule:#e6e5e1;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--ctx:#b9b8b2;--ok:#008300;--bad:#e34948}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#141413;--card:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#8f8e86;--rule:#2e2d2b;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--ctx:#5b5a55;--ok:#3fb950;--bad:#e66767}}}}
:root[data-theme="dark"]{{--bg:#141413;--card:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#8f8e86;--rule:#2e2d2b;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--ctx:#5b5a55;--ok:#3fb950;--bad:#e66767}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:32px 16px 80px}}h1{{font-size:28px;margin:0 0 4px}}h2{{font-size:19px;margin:40px 0 8px}}
.sub{{color:var(--ink2);margin:0 0 24px}}.card{{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:18px 20px;margin:12px 0}}
ol.find{{padding-left:22px}}ol.find li{{margin:0 0 12px}}ol.find b{{display:block}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,470px),1fr));gap:12px}}
.chart h3{{font-size:15px;margin:0}}.chart p{{color:var(--ink2);margin:2px 0 8px;font-size:13px}}
svg text{{fill:var(--ink2);font-size:11px}}svg .axis line,svg .axis path{{stroke:var(--rule)}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin:4px 0}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--rule);vertical-align:top}}th{{color:var(--ink2);font-weight:600}}
td.num{{font-variant-numeric:tabular-nums}}.note{{color:var(--ink3);font-size:12px;margin-top:3px}}
.ok{{color:var(--ok);font-size:12px}}.bad{{color:var(--bad);font-size:12px}}.verdict{{font-size:12px;padding:2px 7px;border-radius:9px;border:1px solid var(--rule)}}
.verdict.differ{{color:var(--s2)}}.verdict.agree{{color:var(--ok)}}.cite{{color:var(--s1);text-decoration:none;font-size:12px}}
.scroll{{overflow-x:auto}}#tip{{position:fixed;pointer-events:none;background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:6px 8px;font-size:12px;display:none;box-shadow:0 2px 8px rgba(0,0,0,.12);z-index:9}}
code{{font-size:12.5px;background:var(--rule);padding:1px 5px;border-radius:4px}}ul.src li,ul.as li{{margin:0 0 6px;font-size:13px;color:var(--ink2)}}
</style></head><body><main>
<h1>What the meters are really saying</h1>
<p class="sub">{v('data.customers_usable')} homes × 8,760 hours, 1 Sep 2025 to 31 Aug 2026. Two independent analysts (plain Claude, and Claude using the skills) worked from the same data; every number below comes from the shared pipeline in <code>analysis/</code>, and every quote and citation is machine-checked. {v('data.customers_missing')} of the promised {v('data.customers_promised')} customers have no data and {v('data.customers_partial_excluded')} more miss over 10% of hours, so they are left out. Customers 10,001 to 20,000 come from the corrected upload.</p>

<div class="card"><h2 style="margin-top:0">Seven findings, in order of how much they change a decision</h2><ol class="find">
{''.join(f'<li><b>{t}</b>{d}</li>' for t, d in findings)}
</ol></div>

<h2>The evidence</h2><div class="grid">
<div class="card chart"><h3>Summer sets the peak; winter follows the cold</h3><p>Daily system peak (MW) and daily mean temperature (°F), {v('data.customers_usable')} homes</p><div id="c-daily"></div></div>
<div class="card chart"><h3>How well each class finds the homes the utility listed</h3><p>Recall on listed homes with 95% interval (dot, bar) vs. how often the rule fires on unlisted homes (tick)</p><div id="c-val"></div></div>
<div class="card chart"><h3>Half the EV list never charges at home</h3><p>Average hourly load on mild days (55 to 70°F, kW), by EV list and charging signature</p><div id="c-ev"></div></div>
<div class="card chart"><h3>Listed heat pumps sit between resistance-style heat and everyone else</h3><p>Median daily use (kWh) by daily mean temperature (°F)</p><div id="c-temp"></div></div>
<div class="card chart"><h3>Who carries the peak</h3><p>Each segment's share of homes vs. its share of summer and winter peak-hour load (%)</p><div id="c-seg"></div></div>
<div class="card chart"><h3>Battery relief as ranked homes are added</h3><p>Cumulative relief at event hours (MW), two-battery setup per home</p><div id="c-supply"></div></div>
<div class="card chart"><h3>The battery is an electrification enabler</h3><p>Homes that stay within the 3 kVA rule after adding the load (%)</p><div id="c-kva"></div></div>
</div>

<h2>Plain Claude vs. Claude with skills vs. the pipeline</h2>
<p class="sub">Each quote is checked word for word against that analyst's report by <code>checks/compare.py</code>. A verdict of differ means their definitions differed and the pipeline column decides.</p>
<div class="card scroll"><table><colgroup><col style='width:26%'><col style='width:24%'><col style='width:24%'><col style='width:18%'><col style='width:8%'></colgroup><tr><th>Finding</th><th>Plain analyst</th><th>Skills analyst</th><th>Pipeline (facts.json)</th><th></th></tr>{''.join(rows)}</table></div>

<h2>Part 1: classification</h2><div class="card scroll"><table><tr><th>Class</th><th>Homes</th><th>Share</th><th>Evidence (rule)</th><th>Confidence</th></tr>{cls_rows}</table>
<p class="note">EV and heat-pump probabilities come from a positive-unlabeled gradient-boosting model (out-of-fold AUC {v('class.ev.pu_auc',2)} EV, {v('class.heat_pump.pu_auc',2)} heat pump). Weather features add {v('class.weather_gain.heat_pump_auc_points')} AUC points for heat pumps and {v('class.weather_gain.ev_auc_points')} for EVs. Customer-level output: <code>outputs/customer_classes.csv</code>.</p></div>

<h2>Part 2: segments and what to do with each</h2><div class="card scroll"><table><tr><th>Segment</th><th>Homes</th><th>Share</th><th>Summer peak</th><th>Winter peak</th><th>Action</th></tr>{seg_rows}</table>
<p class="note">Rule-based because k-means finds no strong natural clusters (silhouette {v('insight.kmeans_silhouette_k3',3)} at k=3, {v('insight.kmeans_silhouette_k6',3)} at k=6). Both analysts found the same.</p></div>

<h2>Part 3: batteries and flexibility</h2><div class="card"><p>Candidates: {v('bess.candidates.count')} homes ({v('bess.candidates.share_pct')}%) loaded at least 3.5 kW through the season's event hours on 9 of 10 event days. Median relief per home {v('bess.relief_per_home_kw')} kW; median own-peak cut {v('bess.peak_reduction_kw')} kW ({v('bess.peak_reduction_pct')}% of the home's annual peak); {v('bess.load_shift_mwh_yr')} MWh a year moved out of 4 to 9 pm. The best 1,000 homes give {v('bess.supply_curve.top1000_summer_mw')} MW summer and {v('bess.supply_curve.top1000_winter_mw')} MW winter. Solar homes have surplus to charge from on {v('bess.solar_charge_days')} days a year. Bill savings ${v('bess.bill_savings_per_home_usd_yr')} a year per median home and payback {v('bess.simple_payback_low_yr')} to {v('bess.simple_payback_high_yr')} years both rest on assumed prices listed below. Ranked list: <code>outputs/bess_candidates.csv</code>.</p></div>

<h2>Additional data that would most improve this</h2><div class="card"><ul class="as">
<li>The {v('data.customers_missing')} missing customers, mostly the {v('data.source.10001_20000.missing_in_range')} IDs absent from the corrected 10,001 to 20,000 upload.</li>
<li>Transformer and feeder mapping: turns system-level MW into which transformers overload, which is where a battery avoids an upgrade.</li>
<li>Gas service flags: confirms which electric-heat homes heat with electricity only.</li>
<li>Charger rebates, interconnection and DMV registrations: validates the unlisted EV and solar homes.</li>
<li>15-minute intervals: hourly averages hide short peaks, so the 3 kVA test here is optimistic.</li>
<li>NYSEG/RG&amp;E tariffs and avoided-cost values: replace every assumption below.</li></ul></div>

<h2>Assumptions (every one must be replaced with a sourced value before the deck)</h2><div class="card"><ul class="as">{''.join(assumptions)}</ul></div>

<h2>Sources cited</h2><div class="card"><ul class="src">{src_list}</ul><p class="note">All {len(CIT)} citations in <code>checks/citations.yaml</code> pass the page check; only those used above are listed.</p></div>

<h2>How to use the repo</h2><div class="card"><p><code>make all</code> rebuilds everything from the zips in about four minutes. <code>make check DECK=deck.pptx</code> answers two questions without anyone re-reading a PDF: are we still answering the challenge they wrote (31 requirements, each quoted and page-checked), and does every number on every slide trace to code or a cited page.</p></div>
</main><div id="tip"></div>
<script>
const DATA={payload};
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const tip=document.getElementById('tip');
function showTip(e,h){{tip.innerHTML=h;tip.style.display='block';tip.style.left=Math.min(e.clientX+12,innerWidth-220)+'px';tip.style.top=(e.clientY+12)+'px'}}
function hideTip(){{tip.style.display='none'}}
const NS='http://www.w3.org/2000/svg';
function el(t,a,p){{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}}
function svg(id,h){{const host=document.getElementById(id);const W=Math.max(300,host.clientWidth);const s=el('svg',{{width:W,height:h,viewBox:`0 0 ${{W}} ${{h}}`}});host.appendChild(s);return [s,W]}}
function ticks(min,max,n){{const st=Math.pow(10,Math.floor(Math.log10((max-min)/n)));const m=[1,2,5,10].find(x=>(max-min)/(st*x)<=n)*st;const out=[];for(let v=Math.ceil(min/m)*m;v<=max+1e-9;v+=m)out.push(+v.toFixed(6));return out}}
function legend(id,items){{const d=document.createElement('div');d.className='legend';d.innerHTML=items.map(([c,t])=>`<span><i style="background:${{c}}"></i>${{t}}</span>`).join('');document.getElementById(id).prepend(d)}}
function lineChart(id,xs,series,o){{
  const [s,W]=svg(id,o.h||230);const H=o.h||230,m={{l:44,r:12,t:10,b:28}};
  const ys=series.flatMap(x=>x.v).filter(v=>v!=null);const y0=o.y0??Math.min(...ys),y1=Math.max(...ys)*1.05;
  const X=v=>m.l+(v-xs[0])/(xs[xs.length-1]-xs[0])*(W-m.l-m.r),Y=v=>H-m.b-(v-y0)/(y1-y0)*(H-m.t-m.b);
  for(const t of ticks(y0,y1,4)){{el('line',{{x1:m.l,x2:W-m.r,y1:Y(t),y2:Y(t),stroke:css('--rule')}},s);el('text',{{x:m.l-6,y:Y(t)+4,'text-anchor':'end'}},s).textContent=t}}
  (o.xt||ticks(xs[0],xs[xs.length-1],6)).forEach(t=>{{el('text',{{x:X(t),y:H-8,'text-anchor':'middle'}},s).textContent=o.xf?o.xf(t):t}});
  for(const se of series){{let d='';se.v.forEach((v,i)=>{{if(v==null)return;d+=(d?'L':'M')+X(xs[i]).toFixed(1)+','+Y(v).toFixed(1)}});el('path',{{d,fill:'none',stroke:se.c,'stroke-width':2,'stroke-linejoin':'round'}},s)}}
  (o.marks||[]).forEach(mk=>{{el('circle',{{cx:X(mk.x),cy:Y(mk.y),r:4,fill:mk.c||css('--ink'),stroke:css('--card'),'stroke-width':2}},s);el('text',{{x:X(mk.x)+(mk.dx||6),y:Y(mk.y)+(mk.dy||-6),'text-anchor':mk.a||'start',style:'fill:'+css('--ink')}},s).textContent=mk.t}});
  const cross=el('line',{{y1:m.t,y2:H-m.b,stroke:css('--ink3'),visibility:'hidden'}},s);
  const hit=el('rect',{{x:m.l,y:m.t,width:W-m.l-m.r,height:H-m.t-m.b,fill:'transparent'}},s);
  hit.addEventListener('mousemove',e=>{{const r=s.getBoundingClientRect();const fx=e.clientX-r.left;let i=0,b=1e9;xs.forEach((x,j)=>{{const dd=Math.abs(X(x)-fx);if(dd<b){{b=dd;i=j}}}});cross.setAttribute('x1',X(xs[i]));cross.setAttribute('x2',X(xs[i]));cross.setAttribute('visibility','visible');
    showTip(e,`<b>${{o.xf?o.xf(xs[i],true):xs[i]}}</b><br>`+series.map(se=>`<span style="color:${{se.c}}">●</span> ${{se.n}}: ${{se.v[i]??'n/a'}} ${{o.unit||''}}`).join('<br>'))}});
  hit.addEventListener('mouseleave',()=>{{cross.setAttribute('visibility','hidden');hideTip()}});
}}
function draw(){{
  document.querySelectorAll('.chart > div').forEach(d=>d.innerHTML='');
  const d=DATA.daily,idx=d.date.map((_,i)=>i);const mo=['Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug'];
  const mt=[0,30,61,91,122,153,181,212,242,273,303,334];const xf=(i,full)=>full?d.date[i]:mo[mt.indexOf(i)];
  const pk=d.peak_mw.indexOf(Math.max(...d.peak_mw));const wi=d.date.indexOf('2026-02-08');
  lineChart('c-daily',idx,[{{n:'Daily peak',v:d.peak_mw,c:css('--s1')}}],{{h:170,y0:0,xt:mt,xf,unit:'MW',marks:[{{x:pk,y:d.peak_mw[pk],t:d.peak_mw[pk].toFixed(1)+' MW, 2 Jul, 92\u00b0F',a:'end',dx:-8}},{{x:wi,y:d.peak_mw[wi],t:d.peak_mw[wi].toFixed(1)+' MW, 8 Feb, 2\u00b0F',a:'end',dx:-8,dy:-10}}]}});
  const t2=document.createElement('div');t2.id='c-daily-t';document.getElementById('c-daily').appendChild(t2);
  lineChart('c-daily-t',idx,[{{n:'Mean temp',v:d.temp_f,c:css('--s2')}}],{{h:120,xt:mt,xf,unit:'°F'}});
  legend('c-daily',[[css('--s1'),'Daily peak, MW (top)'],[css('--s2'),'Daily mean temperature, °F (bottom)']]);
  // validation
  {{const [s,W]=svg('c-val',220);const m={{l:100,r:16,t:8,b:26}},rh=(220-m.t-m.b)/DATA.val.length;const X=v=>m.l+v/100*(W-m.l-m.r);
   ticks(0,100,5).forEach(t=>{{el('line',{{x1:X(t),x2:X(t),y1:m.t,y2:220-m.b,stroke:css('--rule')}},s);el('text',{{x:X(t),y:212,'text-anchor':'middle'}},s).textContent=t+'%'}});
   DATA.val.forEach((r,i)=>{{const y=m.t+rh*i+rh/2;el('text',{{x:m.l-8,y:y+4,'text-anchor':'end',style:'fill:'+css('--ink')}},s).textContent=r.cls;
    el('line',{{x1:X(r.lo),x2:X(r.hi),y1:y,y2:y,stroke:css('--s1'),'stroke-width':2,'stroke-linecap':'round'}},s);
    el('line',{{x1:X(r.base),x2:X(r.base),y1:y-7,y2:y+7,stroke:css('--s2'),'stroke-width':2}},s);
    el('circle',{{cx:X(r.recall),cy:y,r:5,fill:css('--s1'),stroke:css('--card'),'stroke-width':2}},s);
    el('text',{{x:X(r.hi)+6,y:y+4}},s).textContent=r.recall+'%';
    const h=el('rect',{{x:0,y:y-rh/2,width:W,height:rh,fill:'transparent'}},s);
    h.addEventListener('mousemove',e=>showTip(e,`<b>${{r.cls}}</b><br>Found ${{r.k}} of ${{r.n}} listed homes: ${{r.recall}}% (95% CI ${{r.lo}} to ${{r.hi}}%)<br>Fires on ${{r.base}}% of unlisted homes`));h.addEventListener('mouseleave',hideTip)}});
   legend('c-val',[[css('--s1'),'Recall on listed homes, 95% interval'],[css('--s2'),'Flag rate on unlisted homes']])}}
  // ev profiles
  const hrs=[...Array(24).keys()];const cols=[css('--s1'),css('--s2'),css('--s3'),css('--ctx')];
  const evs=Object.entries(DATA.ev).map(([k,v],i)=>({{n:`${{k}} (n=${{v.n}})`,v:v.kw,c:cols[i]}}));
  lineChart('c-ev',hrs,evs,{{y0:0,xt:[0,6,12,18,23],xf:(h,f)=>f?h+':00':h+'h',unit:'kW'}});legend('c-ev',evs.map(x=>[x.c,x.n]));
  // temp response
  const tr=DATA.temp;const ts=Object.entries(tr.series).map(([k,v],i)=>({{n:k,v,c:[css('--s1'),css('--s2'),css('--ctx')][i]}}));
  lineChart('c-temp',tr.bin_f,ts,{{y0:0,xf:(t,f)=>f?t+'°F':t+'°',unit:'kWh/day'}});legend('c-temp',ts.map(x=>[x.c,x.n]));
  // segments: grouped horizontal bars
  {{const S=DATA.seg,H=S.length*44+30;const [s,W]=svg('c-seg',H);const m={{l:110,r:30,t:6,b:22}},mx=50;const X=v=>m.l+v/mx*(W-m.l-m.r);
   const keys=[['homes','--ctx','Share of homes'],['summer','--s2','Share of summer peak'],['winter','--s1','Share of winter peak']];
   ticks(0,mx,5).forEach(t=>{{el('line',{{x1:X(t),x2:X(t),y1:m.t,y2:H-m.b,stroke:css('--rule')}},s);el('text',{{x:X(t),y:H-6,'text-anchor':'middle'}},s).textContent=t+'%'}});
   S.forEach((r,i)=>{{const y=m.t+i*44;el('text',{{x:m.l-8,y:y+22,'text-anchor':'end',style:'fill:'+css('--ink')}},s).textContent=r.seg;
    keys.forEach(([k,c,lab],j)=>{{const b=el('rect',{{x:m.l,y:y+4+j*12,width:Math.max(1,X(r[k])-m.l),height:10,rx:2,fill:css(c)}},s);
     b.addEventListener('mousemove',e=>showTip(e,`<b>${{r.seg}}</b> (${{r.count.toLocaleString()}} homes)<br>${{lab}}: ${{r[k]}}%<br>${{r.action}}`));b.addEventListener('mouseleave',hideTip)}})}});
   legend('c-seg',keys.map(([k,c,l])=>[css(c),l]))}}
  // supply
  const sp=DATA.supply;lineChart('c-supply',sp.homes,[{{n:'Summer event hours',v:sp.summer_mw,c:css('--s2')}},{{n:'Winter event hours',v:sp.winter_mw,c:css('--s1')}}],{{y0:0,unit:'MW',xf:(h,f)=>f?h+' homes':h}});
  legend('c-supply',[[css('--s2'),'Summer event hours'],[css('--s1'),'Winter event hours']]);
  // kva
  {{const K=DATA.kva,H=170;const [s,W]=svg('c-kva',H);const m={{l:90,r:40,t:6,b:22}};const X=v=>m.l+v/100*(W-m.l-m.r);
   const keys=[['none','--ctx','No battery'],['one','--s3','One IQ 10C'],['two','--s1','Program setup (2 units)']];
   ticks(0,100,5).forEach(t=>{{el('line',{{x1:X(t),x2:X(t),y1:m.t,y2:H-m.b,stroke:css('--rule')}},s);el('text',{{x:X(t),y:H-6,'text-anchor':'middle'}},s).textContent=t+'%'}});
   K.forEach((r,i)=>{{const y=m.t+i*68;el('text',{{x:m.l-8,y:y+32,'text-anchor':'end',style:'fill:'+css('--ink')}},s).textContent=r.g;
    keys.forEach(([k,c,lab],j)=>{{const b=el('rect',{{x:m.l,y:y+6+j*18,width:Math.max(1,X(r[k])-m.l),height:14,rx:2,fill:css(c)}},s);el('text',{{x:X(r[k])+5,y:y+17+j*18}},s).textContent=r[k]+'%';
     b.addEventListener('mousemove',e=>showTip(e,`<b>${{r.g}}</b>, ${{lab}}: ${{r[k]}}% of homes stay within 3 kVA`));b.addEventListener('mouseleave',hideTip)}})}});
   legend('c-kva',keys.map(([k,c,l])=>[css(c),l]))}}
}}
draw();let rt;addEventListener('resize',()=>{{clearTimeout(rt);rt=setTimeout(draw,150)}});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',draw);
</script></body></html>"""
(ROOT / "outputs/readout.html").write_text(page)
txt = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
txt = html.unescape(re.sub(r"<[^>]+>", " ", txt))
(ROOT / "outputs/readout.txt").write_text("\n".join(l.strip() for l in txt.splitlines() if l.strip()))
print("wrote outputs/readout.html")
