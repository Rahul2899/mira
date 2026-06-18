import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import run_agent, run_local
from topsis import run_topsis_optimization

app = FastAPI(title="Autonomous Siting Engine Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

AGENT_RATE_LIMIT = 10
AGENT_RATE_WINDOW = 60
_agent_hits = {}


def check_agent_rate(request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    hits = _agent_hits.setdefault(ip, deque())
    while hits and hits[0] <= now - AGENT_RATE_WINDOW:
        hits.popleft()
    if len(hits) >= AGENT_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests, slow down a moment.")
    hits.append(now)


@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


class SitingParameters(BaseModel):
    weight_cost: float = Field(..., ge=0.0, le=1.0)
    weight_green: float = Field(..., ge=0.0, le=1.0)
    weight_grid: float = Field(..., ge=0.0, le=1.0)
    weight_connectivity: float = Field(..., ge=0.0, le=1.0)
    size_mw: float | None = Field(None, gt=0.0)


class AgentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


@app.post("/optimize_site")
def optimize_site(payload: SitingParameters):
    args = payload.model_dump()
    size = args.pop("size_mw")
    result = run_topsis_optimization(args, size_mw=size)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/ask_agent")
def ask_agent(req: AgentRequest, request: Request):
    check_agent_rate(request)
    try:
        return {**run_agent(req.prompt), "source": "live"}
    except Exception:
        return {**run_local(req.prompt), "source": "offline"}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True))
