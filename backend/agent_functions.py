from pydantic import BaseModel
from agents import function_tool, RunContextWrapper
from typing import Any, Dict, List, Optional

from bank_api import (
    get_user_by_id,
    get_account_by_id,
    bankme_link,
    make_payment,
    get_exchange_rate,
    transfer_between_accounts,
    current_user_id,
    Account,
    User,
)

user: User = get_user_by_id(current_user_id)


class BankAgentContext(BaseModel):
    current_user_id: str | None = current_user_id
    current_user_name: str | None = user.name
    current_user_email: str | None = user.email
    current_user_phone: str | None = user.phone
    current_user_account_ids: List[str] | None = user.accounts_ids


@function_tool(
    description_override="Return a newline list of the user’s monetary accounts in the form "
    "‘<id>: <description>  • IBAN: NL…’.  No arguments."
)
def list_accounts() -> List[Dict[str, Any]]:
    accounts = []
    for account_id in user.accounts_ids:
        account = get_account_by_id(account_id)
        accounts.append(
            {
                "id": account.id,
                "description": account.description,
                "currency": account.currency,
                "balance": account.balance,
            }
        )
    return accounts


@function_tool(
    description_override="Resolve an account’s *description name* (e.g. “Travel”) to its numeric "
    "ID.  Args: account_name (str).  Returns “Account id: <id>” or "
    "“Account not found”.  Use this before other tools when you only have a "
    "name."
)
def get_account(account_name: str) -> str:
    accounts: list[Account] = user.accounts_ids
    for acc in accounts:
        if acc.description == account_name:
            return f"Account id: {acc.id}"
    return "Account not found."


@function_tool(
    description_override="Real‑time balance lookup.  Args: account_id (str).  Returns "
    "‘Balance for <id>: €<value>’."
)
def check_balance(account_id: str) -> float:
    account = get_account_by_id(account_id)
    return account.balance


@function_tool(
    description_override="Check exchange rate between currencies. Args: base_currency (str), "
    "target_currency (str), amount(str). Returns ‘<amount> <base> = <rate*amount> <target>’. "
    "Use for quick reference only."
)
def exchange_rate(
    base_currency: str,
    target_currency: str,
    amount: float = 1,
) -> str:
    rate = get_exchange_rate(base_currency, target_currency)
    if rate == -1:
        return f"❌ Currency {target_currency} not found in exchange rates"
    elif rate == -2:
        return f"❌ Failed to fetch exchange rate: {str(e)}"
    return f"{amount} {base_currency} = {rate*amount} {target_currency}"


@function_tool(
    description_override="Show the current user’s profile (ID, name, nationality, preferred "
    "currency).  No arguments."
)
def get_user_info() -> str:
    """Get user info"""
    return f"User: {user.name} ({user.email})\nPhone: {user.phone} "


@function_tool(
    description_override="Send money. **Call only after the user explicitly confirmed.** "
    "Args: from_account (str ID), to_alias (IBAN/email/phone), amount (float), "
    "currency (str, default ‘EUR’), optional description. "
    "Returns a success receipt or error string."
)
def create_payment(
    from_account_id: str,
    to_alias: str,
    amount: float,
    currency: str,
    description: Optional[str] = None,
) -> str:
    payment_request = make_payment(
        amount, currency, to_alias, from_account_id, description
    )
    return payment_request


@function_tool(
    description_override="Create a public bankme payment link (share‑able). "
    "Args: amount (float), currency (str, default ‘EUR’), optional "
    "monetary_account_id, description. Returns the URL and summary."
)
def create_bankme_link(
    amount: float,
    currency: str,
    account_id: str,
    description: Optional[str] = None,
) -> str:
    link = bankme_link(amount, currency, account_id, description)
    return f"Link created: {link}"


@function_tool(
    description_override="Transfer between two accounts. Can be used to transfer between user's own accoutns. Args: from_account_id (str), "
    "to_account_id (str), amount (float), currency (str). Returns ‘Transfer completed’ or "
    "‘Transfer failed’."
)
def transfer_between_accounts_by_ids(
    from_account_id: str,
    to_account_id: str,
    amount: float,
    currency: str,
) -> str:

    transfer = transfer_between_accounts(
        from_account_id, to_account_id, amount, currency
    )
    return f"Transfer completed: {transfer}"


@function_tool()
def get_transaction_history(
    account_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    account = get_account_by_id(account_id)
    if not account:
        return "No account found."
    transactions = account.transactions[-limit]
    return transactions or "No transactions found."


@function_tool()
def get_friends_aliases() -> List[Dict[str, Any]]:
    friends = user.friends_alias
    return friends or "No friends found."
