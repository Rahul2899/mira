import os
import re
import boto3
from topsis import run_topsis_optimization

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")
bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")

SYSTEM_PROMPT = """You are the Autonomous Siting Agent (ASA), a senior infrastructure siting analyst for data center developers. A user describes a data center they want to build, in natural language, with varying priorities around cost, sustainability, grid connection speed, and connectivity.

Your job:
1. Extract the user's priorities as four weights (cost, green, grid, connectivity), each between 0.0 and 1.0, together summing to roughly 1.0. If the user doesn't mention a dimension, give it a moderate default weight (0.15-0.25). If they explicitly say they don't care about it, use a low weight like 0.05. Also extract the facility size in megawatts (size_mw) if the user states one; omit it if they don't.
2. Call the optimize_site tool with these four weights and the size.
3. When you receive the tool result, write a SHORT executive memo as 4-6 concise bullet points (one line each) covering:
- The recommended site and its score out of 100
- Why it won vs the runner-up, with the key number (cost or clean %)
- If a size was given: the grid draw, and how many regions were ruled out for insufficient headroom
- How many sites were filtered out before ranking, and why
- How to power it (from supply_plan: grid clean enough, or a PPA / on-site needed)
- The main trade-off accepted

Never invent numbers. Only reference numbers present in the tool's output. When discussing available grid capacity, always use spare_headroom_mw, never grid_capacity_mw.

FORMAT: each point on its own line, starting with "- " (a dash and a space). Keep each bullet under 18 words. No headings, no preamble like "Here is the memo", no bold/markdown other than the leading dash. Express scores as a number out of 100. Start directly with the first bullet."""

TOOL_CONFIG = {"tools": [{"toolSpec": {
    "name": "optimize_site",
    "description": "Runs a multi-criteria (TOPSIS) ranking of European grid nodes for data center siting, given priority weights for cost, green energy share, grid connection headroom, and connectivity.",
    "inputSchema": {"json": {
        "type": "object",
        "properties": {
            "weight_cost": {"type": "number", "description": "Priority weight for minimizing electricity cost, 0.0-1.0"},
            "weight_green": {"type": "number", "description": "Priority weight for maximizing clean/renewable power share, 0.0-1.0"},
            "weight_grid": {"type": "number", "description": "Priority weight for grid connection headroom / avoiding congestion, 0.0-1.0"},
            "weight_connectivity": {"type": "number", "description": "Priority weight for fiber/network connectivity, 0.0-1.0"},
            "size_mw": {"type": "number", "description": "Data center IT load in megawatts if the user states a size; omit otherwise"},
        },
        "required": ["weight_cost", "weight_green", "weight_grid", "weight_connectivity"],
    }},
}}]}


def extract_weights(prompt):
    topics = {
        'weight_cost': ('cost', 'cheap', 'price', 'budget'),
        'weight_green': ('green', 'clean', 'carbon', 'renewable', 'sustain'),
        'weight_grid': ('grid', 'capacity', 'congest', 'queue', 'quickly'),
        'weight_connectivity': ('latency', 'connectivity', 'fiber', 'internet', 'exchange', 'hub'),
    }
    p = prompt.lower()
    return {k: 0.1 + sum(w in p for w in words) for k, words in topics.items()}


def extract_size(prompt):
    m = re.search(r'(\d+(?:\.\d+)?)\s*mw', prompt.lower())
    return float(m.group(1)) if m else None


def run_local(prompt):
    result = run_topsis_optimization(extract_weights(prompt), size_mw=extract_size(prompt))
    top = result['ranking'][0]
    facility = result.get('facility')
    memo = f"Recommendation: {top['region']}, scoring {round(top['score'] * 100)} out of 100 against your priorities.\n\n"
    if facility:
        memo += (f"At {facility['size_mw']:.0f} MW of IT load, this facility draws about {facility['grid_draw_mw']} MW from the grid once cooling is included, "
                 f"and {result['meta_undersized_filtered']} regions were ruled out because their grid could not absorb that load.\n\n")
    memo += f"{top['supply_plan']['recommendation']}\n\n" if top.get('supply_plan') else ""
    memo += (f"{result['meta_total_environmental_filtered']} sites were also excluded for sitting inside protected nature reserves. "
             "The AI agent is offline right now, so your brief was read with a keyword scan; the ranking math is identical either way.")
    return {"memo": memo, "raw_result": result}


def run_agent(prompt):
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    last_result = None
    turn = 0
    while True:
        # force the tool on the first turn so even vague briefs always produce a ranking
        cfg = dict(TOOL_CONFIG)
        if turn == 0:
            cfg = {**TOOL_CONFIG, "toolChoice": {"tool": {"name": "optimize_site"}}}
        turn += 1
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=cfg,
        )
        message = response["output"]["message"]
        messages.append(message)

        if response["stopReason"] != "tool_use":
            memo = "".join(b["text"] for b in message["content"] if "text" in b)
            return {"memo": memo, "raw_result": last_result}

        tool_results = []
        for block in message["content"]:
            if "toolUse" in block:
                tool = block["toolUse"]
                args = dict(tool["input"])
                size = args.pop("size_mw", None)
                last_result = run_topsis_optimization(args, size_mw=size)
                tool_results.append({"toolResult": {
                    "toolUseId": tool["toolUseId"],
                    "content": [{"json": last_result}],
                }})
        messages.append({"role": "user", "content": tool_results})
