#!/usr/bin/env bash
# Local gate matching .github/workflows/ci.yml (checks job): repo check, full tests, build --check.
# Additive only; does not skip or weaken any check.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Chrome for Testing on the team box (optional). Leave PATH alone on a normal laptop.
if [[ -d /workspace/tools/bin ]]; then
  export PATH="/workspace/tools/bin:${PATH}"
fi

pass=0
fail=0
report() {
  local name="$1" status="$2"
  if [[ "$status" == "ok" ]]; then
    echo "PASS  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name"
    fail=$((fail + 1))
  fi
}

echo "== preflight: Slopworks local CI gate =="
echo "root: $ROOT"
echo

set +e
python3 scripts/check.py repo
st=$?
set -e
if [[ $st -eq 0 ]]; then report "scripts/check.py repo" ok; else report "scripts/check.py repo" fail; fi

set +e
python3 -m unittest discover -s tests -v
st=$?
set -e
if [[ $st -eq 0 ]]; then report "python3 -m unittest discover -s tests -v" ok; else report "python3 -m unittest discover -s tests -v" fail; fi

set +e
python3 scripts/build.py --check
st=$?
set -e
if [[ $st -eq 0 ]]; then report "python3 scripts/build.py --check" ok; else report "python3 scripts/build.py --check" fail; fi

echo
echo "== summary: ${pass} passed, ${fail} failed =="
if [[ "$fail" -ne 0 ]]; then
  echo "preflight: FAILED"
  exit 1
fi
echo "preflight: OK"
exit 0
