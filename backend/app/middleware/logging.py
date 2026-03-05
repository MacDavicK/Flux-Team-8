"""
16.2 — Structured Logging (app/middleware/logging.py) — §14

structlog configuration + correlation ID middleware.
"""
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 16.2.1 — Configure structlog with standard processors
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)


class StructlogMiddleware(BaseHTTPMiddleware):
    """
    16.2.2 — Generates a correlation_id UUID per request.
    Binds it to the structlog context and adds X-Correlation-ID response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = str(uuid.uuid4())

        # Bind to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
        )

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
