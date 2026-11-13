"""Demo check: the offline demo page renders all 8 views, every number on it is a stored number, and the live
screen command answers on the full data in under a minute.

What: confirms outputs/demo/ewu_demo.html loads nothing from outside; renders it in headless Chrome in every
      scenario x overload limit, twice (cycling homes, Network ladder steps, an opened transformer); requires all
      8 views filled, Network states drawn equal to facts, no NaN, every shown number bound to its key and equal
      to it at the shown precision (checks/demo_audit.py judges each state); screenshots each view to
      outputs/private/demo_shots/; times `bin/ewu screen` (fails at the config limit), records
      ewu.cli.screen_seconds, writes docs/demo/cli_output.txt (deck run, then the cautious ladder the earlier film
      shows; the page itself carries deck-profile numbers only), where every number must trace. `--selftest`
      plants seven bad pages.
Why:  the demo is what judges see. A number typed into the page, a stale page after a rerun, a step that fails
      to draw or a link that needs the network would each break the promise that everything traces to code.
How:  checks/demo_audit.py reads the DOM Chrome dumps after the page's script runs; this module picks the states,
      takes the screenshots and times the live screen. Chrome runs with its own empty profile.
"""
import itertools, re, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks import trace_numbers
from checks.demo_audit import (CHROME, NET_VIEWS, OUTSIDE, STEPS, audit_dom, audit_raw, read_sources,   # noqa: F401
                               run_chrome, shown_equals)
from ewu import config_value
from ewu.demo_page import PAGE

SHOTS, CLI_OUTPUT = ROOT / "outputs" / "private" / "demo_shots", ROOT / "docs" / "demo" / "cli_output.txt"


def page_states(sources):
    """Every scenario x overload limit, twice, cycling homes, Network ladder steps and one transformer per state."""
    homes = int(sources.get("fact:ewu.demo.home_count") or 1)
    state = sources.get("private:ewu.deck.network.t.state") or []
    firsts = [state.index(k) for k in (0, 2, 3) if k in state] or [-1]
    cells = itertools.product(("moderate", "high"), range(len(config_value("profiles.deck.overload_limit_options"))), range(2))
    return [f"home={i % homes}&scenario={s}&limit={m}&net={NET_VIEWS[i % len(NET_VIEWS)]}"
            f"&t={firsts[(i // len(NET_VIEWS)) % len(firsts)]}" for i, (s, m, _) in enumerate(cells)]


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
