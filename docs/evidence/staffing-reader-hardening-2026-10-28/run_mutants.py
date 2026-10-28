"""Each mutant removes one guard of the hardened staffing reader; the tests must fail on every one."""
import shutil, subprocess, sys, tempfile
from pathlib import Path
SRC = Path(sys.argv[1])
R, I = "src/services/staffing_evidence.py", "src/services/opportunity_intake.py"
MUTANTS = {
    "bottleneck gap unchecked": (R, "        if need - capacity != shortage:\n", "        if False:\n"),
    "certified unchecked": (R, '    if value.get("certified") is not True:\n', "    if False:\n"),
    "certificate unchecked": (R, '    if not isinstance(value.get("certificate"), dict):\n', "    if False:\n"),
    "bottleneck-when-full unchecked": (R, "        if bottleneck is not None:\n", "        if False:\n"),
    "unfilled outside bottleneck allowed": (R, "        if not {order for order, _ in unfilled} <= orders:\n", "        if False:\n"),
    "outside worker allowed": (R, "        if any(w not in workers for w, _, _ in on_bottleneck):\n", "        if False:\n"),
    "bottleneck capacity unchecked": (R, "        if sum(x for *_, x in on_bottleneck) != capacity:\n", "        if False:\n"),
    "replay not detected": (R, "                if first != here:\n", "                if False:\n"),
    "label only at start": (R, "    match = _LABEL.search(item)\n", "    match = _LABEL.match(item)\n"),
    "label exact case": (R, '_LABEL = re.compile(r"evidence from greg[’\'‘]s certified staffing plan", re.IGNORECASE)', '_LABEL = re.compile(r"Evidence from GREG\'s certified staffing plan")'),
    "unlabeled shape ignored": (R, "            if _SHAPE.search(item):\n                reviews.append", "            if False:\n                reviews.append"),
    "trailing text ignored": (R, "        if match is None and tail < len(item):\n", "        if False:\n"),
    "depth unbounded": (R, "            if depth > MAX_DEPTH:\n", "            if False:\n"),
    "digits unbounded": (R, "            if digits > MAX_DIGITS:\n", "            if False:\n"),
    "staffing items feed demand signals": (I, 'for evidence_item in demand_evidence(packet["evidence"])[:_MAX_SIGNALS]', 'for evidence_item in packet["evidence"][:_MAX_SIGNALS]'),
    "staffing items counted by the committee": (I, 'cases = build_cases({**packet, "evidence": demand}, score, alignment)', "cases = build_cases(packet, score, alignment)"),
    "only-staffing packet allowed": (I, "        elif not demand:\n", "        elif False:\n"),
    "plan ignored in divergence": (I, "review.unfilled, review.assignment)", "review.unfilled)"),
    "wire-order priority": (I, "key=lambda review: review.priority)", "key=lambda review: not review.prevents_go)"),
    "M12 duplicate-key hook dropped": (R, "            value = json.loads(item[start:end], object_pairs_hook=_object, parse_constant=_constant)", "            value = json.loads(item[start:end], parse_constant=_constant)"),
    "M14 zero-unit rows allowed": (R, '_units(row[2], "assignment units", positive=True)', '_units(row[2], "assignment units")'),
    "M19 unit bound dropped": (R, "    if type(value) is not int or not (int(positive) <= value <= MAX_UNITS):", "    if type(value) is not int or not (int(positive) <= value):"),
    "M09 shortage of one ignored": (R, "        return self.error is not None or bool(self.shortage)", "        return self.error is not None or (self.shortage or 0) > 1"),
    "M24 staffing skipped under flags": (I, "        reasons.extend(review.reason for review in staffing)", "        staffing = [] if packet[\"risk_flags\"] else staffing\n        reasons.extend(review.reason for review in staffing)"),
    "M21 unfilled ignored in divergence": (I, "(review.staffed, review.demand, review.shortage, review.unfilled, review.assignment)", "(review.staffed, review.demand, review.shortage, review.assignment)"),
    "M22 only totals in divergence": (I, "(review.staffed, review.demand, review.shortage, review.unfilled, review.assignment)", "(review.staffed, review.demand)"),
    "M36 first JSON line only": (R, "            end = start + _extent(item[start:])", "            end = start + _extent(item[start:].split(chr(10))[0])"),
    "steps not deduplicated": (I, "        validation_plan = list(dict.fromkeys(step for step in [", "        validation_plan = list((step for step in ["),
}
TESTS = ["tests/test_staffing_reader_hardening.py", "tests/test_staffing_evidence.py", "tests/test_opportunity_intake.py"]
results = {}
for name, (path, old, new) in MUTANTS.items():
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(SRC, tmp / "w", ignore=shutil.ignore_patterns(".git", "__pycache__"))
    f = tmp / "w" / path
    text = f.read_text()
    if text.count(old) != 1:
        results[name] = "ANCHOR_MISSING"
        continue
    f.write_text(text.replace(old, new))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "-W", "ignore", *TESTS],
                       cwd=tmp / "w", capture_output=True, text=True, timeout=600)
    last = (r.stdout.strip().splitlines() or ["?"])[-1]
    results[name] = ("CAUGHT" if r.returncode == 1 else ("ERROR(rc=%d)" % r.returncode if r.returncode else "SURVIVED")) + " | " + last
    shutil.rmtree(tmp)
for k, v in results.items():
    print(f"{k:42s} {v}")
caught = sum(v.startswith("CAUGHT") for v in results.values())
print(f"caught {caught} of {len(results)}")
