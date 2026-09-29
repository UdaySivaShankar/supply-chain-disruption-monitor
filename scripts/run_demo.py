#!/usr/bin/env python3
"""End-to-end Hindsight learning demonstration, run against a live backend.

Usage:
    python scripts/run_demo.py [--base-url http://localhost:8000]

Sequence:
    1. Trigger a supplier delay disruption.
    2. Print the agent trace, recommendation and recalled memories.
    3. Approve the recommendation as the human operator.
    4. Resolve the case, which retains the experience in Hindsight.
    5. Trigger a second, similar disruption.
    6. Show how the recalled experience changed the recommendation.

Everything printed comes from the running API. No values are invented here.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

SIMULATED_EVENT = {
    "type": "supplier_delay",
    "description": "Supplier ABC reports a 10 day delivery delay",
    "delay_days": 10,
    "severity": "critical",
}

FIRST_OUTCOME = (
    "Rerouted 45 percent of volume to the alternative supplier. "
    "Delivery landed 2 days before stockout and no line stoppage occurred."
)


def call(base_url, method, path, payload=None, api_key=""):
    url = f"{base_url}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise SystemExit(f"HTTP {exc.code} on {method} {path}: {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach {url}: {exc.reason}")


def wait_for_analysis(base_url, case_id, api_key, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        case = call(base_url, "GET", f"/disruptions/{case_id}", api_key=api_key)
        if case.get("status") in ("pending_approval", "approved", "resolved"):
            return case
        time.sleep(1)
    raise SystemExit(f"Case {case_id} did not reach the approval stage in time.")


def divider(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def describe(case):
    recommendation = case.get("recommendation") or {}
    print(f"Status:              {case.get('status')}")
    print(f"Inventory coverage:  {case.get('inventory_coverage_days')} days")
    print(f"Stockout risk:       {case.get('stockout_risk')}")
    print(f"Estimated impact:    ${case.get('estimated_impact_value', 0):,.2f}")
    print(f"Agent steps:         {len(case.get('agent_trace') or [])}")
    print(f"Recommendation:      {recommendation.get('recommended_action')}")
    print(f"Alternative supplier:{recommendation.get('alternative_supplier')}")
    print(f"Confidence:          {recommendation.get('confidence_score')}")
    print(f"Risk level:          {recommendation.get('risk_level')}")
    print(f"Recalled memories:   {len(case.get('hindsight_memories') or [])}")
    for memory in case.get("hindsight_memories") or []:
        content = memory.get("content") if isinstance(memory, dict) else memory
        print(f"  - {content}")


def main():
    parser = argparse.ArgumentParser(description="Run the Hindsight learning demo.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    health = call(base_url, "GET", "/health")
    print(f"Backend health: {health.get('status')}")

    suppliers = call(base_url, "GET", "/suppliers", api_key=args.api_key)
    if not suppliers:
        raise SystemExit("No suppliers found. Seed the database first.")
    supplier = suppliers[0]
    print(f"Using supplier: {supplier['name']} ({supplier['id']})")

    divider("1. FIRST DISRUPTION (no prior experience)")
    first_payload = dict(SIMULATED_EVENT, supplier_id=supplier["id"])
    first_id = call(base_url, "POST", "/disruptions/simulate", first_payload, args.api_key)["case_id"]
    first = wait_for_analysis(base_url, first_id, args.api_key)
    describe(first)

    divider("2. HUMAN APPROVAL AND OUTCOME RECORDING")
    print(call(base_url, "POST", f"/disruptions/{first_id}/approve",
                {"notes": "Evidence reviewed by operator."}, args.api_key))
    print(call(base_url, "POST", f"/disruptions/{first_id}/resolve",
                {"outcome": FIRST_OUTCOME}, args.api_key))

    divider("3. SECOND, SIMILAR DISRUPTION (memory should be recalled)")
    second_id = call(base_url, "POST", "/disruptions/simulate", first_payload, args.api_key)["case_id"]
    second = wait_for_analysis(base_url, second_id, args.api_key)
    describe(second)

    divider("4. COMPARISON")
    first_confidence = (first.get("recommendation") or {}).get("confidence_score", 0)
    second_confidence = (second.get("recommendation") or {}).get("confidence_score", 0)
    print(f"First confidence:   {first_confidence}")
    print(f"Second confidence:  {second_confidence}")
    print(f"Memories on first:  {len(first.get('hindsight_memories') or [])}")
    print(f"Memories on second: {len(second.get('hindsight_memories') or [])}")
    if len(second.get("hindsight_memories") or []) > 0 and second_confidence > first_confidence:
        print("Result: Hindsight recalled the earlier experience and the new "
              "recommendation is informed by it.")
    else:
        print("Result: no historical experience was recalled for the second event.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
