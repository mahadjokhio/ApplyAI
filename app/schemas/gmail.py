from pydantic import BaseModel, Field


class GmailSyncRequest(BaseModel):
    message_ids: list[str] = Field(default_factory=list)