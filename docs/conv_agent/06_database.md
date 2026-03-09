# Database Schema

Changes to support voice conversations and per-message storage. No changes from the direct-connection architecture shift — the database schema is the same regardless of whether audio flows through the backend or directly to Deepgram.

---

## New Table: `messages`

Stores individual messages from voice (and future text) conversations. Each `ConversationText` event from Deepgram becomes a row, persisted via the client calling `POST /api/v1/voice/messages`.

```sql
-- Stores individual messages for voice and text conversations
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'function')),
    content         TEXT NOT NULL,
    input_modality  TEXT NOT NULL DEFAULT 'text' CHECK (input_modality IN ('voice', 'text')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
```

**Fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID (FK) | Links to conversations table |
| `role` | text | `user`, `assistant`, `system`, or `function` |
| `content` | text | Transcript text or function call result |
| `input_modality` | text | `voice` or `text` — how the message originated |
| `metadata` | JSONB | Extra data (e.g., function call details, latency metrics) |
| `created_at` | timestamptz | When the message was persisted |

---

## Changes to `conversations` Table

Add columns to track voice session state and extracted intents.

```sql
-- New columns for voice session tracking
ALTER TABLE conversations ADD COLUMN voice_session_id  TEXT;
ALTER TABLE conversations ADD COLUMN extracted_intent   TEXT;
ALTER TABLE conversations ADD COLUMN intent_payload     JSONB;
ALTER TABLE conversations ADD COLUMN linked_goal_id     UUID REFERENCES goals(id);
ALTER TABLE conversations ADD COLUMN linked_task_id     UUID REFERENCES tasks(id);
ALTER TABLE conversations ADD COLUMN ended_at           TIMESTAMPTZ;
ALTER TABLE conversations ADD COLUMN duration_seconds   INT;
```

**New columns:**
| Column | Type | Purpose |
|--------|------|---------|
| `voice_session_id` | text | Backend-generated session ID for the voice session |
| `extracted_intent` | text | The intent that was extracted (GOAL, NEW_TASK, RESCHEDULE_TASK) |
| `intent_payload` | JSONB | The full payload sent to the Orchestrator |
| `linked_goal_id` | UUID (FK) | Goal created from this conversation |
| `linked_task_id` | UUID (FK) | Task created from this conversation |
| `ended_at` | timestamptz | When the session ended |
| `duration_seconds` | int | Total session duration |

---

## Update `context_type` Constraint

The existing `conversations` table has a `context_type` check constraint. Add `'voice'`:

```sql
ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_context_type_check;
ALTER TABLE conversations ADD CONSTRAINT conversations_context_type_check
    CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule', 'voice'));
```

---

## SQLAlchemy Model: Message

Add to `backend/dao_service/models/`:

```python
class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = mapped_column(String, nullable=False)  # user, assistant, system, function
    content = mapped_column(Text, nullable=False)
    input_modality = mapped_column(String, nullable=False, default="text")  # voice, text
    metadata_ = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    conversation = relationship("Conversation", back_populates="message_list")
```

Update the `Conversation` model:

```python
# Add to existing Conversation model
voice_session_id = mapped_column(String, nullable=True)
extracted_intent = mapped_column(String, nullable=True)
intent_payload = mapped_column(JSONB, nullable=True)
linked_goal_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("goals.id"), nullable=True)
linked_task_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
ended_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
duration_seconds = mapped_column(Integer, nullable=True)

# Relationship to messages
message_list = relationship("Message", back_populates="conversation", order_by="Message.created_at")
```

---

## Pydantic Schemas

```python
class MessageCreate(BaseModel):
    conversation_id: UUID
    role: str  # user, assistant, system, function
    content: str
    input_modality: str = "voice"
    metadata: dict = {}

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    input_modality: str
    metadata: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## Migration Notes

- Run the `CREATE TABLE messages` statement first
- Then run the `ALTER TABLE conversations` statements
- Update SQLAlchemy models and regenerate any Alembic migrations if using that workflow
- The existing `conversations.messages` JSONB column (used by GoalPlannerAgent) is separate and unaffected
