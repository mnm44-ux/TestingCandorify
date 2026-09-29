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

from ..llm import LLMUnavailable, get_llm_client


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


# Guardrails the AI MUST follow when polishing a letter. These protect the
# product's core principle: never assert an error, never claim savings.
_AI_GUARDRAILS = (
    "STRICT RULES:\n"
    "- Keep a polite, professional, non-accusatory tone.\n"
    "- Do NOT assert that any charge is an error, fraud, or an overcharge.\n"
    "- Do NOT promise or imply savings or a specific outcome.\n"
    "- Only request clarification / review before payment.\n"
    "- Keep all facts (names, dates, account number, codes, amounts) exactly as given.\n"
    "- Return only the letter body text, no preamble or markdown."
)


def _ai_polish(template_key: str, base_body: str, context: dict, llm_client) -> str | None:
    """Ask Gemini to polish the base letter. Returns the new body, or None if
    the AI is unavailable (caller then keeps the template body)."""
    client = llm_client if llm_client is not None else get_llm_client()
    kind = "request for a fully itemized bill" if template_key == "request_itemized_bill" \
        else "request for the provider to review specific charges"
    prompt = (
        f"Rewrite the following patient letter (a {kind}) so it reads naturally "
        f"and personally, while preserving its meaning.\n\n{_AI_GUARDRAILS}\n\n"
        f"LETTER TO REWRITE:\n{base_body}"
    )
    try:
        text = client.generate(prompt, temperature=0.4, max_tokens=600)
    except LLMUnavailable:
        return None
    return text.strip() or None


def render_template(
    template_key: str,
    context: dict | None = None,
    use_ai: bool = False,
    llm_client=None,
) -> Template:
    context = dict(context or {})
    tmpl = _TEMPLATES.get(template_key)
    if tmpl is None:
        raise KeyError(f"Unknown template: {template_key}")

    if template_key == "dispute_charge":
        context["items_block"] = _build_items_block(context)

    data = _Default(context)
    subject = tmpl.subject.format_map(data)
    body = tmpl.body.format_map(data)

    # Optional AI polish. The safe template is always the baseline and the
    # fallback, so drafting never fails even if Gemini is down or unconfigured.
    if use_ai:
        polished = _ai_polish(template_key, body, context, llm_client)
        if polished:
            body = polished

    return Template(key=tmpl.key, label=tmpl.label, subject=subject, body=body)
