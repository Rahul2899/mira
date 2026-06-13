from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import run_agent, run_local
from topsis import run_topsis_optimization

app = FastAPI(title="Autonomous Siting Engine Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    prompt: str


@app.post("/optimize_site")
def optimize_site(payload: SitingParameters):
    args = payload.model_dump()
    size = args.pop("size_mw")
    result = run_topsis_optimization(args, size_mw=size)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/ask_agent")
def ask_agent(req: AgentRequest):
    try:
        return {**run_agent(req.prompt), "source": "live"}
    except Exception:
        return {**run_local(req.prompt), "source": "offline"}


@app.get("/_diag")
def diag():
    """Temporary: surfaces why Bedrock falls back (no secrets exposed)."""
    import os
    k = os.environ.get("AWS_ACCESS_KEY_ID", "")
    sec = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    info = {
        "has_key": bool(k),
        "key_fingerprint": (k[:4] + "..." + k[-4:]) if k else None,
        "secret_length": len(sec),  # a valid AWS secret is exactly 40 chars
        "secret_tail": ("..." + sec[-4:]) if sec else None,  # compare with local (...2/Aw)
        "aws_region_env": os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION"),
        "model_id": os.environ.get("BEDROCK_MODEL_ID", "(default)"),
    }
    try:
        run_agent("test")
        info["bedrock"] = "OK — live call succeeded"
    except Exception as e:
        info["bedrock_error"] = f"{type(e).__name__}: {str(e)[:300]}"
    return info


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True))
