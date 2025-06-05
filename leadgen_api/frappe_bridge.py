import os
from contextlib import contextmanager

try:
    import frappe
except Exception:  # pragma: no cover - frappe not installed during tests
    frappe = None


@contextmanager
def frappe_context():
    """Connect to a Frappe site if configured."""
    if not frappe:
        yield False
        return

    site = os.environ.get("FRAPPE_SITE")
    if not site:
        yield False
        return

    frappe.init(site=site)
    frappe.connect()
    try:
        yield True
    finally:
        frappe.destroy()


def create_lead(name: str, phone_number: str, context: str | None = None) -> str | None:
    """Create a CRM Lead in Frappe and return its name."""
    with frappe_context() as active:
        if not active:
            return None

        doc = frappe.get_doc({
            "doctype": "CRM Lead",
            "lead_name": name,
            "mobile_no": phone_number,
            "source": context or "Leadgen",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name


def log_call(
    call_sid: str,
    lead_name: str,
    from_number: str,
    to_number: str,
    status: str,
    duration: int | None = None,
) -> None:
    """Create or update a CRM Call Log in Frappe."""
    with frappe_context() as active:
        if not active:
            return

        if frappe.db.exists("CRM Call Log", call_sid):
            frappe.db.set_value("CRM Call Log", call_sid, "status", status)
            if duration is not None:
                frappe.db.set_value("CRM Call Log", call_sid, "duration", duration)
            frappe.db.commit()
            return

        doc = frappe.get_doc({
            "doctype": "CRM Call Log",
            "name": call_sid,
            "id": call_sid,
            "from": from_number,
            "to": to_number,
            "type": "Outgoing",
            "status": status,
            "telephony_medium": "Twilio",
            "reference_doctype": "CRM Lead",
            "reference_docname": lead_name,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()


def update_lead_status(lead_name: str, status: str) -> None:
    """Update the status of a CRM Lead."""
    with frappe_context() as active:
        if not active:
            return

        if frappe.db.exists("CRM Lead", lead_name):
            frappe.db.set_value("CRM Lead", lead_name, "status", status)
            frappe.db.commit()
