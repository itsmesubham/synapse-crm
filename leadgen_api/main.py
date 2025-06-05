from __future__ import annotations

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from .calling import TwilioCaller, log_call, update_lead_status
from .database import get_session, init_db
from .frappe_bridge import create_lead
from .models import Campaign, Lead

app = FastAPI(title="AI Lead Generation")

init_db()

twilio_caller: TwilioCaller | None = None
SessionDep = Depends(get_session)


@app.post("/setup_twilio")
async def setup_twilio(account_sid: str, auth_token: str, from_number: str):
	global twilio_caller
	twilio_caller = TwilioCaller(account_sid, auth_token, from_number)
	return {"status": "configured"}


@app.post("/leads")
async def upload_leads(leads: list[Lead], session: Session = SessionDep):
       for lead in leads:
           lead.frappe_name = create_lead(lead.name, lead.phone_number, lead.context)
           session.add(lead)
       session.commit()
       return {"added": len(leads)}


@app.post("/campaigns")
async def create_campaign(campaign: Campaign, session: Session = SessionDep):
	session.add(campaign)
	session.commit()
	session.refresh(campaign)
	return campaign


@app.post("/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: int, background: BackgroundTasks, session: Session = SessionDep):
	campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).one_or_none()
	if not campaign:
	    raise HTTPException(status_code=404, detail="Campaign not found")
	leads = session.exec(select(Lead).where(Lead.campaign_id == campaign_id)).all()
	for lead in leads:
	    background.add_task(place_call_task, lead.id, campaign_id)
	return {"started": len(leads)}


async def place_call_task(lead_id: int, campaign_id: int):
       if not twilio_caller:
           return
       with next(get_session()) as session:
           lead = session.exec(select(Lead).where(Lead.id == lead_id)).one()
           webhook_url = f"/voice/intro?lead_id={lead.id}&campaign_id={campaign_id}"
           call_sid = await twilio_caller.place_call(lead, webhook_url)
           if not call_sid:
                log_call(session, lead.id, "call_failed")
                update_lead_status(session, lead.id, "failed")
           else:
                log_call(
                    session,
                    lead.id,
                    "Initiated",
                    call_sid=call_sid,
                    from_number=twilio_caller.from_number,
                    to_number=lead.phone_number,
                )


@app.post("/voice/intro")
async def voice_intro(lead_id: int, campaign_id: int, session: Session = SessionDep):
	campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).one()
	lead = session.exec(select(Lead).where(Lead.id == lead_id)).one()
	say_text = campaign.call_script.format(name=lead.name, context=lead.context or "")
	twiml = f"""<Response><Gather action='/voice/handle?lead_id={lead.id}' numDigits='1'><Say>{say_text}</Say></Gather><Say>No input received. Goodbye!</Say></Response>"""
	return Response(content=twiml, media_type="text/xml")


@app.post("/voice/handle")
async def voice_handle(lead_id: int, digits: str = "", session: Session = SessionDep):
       if digits == "1":
           update_lead_status(session, lead_id, "Qualified")
           log_call(session, lead_id, "Completed")
           return RedirectResponse(url="/voice/transfer")
       elif digits == "2":
           update_lead_status(session, lead_id, "Unqualified")
           log_call(session, lead_id, "Completed")
           return "<Response><Say>Thank you. Goodbye!</Say></Response>"
       else:
           update_lead_status(session, lead_id, "Contacted")
           log_call(session, lead_id, "No Answer")
           return "<Response><Say>No input received. Goodbye!</Say></Response>"
