from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select
from twilio.rest import Client

from .frappe_bridge import log_call as log_call_frappe
from .frappe_bridge import update_lead_status as update_lead_status_frappe
from .models import CallLog, Lead


class TwilioCaller:
	def __init__(self, account_sid: str, auth_token: str, from_number: str):
		self.client = Client(account_sid, auth_token)
		self.from_number = from_number

	async def place_call(self, lead: Lead, webhook_url: str) -> str | None:
		"""Place a call via Twilio."""
		try:
		    call = self.client.calls.create(
		        to=lead.phone_number,
		        from_=self.from_number,
		        url=webhook_url,
		    )
		    return call.sid
		except Exception:
		    return None


def log_call(
       session: Session,
       lead_id: int,
       status: str,
       duration: int | None = None,
       *,
       call_sid: str | None = None,
       from_number: str | None = None,
       to_number: str | None = None,
) -> None:
       call_log = CallLog(lead_id=lead_id, status=status, duration=duration)
       session.add(call_log)
       session.commit()

       lead = session.exec(select(Lead).where(Lead.id == lead_id)).one()
       if lead.frappe_name and call_sid and from_number and to_number:
               log_call_frappe(call_sid, lead.frappe_name, from_number, to_number, status, duration)


def update_lead_status(session: Session, lead_id: int, status: str) -> None:
       lead = session.exec(select(Lead).where(Lead.id == lead_id)).one()
       lead.status = status
       session.add(lead)
       session.commit()

       if lead.frappe_name:
               update_lead_status_frappe(lead.frappe_name, status)
