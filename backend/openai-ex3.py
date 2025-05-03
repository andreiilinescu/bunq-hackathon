from __future__ import annotations as _annotations

"""
bunq_agents.py – Draft v0.1 (2025‑05‑03)
A multi‑agent architecture for a bunq banking assistant built with the
`agents` framework and the official Bunq SDK helper (BunqLib).

Agents
------
• AccountInfoAgent  – answers questions about accounts, balances & recent
  transactions.
• PaymentAgent      – initiates payments, but *always* double‑confirms with
  the user before any money moves.
• FXAgent           – provides real‑time currency‑exchange info.
• TriageAgent       – first‑line router that decides which specialist should
  handle a user request, or hands back control if the specialist is stuck.

This is a **starting point**.  Feel free to tweak, extend and iterate.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, Field, validator

from bunq.sdk.context.api_context import ApiEnvironmentType

from bunq_lib import BunqLib  # tiny façade shipped separately (see user input)

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Runtime configuration ------------------------------------------------------
# ---------------------------------------------------------------------------

BASE_URL = os.getenv(
    "GENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GENAI_MODEL", "gemini-2.0-flash")

if not API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

openai_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
chat_model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=openai_client)

# ---------------------------------------------------------------------------
# Shared context -------------------------------------------------------------
# ---------------------------------------------------------------------------


class BunqAgentContext(BaseModel):
    """Conversation‑level state shared between all specialist agents."""

    selected_account_id: str | None = Field(
        None, description="Active account the user is working with."
    )
    pending_payment_to: str | None = None
    pending_payment_amount: float | None = None
    pending_payment_currency: str | None = "EUR"

    # For audits / compliance (optional)
    user_confirmed_last_action: bool = False

    @validator("pending_payment_amount")
    def _validate_amount(cls, v):  # noqa: N805
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive.")
        return v


# Instantiate Bunq SDK helper once; reuse across calls -----------------------
BUNQ_ENV = (
    ApiEnvironmentType.SANDBOX
    if os.getenv("BUNQ_ENV", "sandbox").lower() == "sandbox"
    else ApiEnvironmentType.PRODUCTION
)
bunq = BunqLib(BUNQ_ENV)

# ---------------------------------------------------------------------------
# Tool functions (thin async wrappers around BunqLib) ------------------------
# ---------------------------------------------------------------------------


@function_tool(
    name_override="list_accounts",
    description_override="List all bunq monetary accounts visible to the user.",
)
async def list_accounts() -> str:
    accounts = bunq.get_all_monetary_account_active()
    lines = [
        f"{acc.id_} – {acc.description} (\u20ac{acc.balance.value})" for acc in accounts
    ]
    return "\n".join(lines) or "No accounts found."


@function_tool(
    name_override="get_balance",
    description_override="Get the balance of a specific account ID.",
)
async def get_balance(account_id: str) -> str:
    accounts = bunq.get_all_monetary_account_active()
    for acc in accounts:
        if str(acc.id_) == str(account_id):
            return f"Balance for {account_id}: \u20ac{acc.balance.value}"
    return "Account not found."


@function_tool(
    name_override="get_transactions",
    description_override="List N most recent transactions for an account.",
)
async def get_transactions(account_id: str, limit: int = 10) -> str:
    txs = bunq.get_all_payment(count=limit)
    filtered = [tx for tx in txs if str(tx.monetary_account_id) == str(account_id)]
    lines: List[str] = []
    for tx in filtered[:limit]:
        dir_ = "+" if tx.amount.value.startswith("-") is False else "-"
        lines.append(f"{tx.id_}: {dir_}\u20ac{tx.amount.value} – {tx.description}")
    return "\n".join(lines) or "No transactions found."


@function_tool(
    name_override="initiate_payment",
    description_override="Create a payment between two bunq accounts.",
)
async def initiate_payment(
    context: RunContextWrapper[BunqAgentContext],
    *,
    from_account: str,
    to_iban_or_alias: str,
    amount: float,
    currency: str = "EUR",
) -> str:
    # Persist intent; PaymentAgent will ask for confirmation before executing.
    context.context.selected_account_id = from_account
    context.context.pending_payment_to = to_iban_or_alias
    context.context.pending_payment_amount = amount
    context.context.pending_payment_currency = currency
    context.context.user_confirmed_last_action = False

    return (
        "Payment prepared. Please confirm: "
        f"Send {amount:.2f} {currency} from {from_account} to {to_iban_or_alias}? "
        "Reply 'yes' to proceed or 'no' to cancel."
    )


@function_tool(
    name_override="execute_payment",
    description_override="(Internal) Actually perform the payment once the user has confirmed.",
)
async def execute_payment(context: RunContextWrapper[BunqAgentContext]) -> str:
    if not (
        context.context.selected_account_id
        and context.context.pending_payment_to
        and context.context.pending_payment_amount
    ):
        return "No pending payment to execute."

    bunq.make_payment(
        amount_string=str(context.context.pending_payment_amount),
        description="Payment via Finn assistant",
        recipient=context.context.pending_payment_to,
    )

    # Clear pending state
    out = (
        f"Payment of {context.context.pending_payment_amount:.2f} {context.context.pending_payment_currency} "
        f"to {context.context.pending_payment_to} completed successfully."
    )
    context.context.pending_payment_to = None
    context.context.pending_payment_amount = None
    context.context.user_confirmed_last_action = True
    return out


@function_tool(
    name_override="get_fx_rate",
    description_override="Get the latest FX rate between two currencies.",
)
async def get_fx_rate(base_currency: str, target_currency: str) -> str:
    # Placeholder – integrate a real FX feed.
    fake_rate = 0.91  # TODO replace
    return f"1 {base_currency} = {fake_rate} {target_currency} (mock rate)"


# ---------------------------------------------------------------------------
# Specialist agents ----------------------------------------------------------
# ---------------------------------------------------------------------------

account_info_agent = Agent[BunqAgentContext](
    name="Account Info Agent",
    handoff_description="Provides balances and recent transactions.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are the account‑information specialist. Follow this routine:
1. Determine whether the user wants *all* account info or a *specific* account.
2. Use `list_accounts` for general listings or `get_balance` / `get_transactions` for specifics.
3. If the user asks anything about payments or FX, hand off to the appropriate agent.""",
    tools=[list_accounts, get_balance, get_transactions],
    model=chat_model,
)


payment_agent = Agent[BunqAgentContext](
    name="Payment Agent",
    handoff_description="Initiates money transfers between bunq accounts.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are the payment specialist. Routine:
1. Gather `from_account`, `to_iban_or_alias`, and `amount`.
2. Call `initiate_payment` to draft the transaction (this does NOT move money).
3. Wait for an explicit 'yes' / 'confirm' from the user. If confirmed, call `execute_payment`.
4. Otherwise, cancel and clear pending state.
If the user needs only balance or FX info, hand off accordingly.""",
    tools=[initiate_payment, execute_payment],
    model=chat_model,
)


fx_agent = Agent[BunqAgentContext](
    name="FX Agent",
    handoff_description="Provides exchange‑rate information.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are the FX specialist. Use `get_fx_rate` to answer currency‑conversion questions.
If the question involves account balances or payments, hand off appropriately.""",
    tools=[get_fx_rate],
    model=chat_model,
)


# ---------------------------------------------------------------------------
# Triage agent (the entry point) ---------------------------------------------
# ---------------------------------------------------------------------------

triage_agent = Agent[BunqAgentContext](
    name="Triage Agent",
    handoff_description="Routes the user's request to the correct specialist.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are Finn's triage brain. Decide quickly which specialist can best handle the user's latest message.
Options:
• Account Info   – balances, account overview, transactions.
• Payment        – moving money.
• FX             – exchange rates.
If none fit, apologise and explain the limitation (see core rules).""",
    handoffs=[
        handoff(agent=account_info_agent),
        handoff(agent=payment_agent),
        handoff(agent=fx_agent),
    ],
    model=chat_model,
)

# Allow specialists to hand back to triage for out‑of‑scope queries ---------
for specialist in (account_info_agent, payment_agent, fx_agent):
    specialist.handoffs.append(triage_agent)


# ---------------------------------------------------------------------------
# Simple CLI loop for local testing -----------------------------------------
# ---------------------------------------------------------------------------


async def main() -> None:
    context = BunqAgentContext()
    conversation_id = "local‑cli"
    current_agent: Agent[BunqAgentContext] = triage_agent
    input_items: List[TResponseInputItem] = []

    print("Finn • bunq assistant – type 'quit' to exit.")
    while True:
        user_input = await asyncio.to_thread(input, "You: ")
        if user_input.lower().strip() in {"quit", "exit"}:
            print("Bye!")
            break

        # Build request list
        input_items.append({"role": "user", "content": user_input})
        result = await Runner.run(current_agent, input_items, context=context)

        # Display & update
        for new_item in result.new_items:
            agent_name = new_item.agent.name
            if isinstance(new_item, MessageOutputItem):
                print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
            elif isinstance(new_item, HandoffOutputItem):
                print(
                    f"→ Hand‑off: {new_item.source_agent.name} → {new_item.target_agent.name}"
                )
            elif isinstance(new_item, ToolCallItem):
                print(f"{agent_name}: calling tool…")
            elif isinstance(new_item, ToolCallOutputItem):
                print(f"{agent_name}: {new_item.output}")

        input_items = result.to_input_list()
        current_agent = result.last_agent


if __name__ == "__main__":
    asyncio.run(main())
