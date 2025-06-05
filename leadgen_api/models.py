from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Lead(SQLModel, table=True):
       id: int | None = Field(default=None, primary_key=True)
       name: str
       phone_number: str
       context: str | None = None
       status: str = "pending"  # pending, interested, not_interested, failed, no_answer
       campaign_id: int | None = Field(default=None, foreign_key="campaign.id")
       frappe_name: str | None = None

class Campaign(SQLModel, table=True):
	id: int | None = Field(default=None, primary_key=True)
	title: str
	description: str
	call_script: str
	created_at: datetime = Field(default_factory=datetime.utcnow)

class CallLog(SQLModel, table=True):
	id: int | None = Field(default=None, primary_key=True)
	lead_id: int = Field(foreign_key="lead.id")
	status: str
	duration: int | None = None
	updated_at: datetime = Field(default_factory=datetime.utcnow)
