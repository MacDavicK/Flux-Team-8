import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scrum_43_phone_call_trigger.routes import router

app = FastAPI(
    title="Phone Call Trigger API",
    description="""## Phone Call Trigger API

Triggers **outbound phone calls** via Twilio for the Flux Life Assistant escalation pipeline.

### Features
- Initiate automated phone calls with TTS task reminders
- Handle Twilio webhooks for call status and DTMF input
- Track acknowledgements via digit press (press 1 to acknowledge)

### Call Flow
1. Client calls `POST /calls/trigger` to initiate a call
2. Twilio dials the target number and plays a TTS message
3. User presses `1` to acknowledge
4. Twilio sends DTMF callback to `POST /calls/gather`
5. Call status updates are sent to `POST /calls/status`""",
    version="1.0.0",
    contact={"name": "Flux Team 8"},
    openapi_tags=[
        {"name": "phone-calls", "description": "Phone call triggering and webhook endpoints."},
        {"name": "Health", "description": "Service health endpoints."},
    ],
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/", tags=["Health"], summary="API root", description="Returns service info and links to docs.")
async def root():
    return {"service": "Phone Call Trigger API", "version": "1.0.0", "docs": "/docs", "redoc": "/redoc", "openapi": "/openapi.json"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8043, reload=True)
