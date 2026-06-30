from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
from langchain_core.prompts import ChatPromptTemplate

# Import the compiled graph and all node functions from the existing file.
from kalpi_strategy_builder import (
    app as langgraph_app,
    State,
    take_input,
    universe_node,
    filter_node,
    ranking_node,
    weightage_node,
    display_node,
    modification_node,
    metrics_constant,
    universes_constant,
    validate_metrics,
    validated_filters,
    extract_json,
    llm,
    clarification_node,
    _fmt_filter,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return FileResponse("kalpi_chat.html")

sessions: dict[str, State] = {}

class StartRequest(BaseModel):
    session_id: str
    user_input: str

class ModifyRequest(BaseModel):
    session_id: str
    modification_input: str

class StateResponse(BaseModel):
    session_id: str
    stage: str
    state: dict
    message: str

def _run_enrich(state: State, user_input: str) -> State:
    prompt = ChatPromptTemplate.from_template(
        """You are a quantitative trading strategy analyst. A user has described an investment strategy in their own words — it may be technical or plain language. Your job is to expand it into a precise, implementation-ready breakdown that downstream systems will use to screen and rank stocks.

Respond ONLY with a bullet-point breakdown using exactly these six sections. Do not add commentary, preamble, or a summary outside this structure.

- Core thesis: The market pattern or inefficiency this strategy exploits.
- Target stocks: Company characteristics to look for — size, sector, liquidity, growth vs. value orientation.
- Entry criteria: Specific conditions a stock must meet — technical signals, fundamental thresholds, price action, valuation limits. Be quantitative where possible (e.g. "RSI 14 above 55", "P/E below 20").
- Ranking logic: What separates the best picks from merely eligible ones. List signals in priority order.
- Risk profile: Aggressive / balanced / conservative. Note expected volatility tolerance and any concentration limits.
- Holding intent: Short-term trade (days–weeks) or medium/long-term investment (months–years).

Rules:
- Each bullet should be 1–3 sentences.
- Prefer numbers and thresholds over vague language. "Momentum above peers" is too vague; "3-month return in top 30% of universe" is good.
- If the user's input is ambiguous, make a reasonable assumption and state it in parentheses — e.g. (assumed: large-cap bias given mention of stability).
- Never ask the user a clarifying question.

User Input : {input}"""
    )
    enriched_input = prompt | llm
    enriched_input = enriched_input.invoke(
        {"input": user_input}
    )

    print("🔴 " + enriched_input.content)

    return {
        **state,
        "input": user_input,
        'enriched_input': enriched_input.content
    }

def _run_modification(state: State, mod_input: str) -> State:
    filters_str = "\n".join(
        f"    • {_fmt_filter(f)}"
        for f in state["filters"]
    )
    ranking_str = "\n".join(f"    {i+1}. {m}" for i, m in enumerate(state["ranking_metrics"]))

    if state["weight_type"] == "metric":
        inverse, metric = state["weight_metrics"][0], state["weight_metrics"][1]
        weight_str = f"Metric-based → {metric}" + (" (inverse)" if inverse == "inverse" else "")
    else:
        weight_str = "Equal weighting"

    conversation = [
        ('system', """\
You are a quantitative portfolio strategist specialising in Indian equities. \
A user wants to modify an existing screener strategy. Your job is to interpret \
their intent precisely and produce a concrete, implementation-ready modification plan.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Universe       : {universe}
Filters        : {filters}
Ranking metrics: {ranking}
Weighting      : {weight}
Top N stocks   : {top_n}

Reasoning on record:
  Universe  → {r_universe}
  Filters   → {r_filter}
  Ranking   → {r_rank}
  Weighting → {r_weight}""".format(
        universe=state["universe"],
        filters=filters_str,
        ranking=ranking_str,
        weight=weight_str,
        top_n=state["top_n"],
        r_universe=state["reasoning"].get("universe", "—"),
        r_filter=state["reasoning"].get("filter", "—"),
        r_rank=state["reasoning"].get("rank", "—"),
        r_weight=state["reasoning"].get("weightage", "—"),
        )
  ),

('human',"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INSTRUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{instructions}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Enrich the user instruction: infer any implicit intent and resolve ambiguity. \
   State your interpretation.

2. Produce a modification plan using ONLY these five sections. \
   Do not add, rename, or reorder them.

- Universe change  : State the new universe, or "No change" if unaffected. \
                     One sentence justifying the choice.
- Filter changes   : List each filter to ADD, REMOVE, or MODIFY as a bullet. \
                     Use the format → ADD / REMOVE / MODIFY | <metric> <operator> <value> | <reason>. \
                     Write "No change" if unaffected.
- Ranking changes  : List each ranking metric to ADD, REMOVE, or REORDER as a bullet \
                     using the same → ACTION | <metric> | <reason> format. \
                     Write "No change" if unaffected.
- Weighting change : State the new weighting scheme, or "No change". One sentence justifying it. weights can be applied based on a metric (like "PE Ratio") or equal.
- Top N change     : State the new number, or "No change". One sentence justifying it.

Rules:
- Be quantitative. "Increase momentum exposure" is not acceptable; \
  "ADD | 3-month price return | top momentum signal for medium-term strategies" is.
- Never suggest metrics that are not measurable or that require data outside a standard \
  Indian equity screener (e.g. management quality, ESG ratings without a numeric score).
- Do not restate parts of the strategy that are unchanged beyond writing "No change".
- If the user instruction contradicts the strategy's core thesis, flag it explicitly \
  before the modification plan with: ⚠ Conflict: <one sentence>.
""".format(
        instructions = mod_input
        )
    )
    ]

    enriched_mod = llm.invoke(conversation)

    print("🟡 Modification Plan:\n", enriched_mod.content.strip())
    conversation.append(('ai', enriched_mod.content.strip()))

    conversation.append(('system', """Identify which sections need modification. Respond with ONLY a valid JSON object — no markdown, no code fences, no explanation.

Valid section names: "universe", "filters", "ranking_metrics", "weight_metrics", "top_n"

Format: {"sections": ["<section_name>", ...]}
Example: {"sections": ["universe", "filters", "top_n"]}"""))
    response = llm.invoke(conversation)
    try:
        parsed = extract_json(response.content.strip())
    except:
        print("⚠️ Invalid JSON Returned... Trying again")
        response = llm.invoke(conversation)
        parsed = extract_json(response.content.strip())

    parsed = validate_metrics(parsed['sections'], ["universe", "filters", "ranking_metrics", "weight_metrics", "top_n"])

    state = {**state, "mod_conversation": conversation,
             "latest_mod_plan": enriched_mod.content.strip(),
             "enriched_input": f"ORIGINAL:\n{state['enriched_input']}\n\nMODIFICATION PLAN:\n{enriched_mod.content.strip()}"}

    SECTION_NODE_MAP = {
        "universe":        universe_node,
        "filters":         filter_node,
        "ranking_metrics": ranking_node,
        "weight_metrics":  weightage_node,
        "top_n":           weightage_node,
    }

    already_run = set()
    for section in parsed:
        node_fn = SECTION_NODE_MAP.get(section)
        if node_fn is None:
            print(f"⚠️ Unknown section '{section}', skipping.")
            continue
        if node_fn in already_run:
            continue
        print(f"🔄 Updating: {section}")
        state = node_fn(state)
        already_run.add(node_fn)

    return {
        **state,
        "mod_conversation": state.get("mod_conversation", []) + conversation,
        "is_complete": False,  # send back to display_node for review
    }


@app.post("/api/start")
def start_workflow(req: StartRequest):
    try:
        initial_state: State = {
            "input": req.user_input,
            "enriched_input": "",
            "metrics": metrics_constant,
            "universe": "",
            "filters": [],
            "ranking_metrics": [],
            "top_n": 0,
            "weight_type": "equal",
            "weight_metrics": [],
            "reasoning": {},
            "mod_conversation": [],
            "is_complete": False,
            "clarification_history": [],
            "awaiting_clarification": False,
            "clarification_rounds": 0,
            "clarification_attempts_max": 3,
            "latest_clarification_question": None,
        }
        state = _run_enrich(initial_state, req.user_input)
        state = universe_node(state)
        state = filter_node(state)
        state = ranking_node(state)
        state = weightage_node(state)
        sessions[req.session_id] = state
        return StateResponse(
            session_id=req.session_id,
            stage="complete",
            state=state,
            message="Workflow completed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _run_full_pipeline(state: State) -> State:
    """Run the main pipeline steps after clarification is sufficient."""
    state = _run_enrich(state, state["input"])
    state = universe_node(state)
    state = filter_node(state)
    state = ranking_node(state)
    state = weightage_node(state)
    return state

@app.post("/api/chat/start")
def chat_start(req: StartRequest):
    """Start a session with interactive clarification flow."""
    try:
        # Initialize state with clarification fields (already included in start_workflow)
        initial_state: State = {
            "input": req.user_input,
            "enriched_input": "",
            "metrics": metrics_constant,
            "universe": "",
            "filters": [],
            "ranking_metrics": [],
            "top_n": 0,
            "weight_type": "equal",
            "weight_metrics": [],
            "reasoning": {},
            "mod_conversation": [],
            "is_complete": False,
            "clarification_history": [],
            "awaiting_clarification": False,
            "clarification_rounds": 0,
            "clarification_attempts_max": 3,
            "latest_clarification_question": None,
        }
        # Run the first clarification check
        state = clarification_node(initial_state)
        sessions[req.session_id] = state
        if state.get("awaiting_clarification"):
            return StateResponse(
                session_id=req.session_id,
                stage="clarification",
                state=state,
                message=state.get("latest_clarification_question", "Need clarification"),
            )
        # No clarification needed – run full pipeline
        state = _run_full_pipeline(state)
        sessions[req.session_id] = state
        return StateResponse(
            session_id=req.session_id,
            stage="complete",
            state=state,
            message="Workflow completed",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRespondRequest(BaseModel):
    session_id: str
    answer: str

@app.post("/api/chat/respond")
def chat_respond(req: ChatRespondRequest):
    """Provide an answer to the latest clarification question and continue."""
    try:
        if req.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        state = sessions[req.session_id]
        # Record the answer
        q = state.get("latest_clarification_question")
        if q:
            state["clarification_history"].append((q, req.answer))
        state["clarification_rounds"] = state.get("clarification_rounds", 0) + 1
        # Reset awaiting flag before next check
        state["awaiting_clarification"] = False
        state["latest_clarification_question"] = None
        # Run clarification node again
        state = clarification_node(state)
        sessions[req.session_id] = state
        if state.get("awaiting_clarification"):
            return StateResponse(
                session_id=req.session_id,
                stage="clarification",
                state=state,
                message=state.get("latest_clarification_question", "Need clarification"),
            )
        # Clarification sufficient – run the rest of the pipeline
        state = _run_full_pipeline(state)
        sessions[req.session_id] = state
        return StateResponse(
            session_id=req.session_id,
            stage="complete",
            state=state,
            message="Workflow completed",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modify")
def modify_workflow(req: ModifyRequest):
    try:
        if req.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = sessions[req.session_id]
        state = _run_modification(state, req.modification_input)
        sessions[req.session_id] = state
        return StateResponse(
            session_id=req.session_id,
            stage="complete",
            state=state,
            message="Modification completed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
def reset_session(req: StartRequest):
    if req.session_id in sessions:
        del sessions[req.session_id]
    return {"ok": True}

@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return StateResponse(
        session_id=session_id,
        stage="complete",
        state=sessions[session_id],
        message="Session fetched"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
