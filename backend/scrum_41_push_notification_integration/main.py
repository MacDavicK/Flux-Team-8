import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scrum_41_push_notification_integration.routes import router

app = FastAPI(
    title="Push Notification Integration API",
    description="""## Push Notification Integration API

Manages **Web Push Notifications** using the VAPID protocol for the Flux Life Assistant.

### Features
- Send push notifications to subscribed devices
- Manage push notification subscriptions (subscribe / unsubscribe)
- Retrieve VAPID public key for client-side subscription setup

### VAPID Flow
1. Client fetches VAPID public key via `GET /vapid-public-key`
2. Client subscribes via browser Push API and sends subscription to `POST /subscribe`
3. Server sends push notifications via `POST /` using stored subscriptions""",
    version="1.0.0",
    contact={"name": "Flux Team 8"},
    openapi_tags=[
        {"name": "push-notifications", "description": "Send and manage Web Push Notifications."},
        {"name": "Health", "description": "Service health endpoints."},
    ],
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/", tags=["Health"], summary="API root", description="Returns service info and links to docs.")
async def root():
    return {"service": "Push Notification Integration API", "version": "1.0.0", "docs": "/docs", "redoc": "/redoc", "openapi": "/openapi.json"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8041, reload=True)
