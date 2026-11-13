"""Demo check: the offline demo page renders all 9 views, every number on it is a stored number, and the live
screen command answers on the full data in under a minute.

What: confirms outputs/demo/ewu_demo.html loads nothing from outside; renders it in headless Chrome in every
      scenario x grouping x sizing (cycling homes, hosts, Network ladder steps, an opened transformer); requires
      all 9 views filled, Network states drawn equal to facts, no NaN, every shown number bound to its key and
      equal to it at the shown precision; screenshots each view to outputs/private/demo_shots/; times `bin/ewu
      screen` (fails at the config limit), records ewu.cli.screen_seconds, writes docs/demo/cli_output.txt (deck
      run, then the cautious ladder), where every number must trace. `--selftest` plants seven bad pages.
Why:  the demo is what judges see. A number typed into the page, a stale page after a rerun, a step that fails
      to draw or a link that needs the network would each break the promise that everything traces to code.
How:  html.parser reads the DOM Chrome dumps after the page's script runs; numbers outside bound elements are found
      as checks/trace_numbers.py does; Chrome runs with its own empty profile, so the page never leaves this machine.
"""
import itertools, json, re, subprocess, sys, tempfile, time
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks import trace_numbers
from ewu import config_value, read_config
from ewu.demo_page import PAGE, collect_values, config_inputs, read_json

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOTS, CLI_OUTPUT = ROOT / "outputs" / "private" / "demo_shots", ROOT / "docs" / "demo" / "cli_output.txt"
OUTSIDE, BROKEN = re.compile(r"https?://|<link\b|@import|\bsrc\s*=|url\(", re.I), re.compile(r"\b(NaN|undefined|Infinity)\b")
STEPS = ("deck", "network", "overview", "inventory", "flag", "shift", "protect", "upgrade", "money")   # the side panel, in order
NET_VIEWS, MARKS = ("today", "flag", "shift", "protect", "upgrade"), ("polyline", "rect", "path", "circle", "line")


class RenderedPage(HTMLParser):
    """Bound numbers (key, index, text), free text, and per step: bound count, chart marks, 'not built'."""

    def __init__(self):
        super().__init__()
        self.bound, self.free, self.skip, self.open = [], [], 0, None
        self.section, self.steps, self.looks = None, {s: {"bound": 0, "marks": 0, "not_built": False} for s in STEPS}, {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "title"):
            self.skip += 1
        if tag == "section" and a.get("id") in self.steps:
            self.section = a["id"]
        if self.section and tag in MARKS:
            self.steps[self.section]["marks"] += 1
        if self.section == "network" and tag == "g" and "data-look" in a:
            self.looks[a["data-look"]] = self.looks.get(a["data-look"], 0) + 1
        if self.section and "notbuilt" in (a.get("class") or ""):
            self.steps[self.section]["not_built"] = True
        if "data-key" in a:
            self.open = [a["data-key"], int(a["data-index"]) if a.get("data-index") else None, ""]

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag in ("script", "style", "title"):
            self.skip -= 1
        if tag == "section":
            self.section = None
        if self.open and tag == "span":
            self.bound.append(tuple(self.open))
            if self.section:
                self.steps[self.section]["bound"] += 1
            self.open = None

    def handle_data(self, data):
        if not self.skip and self.open:
            self.open[2] += data
        elif not self.skip:
            self.free.append(data)


def read_sources(root=ROOT):
    facts, private = (read_json(root / p) for p in ("facts/facts.json", "outputs/private/facts_private.json"))
    return ({f"fact:{k}": v["value"] for k, v in facts.items()} | {f"private:{k}": v["value"] for k, v in private.items()}
            | {f"config:{k}": v for k, v in config_inputs(read_config()).items()})


def shown_equals(text, value):
    """True when `text` is `value` (or value x 100) rounded to the digits shown."""
    raw = text.replace(",", "").replace("$", "").strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", raw) or isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    shown, digits = float(raw), len(raw.split(".")[1]) if "." in raw else 0
    return any(abs(v - shown) <= 0.5 * 10 ** -digits + 1e-9 for v in (value, value * 100))


def audit_raw(raw, sources):
    """Problems in the page file itself: outside resources, and stored values that no longer match the source."""
    block = re.search(r'<script type="application/json" id="data">(.*?)</script>', raw, re.S)
    values = json.loads(block.group(1).replace("<\\/", "</"))["values"] if block else {}
    problems = [f"loads from outside: '{m.group(0)}'" for m in OUTSIDE.finditer(raw)] + ([] if block else ["no data block"])
    problems += [f"stale value {k}: page {v} vs source {sources.get(k)}" for k, v in values.items() if sources.get(k) != v]
    return problems


def audit_dom(dom, sources, net_view=None):
    """Problems in one rendered state: unfilled views, broken or unbound numbers, Network states unequal to facts."""
    page = RenderedPage()
    page.feed(dom)
    stored = {k.rsplit(".", 1)[1]: v for k, v in sources.items() if net_view and k.startswith(f"fact:ewu.network.{net_view}.") and v}
    problems = [] if page.looks == stored else [f"network {net_view}: drawn {page.looks} vs facts {stored}"]
    problems += [f"{s}: not built" if v["not_built"] else f"{s}: not filled ({v['bound']} numbers, {v['marks']} chart marks)"
                for s, v in page.steps.items() if v["not_built"] or not v["bound"] or not v["marks"]]
    text = "\n".join(page.free) + "\n" + "\n".join(t for _, _, t in page.bound)
    problems += [f"shows '{m.group(0)}'" for m in BROKEN.finditer(text)]
    problems += [f"unbound number {shown}" for _, shown, _, _ in trace_numbers.claimed_numbers("\n".join(page.free))]
    for key, index, shown in page.bound:
        value = sources.get(key)
        value = value[index] if index is not None and isinstance(value, list) and index < len(value) else value
        if not shown_equals(shown, value):
            problems.append(f"{key}{'' if index is None else f'[{index}]'} shows '{shown.strip()}', source holds {value}")
    return problems, len(page.bound)


def run_chrome(url, profile, *extra):
    args = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-sync",
            "--disable-extensions", "--disable-background-networking", "--disable-component-update", "--hide-scrollbars",
            f"--user-data-dir={profile}", "--virtual-time-budget=3000", *extra, url]
    return subprocess.run(args, capture_output=True, text=True, timeout=90).stdout


def page_states(sources):
    """Every scenario x grouping x sizing, cycling homes, hosts, Network ladder steps and one transformer per state."""
    homes, state = int(sources.get("fact:ewu.demo.home_count") or 1), sources.get("private:ewu.network.t.state") or []
    firsts = [state.index(k) for k in range(4) if k in state] or [-1]
    cells = itertools.product(("moderate", "high"), ("random", "same_segment"), range(len(config_value("transformer.sizing_margins"))))
    return [f"home={i % homes}&scenario={s}&grouping={g}&margin={m}&hosts={i % 2}&net={NET_VIEWS[i % len(NET_VIEWS)]}"
            f"&t={firsts[i % len(firsts)]}" for i, (s, g, m) in enumerate(cells)]


def time_live_screen():
    """Run the default deck screen (timed), then the cautious ladder the video films; return seconds and both outputs."""
    runs = []
    for args in ([], ["--profile", "cautious", "--scenario", config_value("demo.scenario"), "--margin", str(config_value("demo.margin"))]):
        started, run = time.time(), subprocess.run([str(ROOT / "bin/ewu"), "screen", *args], capture_output=True, text=True, timeout=600)
        if run.returncode:
            raise SystemExit(f"FAIL  bin/ewu screen exited {run.returncode}: {run.stderr[-400:]}")
        runs.append((time.time() - started, f"$ bin/ewu screen {' '.join(args)}".rstrip() + f"\n{run.stdout}"))
    return runs[0][0], "\n".join(text for _, text in runs)


def run_selftest():
    sources = {"config:transformer.overload_limit": 1.2, "fact:x.share_pct": 51.92}
    step = lambda s: f'<section id="{s}"><span class="n" data-key="fact:x.share_pct">51.92</span>% <svg><polyline/></svg></section>'
    payload = '<script type="application/json" id="data">{"values": {"fact:x.share_pct": 51.92}}</script>'
    clean = "".join(step(s) for s in STEPS) + payload
    plants = {"unbound number": clean.replace("% <svg>", "% of 42 homes <svg>", 1),
              "number unequal to its fact": clean.replace(">51.92<", ">51.29<", 1),
              "outside script": clean + '<script src="https://cdn.example/x.js"></script>',
              "NaN on the page": clean.replace("% <svg>", "% NaN <svg>", 1),
              "empty step": clean.replace(step("money"), '<section id="money"></section>'),
              "stale stored value": clean.replace('{"fact:x.share_pct": 51.92}', '{"fact:x.share_pct": 50.0}'),
              "step not built": clean.replace(step("protect"), '<section id="protect"><p class="notbuilt">not built</p></section>')}
    ok = not (found := audit_raw(clean, sources) + audit_dom(clean, sources)[0])
    print(f"{'PASS' if ok else 'FAIL'}  clean planted page has no problems {found}")
    for label, page in plants.items():
        caught = audit_raw(page, sources) + audit_dom(page, sources)[0]
        ok &= bool(caught)
        print(f"{'PASS' if caught else 'FAIL'}  caught {label}: {caught[:1]}")
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if run_selftest() else 1)
    if not PAGE.exists():
        sys.exit(f"FAIL  {PAGE.relative_to(ROOT)} not found; run bin/ewu demo --no-open")
    sources = read_sources()
    problems = [f"page: {p}" for p in audit_raw(PAGE.read_text(), sources)]
    states, numbers = page_states(sources), 0
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs" / "private") as profile:
        for state in states:
            found, count = audit_dom(run_chrome(f"{PAGE.as_uri()}#{state}", profile, "--dump-dom"), sources,
                                     re.search(r"net=(\w+)", state).group(1))
            problems += [f"{state}: {p}" for p in found]
            numbers += count
        SHOTS.mkdir(parents=True, exist_ok=True)
        for step in STEPS:
            run_chrome(f"{PAGE.as_uri()}#step={step}", profile, f"--screenshot={SHOTS / f'{step}.png'}",
                       "--window-size=1920,1080")
            problems += [] if (SHOTS / f"{step}.png").stat().st_size > 10_000 else [f"{step} screenshot is blank"]
    seconds, output = time_live_screen()
    from analysis.facts import record
    record("ewu.cli.screen_seconds", round(seconds, 1), "s", "wall clock of bin/ewu screen on the full data, from demo_check")
    limit = config_value("checks.screen_seconds_max")
    problems += [] if seconds < limit else [f"bin/ewu screen took {seconds:.1f} s, limit {limit} s"]
    CLI_OUTPUT.write_text(output)
    _, untraced = trace_numbers.trace_document(CLI_OUTPUT, trace_numbers.numeric_sources())
    problems += [f"cli output: {shown} at {where} traces to nothing" for where, shown, _ in untraced]
    print("".join(f"FAIL  {p}\n" for p in problems[:40]), end="")
    print(f"demo_check: {len(states)} rendered states, {numbers} bound numbers checked, {len(STEPS)} screenshots in "
          f"{SHOTS.relative_to(ROOT)}, live screen {seconds:.1f} s (limit {limit} s), {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
