# End-to-end demonstration

This walkthrough proves the two claims that matter: the system runs a complete
human-approved mitigation workflow, and Hindsight lets it learn from earlier
events.

All values shown below come from the running system. Nothing is pre-recorded.

## Before you start

```bash
cp .env.example .env          # add GOOGLE_API_KEY if you want LLM phrasing
docker compose up -d
docker compose exec backend python scripts/seed_data.py
```

Open http://localhost:3000 for the dashboard and http://localhost:8000/docs
for the API.

Alternative without the full stack:

```bash
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1   # tests, build, migrations, seed
```

## Part A: first disruption, no prior memory

| Step | Where | What to look at |
|---|---|---|
| 1 | Simulator, scenario "Supplier delay" | Supplier ABC reports a 10 day delay |
| 2 | Disruptions list | A new case appears with CRITICAL severity |
| 3 | Open the case, Agent Reasoning Timeline | 8 stages recorded, ending at Human Approval Gatekeeper |
| 4 | Impact Assessment card | Inventory coverage is 5 days, stockout risk is above 70 percent |
| 5 | Impact Assessment panel | Estimated impact value computed from coverage, demand and unit cost |
| 6 | Historical Memory from Hindsight | Empty state: "No prior disruption experiences found" |
| 7 | Agent Recommendation | Emergency secondary purchase order, confidence 76 percent, risk Medium |
| 8 | Affected Supplier panel | Lead time, reliability score and capabilities from PostgreSQL |
| 9 | Human Approval Required | Autonomous action is halted, Approve and Reject are the only controls |
| 10 | Approve with operator notes | Case moves to approved, an operator entry is added to the timeline |
| 11 | Record the outcome and resolve | Case moves to resolved and the experience is written to Hindsight |
| 12 | Memory page | The retained experience is now listed with its outcome |

## Part B: second disruption, memory recalled

| Step | Where | What to look at |
|---|---|---|
| 13 | Simulator, same scenario again | A second, separate case is created |
| 14 | Open it, Hindsight Memory section | The previous event, recommendation and outcome are shown with a relevance score |
| 15 | Agent Recommendation | Confidence rises to 94 percent, risk drops to Low, the rationale quotes the recalled experience |

The visible difference between step 7 and step 15 is the learning
demonstration: same supplier, same disruption type, different recommendation
because the earlier outcome is now available.

## What to point out to a judge

- The reasoning timeline separates SQL evidence, recalled memory, the agent
  conclusion and the human decision.
- Nothing executes without approval. Approve and Reject are the only paths to
  a state change, and rejection records the operator note.
- Retention only happens at resolution, so memory reflects real outcomes rather
  than proposals.

## Running the same sequence from the command line

With the backend running:

```bash
python scripts/run_demo.py --base-url http://localhost:8000
```

The script triggers the first disruption, prints the agent trace and
recommendation, approves and resolves it, triggers the second disruption and
then prints the confidence and memory comparison. It exits non-zero if the
second event does not recall the first.

## Automated checks

```bash
cd backend && python -m pytest tests -v
```

The suite covers database operations, inventory calculations, disruption
detection, impact assessment, supplier comparison, Hindsight retain and
recall, the agent workflow, the approval workflow, every API endpoint, and an
end-to-end test that repeats the two-event learning sequence above.
