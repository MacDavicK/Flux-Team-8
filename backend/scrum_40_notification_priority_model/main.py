import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scrum_40_notification_priority_model.routes import priority_router

app = FastAPI(
    title="Notification Priority Model API",
    description="""## Notification Priority Model API

Manages notification **priority scoring** and **escalation timing** calculations
for the Flux Life Assistant platform.

### Priority Levels
| Level | Value | Description |
|-------|-------|-------------|
| Standard | `standard` | Normal-priority notifications |
| Important | `important` | Elevated-priority notifications |
| Must-Not-Miss | `must_not_miss` | Critical-priority notifications |

### Speed Multipliers
Control how fast escalation windows shrink:
- **1x** - Default timing
- **5x** - Accelerated escalation
- **10x** - Maximum speed""",
    version="1.0.0",
    contact={"name": "Flux Team 8"},
    openapi_tags=[
        {"name": "Notification Priority", "description": "Compute priority scores and escalation timing."},
        {"name": "Health", "description": "Service health endpoints."},
    ],
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(priority_router)

@app.get("/", tags=["Health"], summary="API root", description="Returns service info and links to docs.")
async def root():
    return {"service": "Notification Priority Model API", "version": "1.0.0", "docs": "/docs", "redoc": "/redoc", "openapi": "/openapi.json"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8040, reload=True)
