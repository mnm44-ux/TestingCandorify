"""Editable letter templates.

Two templates:
  request_itemized_bill  -- ask a provider for a fully itemized statement
  dispute_charge         -- raise specific line items for the provider to review

Rendering uses safe ``str.format_map`` with a default that leaves unknown
placeholders visible (so the user can fill them in), and every field has a
friendly default. Output is plain text the user can freely edit before sending.
"""
from __future__ import annotations

from dataclasses import dataclass


class _Default(dict):
    def __missing__(self, key: str) -> str:  # keep unknown placeholders visible
        return "[" + key.replace("_", " ") + "]"


@dataclass
class Template:
    key: str
    label: str
    subject: str
    body: str


_TEMPLATES: dict[str, Template] = {
    "request_itemized_bill": Template(
        key="request_itemized_bill",
        label="Request an itemized bill",
        subject="Request for a fully itemized bill — account {account_number}",
        body=(
            "Dear {provider_name} Billing Department,\n\n"
            "I am writing to request a fully itemized bill for services provided to "
            "{patient_name} on {service_date} (account number {account_number}).\n\n"
            "Please include, for each charge: the procedure or service code (CPT/HCPCS), "
            "a description, the date of service, the quantity, and the unit price. "
            "I would like to review each line before making payment.\n\n"
            "Please send the itemized statement to {patient_contact}. "
            "Thank you for your help.\n\n"
            "Sincerely,\n{patient_name}"
        ),
    ),
    "dispute_charge": Template(
        key="dispute_charge",
        label="Dispute a charge",
        subject="Request to review specific charges — account {account_number}",
        body=(
            "Dear {provider_name} Billing Department,\n\n"
            "After reviewing the itemized bill for {patient_name} (account "
            "{account_number}, date of service {service_date}), I have some questions "
            "about the following items that I would like you to review:\n\n"
            "{items_block}\n"
            "I am not asserting that these are errors; I am asking for clarification "
            "before I make payment. Please confirm whether each item is correct, and "
            "provide a corrected statement if any adjustment is warranted.\n\n"
            "Please reply to {patient_contact}. Thank you for your time.\n\n"
            "Sincerely,\n{patient_name}"
        ),
    ),
}


def available_templates() -> list[dict]:
    return [{"key": t.key, "label": t.label} for t in _TEMPLATES.values()]


def _build_items_block(context: dict) -> str:
    """Turn a list of item dicts into a readable bulleted block."""
    items = context.get("items") or []
    if not items:
        return "- [describe the charge(s) you want reviewed]\n"
    lines = []
    for it in items:
        code = it.get("code", "")
        desc = it.get("description", "")
        note = it.get("note", "please confirm this charge")
        amount = it.get("line_total")
        amount_str = f" (${amount:,.2f})" if isinstance(amount, (int, float)) else ""
        lines.append(f"- {code} {desc}{amount_str}: {note}")
    return "\n".join(lines) + "\n"


def render_template(template_key: str, context: dict | None = None) -> Template:
    context = dict(context or {})
    tmpl = _TEMPLATES.get(template_key)
    if tmpl is None:
        raise KeyError(f"Unknown template: {template_key}")

    if template_key == "dispute_charge":
        context["items_block"] = _build_items_block(context)

    data = _Default(context)
    return Template(
        key=tmpl.key,
        label=tmpl.label,
        subject=tmpl.subject.format_map(data),
        body=tmpl.body.format_map(data),
    )
