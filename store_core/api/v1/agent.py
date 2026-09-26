"""Delivery agent actions: /api/method/store_core.api.v1.agent.update_status

Used by the /agent page. Login required; an agent can only move their own assignments and only
through the agent transitions (Confirmed -> Out for Delivery -> Delivered / Returned).
"""

import frappe
from frappe import _
from frappe.utils import flt

from store_core.utils import status_machine as sm


@frappe.whitelist(methods=["POST"])
def update_status(
	assignment: str, status: str, collected_amount: str | float | None = None, notes: str | None = None
):
	frappe.only_for(("Lamsa Delivery Agent", "System Manager"))
	doc = frappe.get_doc("Delivery Assignment", assignment)
	agent_user = frappe.db.get_value("Delivery Agent", doc.agent, "user") if doc.agent else None
	if agent_user != frappe.session.user and "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError(_("This delivery is not assigned to you"))
	if not sm.is_agent_transition(doc.status, status):
		frappe.local.response.http_status_code = 422
		return {
			"ok": False,
			"error": {"code": "invalid_transition", "message": _("This status change is not allowed")},
		}

	doc.status = status
	if status == sm.DELIVERED:
		doc.collected_amount = (
			flt(collected_amount) if collected_amount not in (None, "") else doc.expected_amount
		)
	if notes:
		doc.notes = "\n".join(filter(None, [doc.notes, str(notes)[:500]]))
	doc.flags.ignore_permissions = True
	doc.save()
	return {"ok": True, "status": doc.status}
