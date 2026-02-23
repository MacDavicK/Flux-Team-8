"""FastAPI routes for phone call trigger API."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.base.exceptions import TwilioRestException

from .models import CallRequest, CallResponse, GatherResponse
from .service import TwilioCallService

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/notifications/call",
    tags=["phone-calls", "notifications"]
)

# Initialize Twilio service
try:
    twilio_service = TwilioCallService()
except ValueError as e:
    logger.error(f"Failed to initialize Twilio service: {e}")
    twilio_service = None


@router.post("", response_model=CallResponse, status_code=201)
async def initiate_call(call_request: CallRequest, request: Request) -> CallResponse:
    """Initiate a phone call with TTS message and gather user input.
    
    **Endpoint:** `POST /notifications/call`
    
    **SCRUM-43 Requirements:**
    - Integrates Twilio Voice API
    - Makes call to configured phone number
    - Plays TTS message with task title
    - Gathers DTMF input (digit '1') for acknowledgment
    
    Args:
        call_request: Phone number and task details
        request: FastAPI request object for building callback URLs
    
    Returns:
        CallResponse with call SID and status
    
    Raises:
        HTTPException: If Twilio service is not initialized or call fails
    """
    if not twilio_service:
        raise HTTPException(
            status_code=503,
            detail="Twilio service not initialized. Check environment variables."
        )
    
    try:
        # Get base URL from request
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        # Initiate the call
        response = twilio_service.initiate_call(call_request, base_url)
        
        logger.info(
            f"Call initiated: SID={response.call_sid}, "
            f"to={response.to}, task={call_request.task_title}"
        )
        
        return response
        
    except TwilioRestException as e:
        logger.error(f"Twilio API error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.post("/twiml", response_class=Response)
async def generate_twiml(
    request: Request,
    task_title: str,
    task_id: Optional[str] = None
) -> Response:
    """Generate TwiML response with TTS message and gather input.
    
    This endpoint is called by Twilio when the call is answered.
    It generates TwiML that:
    1. Plays a TTS message with the task title
    2. Gathers DTMF input (pressing 1) for acknowledgment
    3. Redirects to /gather endpoint to process the input
    
    Args:
        request: FastAPI request
        task_title: Title of the task to announce
        task_id: Optional task ID for tracking
    
    Returns:
        TwiML XML response
    """
    response = VoiceResponse()
    
    # Create TTS message per SCRUM-43 requirements
    message = (
        f"Hi! This is Flux. You have a critical task: {task_title}. "
        "Press 1 to acknowledge."
    )
    
    # Build gather URL with parameters
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    gather_url = f"{base_url}/notifications/call/gather"
    if task_id:
        gather_url += f"?task_id={task_id}"
    
    # Gather DTMF input
    gather = Gather(
        num_digits=1,
        action=gather_url,
        method="POST",
        timeout=10
    )
    gather.say(message, voice="alice", language="en-US")
    response.append(gather)
    
    # If no input received, thank and hangup
    response.say("Thank you. Goodbye.", voice="alice", language="en-US")
    
    logger.info(f"TwiML generated for task: {task_title}")
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/gather", response_class=Response)
async def handle_gather(
    request: Request,
    Digits: Optional[str] = Form(None),
    CallSid: str = Form(...),
    task_id: Optional[str] = None
) -> Response:
    """Handle gathered DTMF input from user.
    
    This endpoint is called by Twilio after the user presses a digit.
    If the user presses '1', the task is marked as acknowledged.
    
    Args:
        request: FastAPI request
        Digits: The digit(s) pressed by the user
        CallSid: Twilio Call SID
        task_id: Optional task ID for tracking
    
    Returns:
        TwiML response confirming or rejecting acknowledgment
    """
    response = VoiceResponse()
    
    acknowledged = False
    
    if Digits == "1":
        # User pressed 1 to acknowledge
        response.say(
            "Thank you. Task acknowledged. Goodbye.",
            voice="alice",
            language="en-US"
        )
        acknowledged = True
        logger.info(f"Task acknowledged: CallSid={CallSid}, TaskId={task_id}")
        
        # TODO: Integrate with task management system to mark task as acknowledged
        # This would typically involve calling another service or updating a database
        
    else:
        # User pressed something other than 1 or timeout
        response.say(
            "No acknowledgment received. Goodbye.",
            voice="alice",
            language="en-US"
        )
        logger.info(f"Task not acknowledged: CallSid={CallSid}, Digits={Digits}")
    
    # Store gather response data
    gather_response = GatherResponse(
        call_sid=CallSid,
        digits=Digits,
        task_id=task_id,
        acknowledged=acknowledged
    )
    
    # Log the response for tracking
    logger.info(f"Gather response: {gather_response.dict()}")
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def handle_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: Optional[int] = Form(None)
):
    """Handle call status callbacks from Twilio.
    
    This endpoint receives status updates for calls (completed, failed, etc.)
    
    Args:
        CallSid: Twilio Call SID
        CallStatus: Current status of the call
        CallDuration: Duration of the call in seconds
    
    Returns:
        Success message
    """
    logger.info(
        f"Call status update: SID={CallSid}, "
        f"Status={CallStatus}, Duration={CallDuration}s"
    )
    
    return {"status": "received", "call_sid": CallSid}
