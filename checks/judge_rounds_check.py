"""Judge rounds check: runs/judge_rounds.json holds complete, self-consistent judge rounds, and the review is recorded.

What: `--round N` passes when round N has all 9 judge seats, exactly one held out, every criterion scored 1
      to 5, each weighted score equal to the rubric weights applied to its scores, each per-criterion gap to
      the A1 anchor equal to score minus anchor, and the round averages equal to the judges' numbers.
      Round 2 must also state the held-out judge's change from round 1. `--review` passes when
      runs/review_round.json holds 10 number checks and 10 examiner answers with at least 9 passing.
      `--selftest` plants one bad case of each kind and fails unless every one is caught.
Why:  the plan's stop rule and morning report read these scores; a round with a missing judge, a weighted
      score that does not follow from its parts or a gap typed by hand would mislead the next fix.
How:  plain JSON reads and arithmetic, with a tolerance of one rounding step (0.006); each problem is a
      plain sentence, and the script exits 1 if there is any.
"""
import argparse, copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUNDS = ROOT / "runs" / "judge_rounds.json"
REVIEW = ROOT / "runs" / "review_round.json"
CRITERIA = ("value", "analytics", "presentation", "innovation")
SEATS = 9
TOLERANCE = 0.006


def close(a, b):
    return abs(float(a) - float(b)) <= TOLERANCE


def mean(values):
    return sum(values) / len(values)


def round_problems(data, number):
    """Every problem with round `number` of a judge_rounds document, as plain sentences."""
    anchor = data.get("anchor", {})
    rounds = [r for r in data.get("rounds", []) if r.get("round") == number]
    if not rounds:
        return [f"round {number} is not recorded"]
    rnd, problems = rounds[0], []
    weights = rnd.get("weights", {})
    if set(weights) != set(CRITERIA) or not close(sum(weights.values()), 1.0):
        problems.append("weights must cover the 4 criteria and add to 1")
    judges = rnd.get("judges", [])
    if len(judges) != SEATS or len({j.get("seat") for j in judges}) != SEATS:
        problems.append(f"{len(judges)} judges recorded, {SEATS} distinct seats required")
    if sum(bool(j.get("held_out")) for j in judges) != 1:
        problems.append("exactly one judge must be held out")
    for j in judges:
        seat, scores = j.get("seat"), j.get("scores", {})
        if set(scores) != set(CRITERIA) or not all(1 <= scores[c] <= 5 for c in scores):
            problems.append(f"{seat}: needs a 1 to 5 score on each of {', '.join(CRITERIA)}")
            continue
        if weights and not close(j.get("weighted", -1), sum(weights[c] * scores[c] for c in CRITERIA)):
            problems.append(f"{seat}: weighted {j.get('weighted')} does not follow from its scores")
        for c in CRITERIA:
            if not close(j.get("gap_to_anchor", {}).get(c, 99), scores[c] - anchor.get("scores", {}).get(c, 0)):
                problems.append(f"{seat}: gap to anchor on {c} is not score minus anchor")
    if judges and not problems:
        if not close(rnd.get("average_weighted", -1), mean([j["weighted"] for j in judges])):
            problems.append("average_weighted is not the mean of the judges")
        for c in CRITERIA:
            avg = mean([j["scores"][c] for j in judges])
            if not close(rnd.get("average_by_criterion", {}).get(c, -1), avg):
                problems.append(f"average on {c} is not the mean of the judges")
            if not close(rnd.get("gap_to_anchor_by_criterion", {}).get(c, 99), avg - anchor["scores"][c]):
                problems.append(f"round gap on {c} is not the average minus the anchor")
    if number > 1 and "held_out_change" not in rnd:
        problems.append(f"round {number} must state the held-out judge's change from round {number - 1}")
    return problems


def review_problems(review):
    """Every problem with the M8 review record."""
    problems = []
    checks, answers = review.get("number_checks", []), review.get("examiner_answers", [])
    if len(checks) != 10:
        problems.append(f"{len(checks)} number checks recorded, 10 required")
    if len(answers) != 10:
        problems.append(f"{len(answers)} examiner answers recorded, 10 required")
    passed = sum(bool(a.get("pass")) for a in answers)
    if passed < 9:
        problems.append(f"examiner passed {passed} of {len(answers)}, 9 required")
    return problems


def run_selftest(data):
    """Plant one bad case of each kind into a copy of the real round 1; each must be caught."""
    plants = {
        "a judge removed": lambda d: d["rounds"][0]["judges"].pop(),
        "weighted typed wrong": lambda d: d["rounds"][0]["judges"][0].__setitem__("weighted", 4.9),
        "score out of range": lambda d: d["rounds"][0]["judges"][1]["scores"].__setitem__("value", 7),
        "gap typed by hand": lambda d: d["rounds"][0]["judges"][2]["gap_to_anchor"].__setitem__("value", 0.0),
        "no held-out judge": lambda d: [j.__setitem__("held_out", False) for j in d["rounds"][0]["judges"]],
        "average typed wrong": lambda d: d["rounds"][0].__setitem__("average_weighted", 4.5),
    }
    ok = not round_problems(data, 1)
    print(f"{'PASS' if ok else 'FAIL'}  the real round 1 passes unchanged")
    for name, plant in plants.items():
        bad = copy.deepcopy(data)
        plant(bad)
        caught = bool(round_problems(bad, 1))
        ok &= caught
        print(f"{'PASS' if caught else 'FAIL'}  caught: {name}")
    missing = bool(round_problems(data, 99))
    short = bool(review_problems({"number_checks": [{}] * 10, "examiner_answers": [{"pass": True}] * 8 + [{}] * 2}))
    ok &= missing and short
    print(f"{'PASS' if missing else 'FAIL'}  caught: a round that is not recorded")
    print(f"{'PASS' if short else 'FAIL'}  caught: an examiner pass of 8 of 10")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--round", type=int, help="check this judge round")
    parser.add_argument("--review", action="store_true", help="check runs/review_round.json")
    parser.add_argument("--selftest", action="store_true", help="plant bad cases and require each caught")
    args = parser.parse_args()
    data = json.loads(ROUNDS.read_text()) if ROUNDS.exists() else {}
    if args.selftest:
        sys.exit(0 if run_selftest(data) else 1)
    problems = []
    if args.round:
        problems += round_problems(data, args.round)
    if args.review:
        problems += review_problems(json.loads(REVIEW.read_text())) if REVIEW.exists() else ["runs/review_round.json is missing"]
    if not (args.round or args.review):
        parser.error("pass --round N, --review or --selftest")
    for p in problems:
        print(f"FAIL  {p}")
    if args.round and not problems:
        rnd = [r for r in data["rounds"] if r["round"] == args.round][0]
        print(f"round {args.round}: {len(rnd['judges'])} judges, average {rnd['average_weighted']:.2f} against anchor "
              f"{data['anchor']['weighted']:.2f}; gaps by criterion {rnd['gap_to_anchor_by_criterion']}")
    print(f"judge_rounds_check: {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
