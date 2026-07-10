# RAG Methodology — Project Health Scoring

## What this measures

Every project gets a Red/Amber/Green (RAG) status computed from four signals pulled from
its project plan (task list, per-task status, and stakeholder comments). The score is
deterministic and reproducible — the same inputs always produce the same status, and an
LLM narrative layer explains the "why" in plain English without ever changing the number.

## The four signals

| Signal | Weight | What it measures |
|---|---|---|
| **Schedule slippage** | 35% | Is the project further behind than time elapsed would suggest? Compares actual % complete to expected % complete (days elapsed ÷ total planned duration, measured from the plan's own "Today's Date," not the system clock). Also penalized if a task on the critical path (`Critical? = True`) has negative schedule float. |
| **Milestone health** | 30% | Are named phase/milestone checkpoints hitting their dates? Each milestone whose baseline finish date has passed without being marked Completed is penalized, scaled by how many days overdue it is. |
| **Blockers** | 20% | How many open issues are sitting in the plan right now? Counts tasks flagged On Hold, tasks with an explicit status comment describing a problem, and not-yet-started tasks whose predecessor task is itself overdue. |
| **Stakeholder sentiment** | 15% | How does the tone of PM/stakeholder comments read? Scored with VADER, a lexicon-based sentiment model built for short informal text (no LLM calls, so it's fast, free, and deterministic). Calm comments score high; urgent/frustrated comments score low. |

Each signal is normalized to 0–100, then combined into one **composite score**:

```
composite = 0.35 × schedule + 0.30 × milestone + 0.20 × blockers + 0.15 × sentiment
```

## Turning the score into a status

| Composite score | Status |
|---|---|
| 80–100 | 🟢 Green |
| 60–79 | 🟡 Amber |
| Below 60 | 🔴 Red |

## Hard overrides (these win, no matter what the composite says)

Some situations are serious enough that no amount of "good average" should paper over them:

1. **A milestone is overdue by more than 10 days** (configurable) and still isn't marked
   Completed → forced Red.
2. **A critical-path task has negative float** and there's no documented recovery plan on
   record → forced Red.

If either fires, the project shows Red even if the weighted composite lands in Amber or
Green territory — and the report always states plainly that an override fired and why,
rather than hiding the discrepancy.

## What this deliberately does NOT measure

**Budget burn is out of scope.** Neither sample project plan contains a cost or budget
column — there is nothing to score. Rather than inventing a cost proxy (e.g., treating
task count as a stand-in for spend), the system reports this as a named, explicit data
gap on every run. If budget data becomes available, it would be a natural fifth signal.

## How missing or messy data is handled

Real project plans are inconsistent — this system does not paper over that. Anywhere a
required column or value is missing, unparseable, or structurally different between
project plans (e.g., one plan lacking a `Level` hierarchy column, or a Comments sheet
with zero entries), the affected sub-score falls back to a neutral default (50) and the
report explicitly names the gap. Nothing is silently defaulted to a guessed value, and a
missing signal is never treated as "automatically fine."
