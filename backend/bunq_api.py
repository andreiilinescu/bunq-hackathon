from typing import Any

from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_environment_type import ApiEnvironmentType
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject
from bunq.sdk.model.generated.endpoint import (
    BunqMeTabApiObject,
    BunqMeTabEntryApiObject,
)

from bunq import Pagination
from pydantic import BaseModel
import os
from agents import function_tool, RunContextWrapper
import re
from dotenv import load_dotenv
import requests
import time

load_dotenv()

BUNQ_API_KEY = os.getenv("BUNQ_API_KEY")  # production or sandbox key
DEVICE_DESCRIPTION = os.getenv("DEVICE_DESC", "Finn‑CLI")
ENV = ApiEnvironmentType.SANDBOX  # swap to .SANDBOX for tests

time.sleep(3)
print("Loading bunq API context...")
_api_context = ApiContext.create(ENV, BUNQ_API_KEY, DEVICE_DESCRIPTION)
_api_context.ensure_session_active()  # log in / refresh session
_api_context.save()  # cache token & device cert
# time.sleep(3)
BunqContext.load_api_context(_api_context)
# time.sleep(3)
_user_context = BunqContext.user_context()
# time.sleep(3)
accounts = MonetaryAccountBankApiObject.list().value
# ------------------------------------------------------------------------------
# 1.  Shared conversation context model
# ------------------------------------------------------------------------------


class BunqAgentContext(BaseModel):
    accounts: list[dict[str, Any]] = accounts  # [{'id': id, 'description': desc}, ...]
    user_id: str | None = _user_context.user_id  # current user id
    user_name: str | None = _user_context.user_person.display_name  # current user name
    user_nationality: str | None = _user_context.user_person.nationality  # current
    preffered_currency: str | None = "EUR"  # default currency
    current_account_id: str | None = None  # chosen account for this turn
    pending_payment: dict[str, Any] | None = None  # {'from': id, 'to': id, ...}
    last_fx_pair: tuple[str, str] | None = None  # (base, target)


# ------------------------------------------------------------------------------
# 2.  Low‑level Bunq helpers (thin wrappers around SDK)
# ------------------------------------------------------------------------------


def _monetary_accounts() -> list:  # → [MonetaryAccountBank, …]
    try:
        return MonetaryAccountBankApiObject.list().value
    except Exception as e:
        return []


def _account_balance(account_id: str) -> str:
    acc = MonetaryAccountBankApiObject.get(account_id).value
    # Each MonetaryAccountBank has a balance object in .balance.value
    return acc.balance.value  # e.g. '1234.56'


# ------------------------------------------------------------------------------
# 3.  Tool definitions (decorated so agents can call them)
# ------------------------------------------------------------------------------


@function_tool(
    description_override="Return a newline list of the user’s monetary accounts in the form "
    "‘<id>: <description>  • IBAN: NL…’.  No arguments."
)
def list_bunq_accounts(context: RunContextWrapper[BunqAgentContext]) -> str:
    accounts = _monetary_accounts()
    accounts = [
        {"account_id": acc.id_, "description": acc.description, "aliases": acc.alias}
        for acc in accounts
    ]
    for acc in accounts:
        for i, alias in enumerate(acc["aliases"]):
            acc["aliases"][i] = {
                "type": alias.type_,
                "value": alias.value,
            }
    context.context.accounts = accounts  # update context
    lines = []
    for acc in accounts:
        line = f"{acc['account_id']}: {acc['description']}"
        for alias in acc["aliases"]:
            line += f"  • {alias['type']}: {alias['value']}"
        lines.append(line)
    return "\n".join(lines) if lines else "No accounts found."


@function_tool(
    description_override="Resolve an account’s *description name* (e.g. “Travel”) to its numeric "
    "ID.  Args: account_name (str).  Returns “Account id: <id>” or "
    "“Account not found”.  Use this before other tools when you only have a "
    "name."
)
def get_bunq_account(account_name: str) -> str:
    """Get the id of a bunq account. Args: String account name (str). Returns 'Account id'."""
    accounts = _monetary_accounts()
    for acc in accounts:
        if acc.description == account_name:
            return f"Account id: {acc.id_}"
    return "Account not found."


@function_tool(
    description_override="Real‑time balance lookup.  Args: account_id (str).  Returns "
    "‘Balance for <id>: €<value>’."
)
def get_bunq_balance(account_id: str) -> str:
    """Look up the real-time balance of a bunq account. Args: account_id (str). Returns 'Balance for id: €value'."""
    balance = _account_balance(account_id)
    return f"Balance for {account_id}: €{balance}"


@function_tool(
    description_override="Fetch recent transactions.  Args: account_id (str), limit (int, default 10). "
    "Returns up to <limit> lines formatted "
    "‘YYYY‑MM‑DD: ±€amount – description’ newest→oldest."
)
def get_transaction_history(account_id: str, limit: int = 10) -> str:
    """Fetch recent transcations for an account. Args: account_id (str), limit (int, default 10). Returns up to <limit> lines formatted 'YYYY-MM-DD: ±€amount – description' sorted newest→oldest."""
    pagination = Pagination()
    pagination.count = limit
    txs = PaymentApiObject.list(account_id, pagination.url_params_count_only).value
    out = [f"{tx.created}: {tx.amount.value} – {tx.description}" for tx in txs[:limit]]
    return "\n".join(out) or "No transactions."


@function_tool(
    description_override="Send money. **Call only after the user explicitly confirmed.** "
    "Args: from_account (str ID), to_alias (IBAN/email/phone), amount (float), "
    "currency (str, default ‘EUR’), optional description. "
    "Returns a success receipt or error string."
)
def create_payment(
    context: RunContextWrapper[BunqAgentContext],
    from_account: str,
    to_alias: str,
    amount: float,
    currency: str = "EUR",
    alias_type: str | None = None,  # 'IBAN' | 'EMAIL' | 'PHONE_NUMBER'
    description: str | None = None,
) -> str:
    """
    If a transfer to a bunqto alias fails, the user is prompted to choose a different alias type.
    If the  user wants to send money between his own accounts, he doesn't have to provide ids, you can use the account name and get the id from context.
    Args:
    Send money from *from_account* to *to_alias* (IBAN, email or phone).

    • Automatically infers alias type when not given.
    • Surfaces Bunq API errors to the user instead of crashing.
    """

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
            monetary_account_id=from_account,
        )

        context.context.pending_payment = None  # clear draft
        return (
            f"✅ Payment {payment.value} executed!\n"
            f"• Amount : {amount} {currency}\n"
            f"• From   : {from_account}\n"
            f"• To     : {to_alias} ({p_type})\n"
            f"• Desc.  : {description or '—'}"
            "\n\nThis is not financial advice."
        )

    except Exception as e:
        err_msg = "; ".join(err.error_description for err in e.error)
        print(err_msg)
        return f"❌ Payment failed: {err_msg}"


@function_tool(
    description_override="Create a public bunq.me payment link (share‑able). "
    "Args: amount (float), currency (str, default ‘EUR’), optional "
    "monetary_account_id, description. Returns the URL and summary."
)
def bunqme_tab(
    context: RunContextWrapper[BunqAgentContext],
    amount: float,
    currency: str = "EUR",
    monetary_account_id: str | None = None,
    description: str | None = None,
) -> str:
    """
    Create a public bunq.me payment request link. Args: amount (float), currency (str, default 'EUR'), optional monetary_account_id, description. Returns the tab URL and summary.
    """
    try:
        amount_inquired = AmountObject(str(amount), currency)
        tab = BunqMeTabEntryApiObject(
            amount_inquired=amount_inquired,
            description=description or "",
        )
        tab_obj = BunqMeTabApiObject.create(
            bunqme_tab_entry=tab,
            monetary_account_id=monetary_account_id,
        )
        url_obj = BunqMeTabApiObject.get(
            bunq_me_tab_id=tab_obj.value, monetary_account_id=monetary_account_id
        ).value
        return (
            f"✅ Tab created! {url_obj.bunqme_tab_share_url}\n"
            f"• Amount : {amount} {currency}\n"
            f"• Desc.  : {description or '—'}"
            "\n\nThis is not financial advice."
        )

    except Exception as e:
        err_msg = "; ".join(err.error_description for err in e)
        return f"❌ Tab creation failed: {err_msg}"


@function_tool(
    description_override="Get an indicative FX spot rate. Args: base_currency (str), "
    "target_currency (str). Returns ‘1 <base> = <rate> <target>’. "
    "Use for quick reference only."
)
def get_exchange_rate(base_currency: str, target_currency: str) -> str:
    """
    Get the current exchange rate between two currencies using a free exchange rate API.
    Args: base_currency (str), target_currency (str)
    Returns: Formatted string with the exchange rate
    """
    try:
        # Use a free exchange rate API
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if target_currency in data["rates"]:
            rate = data["rates"][target_currency]
            return f"1 {base_currency} = {rate:.4f} {target_currency}"
        else:
            return f"❌ Currency {target_currency} not found in exchange rates"

    except Exception as e:
        return f"❌ Failed to fetch exchange rate: {str(e)}"


@function_tool(
    description_override="Show the current user’s profile (ID, name, nationality, preferred "
    "currency).  No arguments."
)
def get_user_info() -> str:
    """
    Get the current user's information(name,user_id,nationality,preffered_currency).
    Returns: Formatted string with user information
    """
    user = _user_context.user_person
    return (
        f"User ID: {user.id_}\n"
        f"Name: {user.display_name}\n"
        f"Nationality : {user.nationality}\n"
        f"Preferred Currency: Euro\n"
    )
