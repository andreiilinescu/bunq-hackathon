from typing import Any

from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_environment_type import ApiEnvironmentType

from pydantic import BaseModel
import os
from agents import function_tool, RunContextWrapper

BUNQ_API_KEY = os.getenv("BUNQ_API_KEY")  # production or sandbox key
DEVICE_DESCRIPTION = os.getenv("DEVICE_DESC", "Finn‑CLI")
ENV = ApiEnvironmentType.SANDBOX  # swap to .SANDBOX for tests


_api_context = ApiContext.create(ENV, BUNQ_API_KEY, DEVICE_DESCRIPTION)
_api_context.ensure_session_active()  # log in / refresh session
_api_context.save()  # cache token & device cert
BunqContext.load_api_context(_api_context)

_user_context = BunqContext.user_context()
# ------------------------------------------------------------------------------
# 1.  Shared conversation context model
# ------------------------------------------------------------------------------


class BunqAgentContext(BaseModel):
    current_account_id: str | None = None  # chosen account for this turn
    pending_payment: dict[str, Any] | None = None  # {'from': id, 'to': id, ...}
    last_fx_pair: tuple[str, str] | None = None  # (base, target)


# ------------------------------------------------------------------------------
# 2.  Low‑level Bunq helpers (thin wrappers around SDK)
# ------------------------------------------------------------------------------


def _monetary_accounts() -> list:  # → [MonetaryAccountBank, …]
    from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject

    try:
        return MonetaryAccountBankApiObject.list().value
    except Exception as e:
        return []


def _account_balance(account_id: str) -> str:
    from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject

    acc = MonetaryAccountBankApiObject.get(account_id).value
    # Each MonetaryAccountBank has a balance object in .balance.value
    return acc.balance.value  # e.g. '1234.56'


# ------------------------------------------------------------------------------
# 3.  Tool definitions (decorated so agents can call them)
# ------------------------------------------------------------------------------


@function_tool
def list_bunq_accounts() -> str:
    accounts = _monetary_accounts()
    lines = [f"{acc.id_}: {acc.description}" for acc in accounts]
    return "\n".join(lines) if lines else "No accounts found."


@function_tool
def get_bunq_balance(account_id: str) -> str:
    balance = _account_balance(account_id)
    return f"Balance for {account_id}: €{balance}"


@function_tool
def get_transaction_history(account_id: str, limit: int = 10) -> str:
    from bunq.sdk.model.generated.endpoint import PaymentApiObject
    from bunq import Pagination

    pagination = Pagination()
    pagination.count = limit
    txs = PaymentApiObject.list(account_id, pagination.url_params_count_only).value
    out = [f"{tx.created}: {tx.amount.value} – {tx.description}" for tx in txs[:limit]]
    return "\n".join(out) or "No transactions."


@function_tool
def create_payment(
    context: RunContextWrapper[BunqAgentContext],
    from_account: str,
    to_alias: str,
    amount: float,
    currency: str = "EUR",
    *,
    alias_type: str | None = None,  # 'IBAN' | 'EMAIL' | 'PHONE_NUMBER'
    description: str | None = None,
    merchant_reference: str | None = None,
    allow_bunqto: bool | None = None,
    attachment_ids: list[int] | None = None,
) -> str:
    """
    Send money from *from_account* to *to_alias* (IBAN, email or phone).

    • Automatically infers alias type when not given.
    • Surfaces Bunq API errors to the user instead of crashing.
    """
    from bunq.sdk.model.generated.endpoint import PaymentApiObject
    from bunq.sdk.model.generated.object_ import AmountObject, PointerObject
    import re

    # ------------------------------------------------------------------
    # 1️⃣  Determine the pointer type
    # ------------------------------------------------------------------
    def _guess_pointer_type(val: str) -> str:
        if re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$", val.replace(" ", "")):
            return "IBAN"
        if "@" in val:
            return "EMAIL"
        return "PHONE_NUMBER"

    p_type = (alias_type or _guess_pointer_type(to_alias)).upper()

    # ------------------------------------------------------------------
    # 2️⃣  Build SDK objects
    # ------------------------------------------------------------------
    amount_obj = AmountObject(str(amount), currency)
    counterparty = PointerObject(p_type, to_alias, "Counterparty")

    # ------------------------------------------------------------------
    # 3️⃣  Call Bunq
    # ------------------------------------------------------------------
    try:
        payment = PaymentApiObject.create(
            amount=amount_obj,
            counterparty_alias=counterparty,
            description=description or "",
            attachment=attachment_ids or None,
            merchant_reference=merchant_reference,
            allow_bunqto=allow_bunqto,
            monetary_account_id=from_account,
        ).value

        context.context.pending_payment = None  # clear draft
        return (
            f"✅ Payment {payment.id_} executed!\n"
            f"• Amount : {payment.amount.value} {payment.amount.currency}\n"
            f"• From   : {from_account}\n"
            f"• To     : {to_alias} ({p_type})\n"
            f"• Desc.  : {payment.description or '—'}"
            "\n\nThis is not financial advice."
        )

    except Exception as e:
        err_msg = "; ".join(err.error_description for err in e.error)
        return f"❌ Payment failed: {err_msg}"


@function_tool
def get_exchange_rate(base_currency: str, target_currency: str) -> str:
    # Placeholder → plug your preferred FX API here
    dummy_rate = 1.08 if (base_currency, target_currency) == ("EUR", "USD") else 0.92
    return f"1 {base_currency} = {dummy_rate} {target_currency}"
