from __future__ import annotations as _annotations

"""
Bunq Multi‑Agent Example
-----------------------
This script shows how to structure Finn (bunq’s AI assistant) with
specialised sub‑agents that each focus on a discrete banking task.
A triage agent decides which specialist to hand the conversation to.
Each tool is a thin wrapper around the BunqClient so that *all* account
logic lives in one place.

⚠️  The BunqClient class from your previous snippet must be available in
    your PYTHONPATH as `bunq_client.py` or an installed package. Implement
    the missing helper methods there (get_balance, get_transaction_history,
    get_exchange_rate) so the tools below can call them.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

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
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# --- bunq SDK wrapper -------------------------------------------------------------------------
from bunq_client import BunqClient

bunq_client = BunqClient()  # reads BUNQ_API_KEY from env

# --- Shared conversation context --------------------------------------------------------------


class BunqAgentContext(BaseModel):
    """State that all agents can read/write during the session."""

    selected_account_id: Optional[int] = None
    pending_payment_amount: Optional[float] = None
    pending_payment_currency: str = "EUR"
    pending_payment_recipient: Optional[str] = None  # IBAN
    pending_payment_description: Optional[str] = None


# --- Tool definitions -------------------------------------------------------------------------


@function_tool(
    name_override="list_accounts",
    description_override="List all bunq monetary accounts.",
)
def list_accounts() -> str:
    # 🔧 Replace this with real logic using bunq_client once ready
    return "\n".join(["12345 (Checking)", "67890 (Savings)"])


@function_tool
def get_balance(account_id: int) -> str:
    return bunq_client.get_balance(account_id)  # ➜ implement this in BunqClient


@function_tool
def transaction_history(account_id: int, limit: int = 10) -> str:
    return bunq_client.get_transaction_history(account_id, limit)


@function_tool
def send_payment(
    context: RunContextWrapper[BunqAgentContext],
    from_account_id: int,
    to_iban: str,
    amount: float,
    description: str,
    currency: str = "EUR",
) -> str:
    """Execute an *immediate* payment **after the user has confirmed** the details."""
    # Store a copy in the shared context for audit / follow‑up questions
    context.context.pending_payment_amount = amount
    context.context.pending_payment_currency = currency
    context.context.pending_payment_recipient = to_iban
    context.context.pending_payment_description = description

    payment = bunq_client.send_payment(
        from_account_id, to_iban, amount, description, currency
    )
    return f"Payment {payment['id']} — status: {payment['status']}"


@function_tool
def schedule_payment(
    from_account_id: int,
    to_iban: str,
    amount: float,
    description: str,
    schedule_date: datetime,
    currency: str = "EUR",
) -> str:
    scheduled = bunq_client.schedule_payment(
        from_account_id, to_iban, amount, description, schedule_date, currency
    )
    return f"Payment {scheduled['id']} scheduled for {scheduled['scheduled_for']}"


@function_tool
def cancel_schedule(account_id: int, schedule_id: int) -> str:
    cancelled = bunq_client.cancel_scheduled_payment(account_id, schedule_id)
    return (
        f"Cancelled schedule {cancelled['schedule_id']} (status: {cancelled['status']})"
    )


@function_tool
def fx_rate(base_currency: str = "EUR", target_currency: str = "USD") -> str:
    return bunq_client.get_exchange_rate(base_currency, target_currency)


# --- Specialist agents ------------------------------------------------------------------------

accounts_agent = Agent[BunqAgentContext](
    name="Accounts Agent",
    handoff_description="Handles account listings and balances.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You specialise in account overviews.
# Routine
1. If the user wants to *see* their accounts, call `list_accounts`.
2. If they want a *balance*, clarify which account ID then call `get_balance`.
3. Otherwise, hand back to the triage agent.""",
    tools=[list_accounts, get_balance],
)

transactions_agent = Agent[BunqAgentContext](
    name="Transactions Agent",
    handoff_description="Shows recent transactions.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You provide transaction history.
# Routine
1. Ask which account.
2. Ask how many items (default 10).
3. Call `transaction_history`.""",
    tools=[transaction_history],
)

payment_agent = Agent[BunqAgentContext](
    name="Payment Agent",
    handoff_description="Sends or schedules payments, with explicit user confirmation.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You can *only* move money after double‑checking the user’s intent.
# Routine for immediate payment
1. Collect: from_account_id, recipient IBAN, amount, currency, description.
2. Summarise these details and ask "Is this correct? (yes/no)".
3. Only on an explicit **yes**, call `send_payment`.

# Routine for scheduled payments
Same, but also ask for the date, then call `schedule_payment`.

If the user wants to cancel, call `cancel_schedule`.""",
    tools=[send_payment, schedule_payment, cancel_schedule],
)

fx_agent = Agent[BunqAgentContext](
    name="FX Agent",
    handoff_description="Provides currency exchange rates.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
Answer exchange‑rate questions with the `fx_rate` tool.""",
    tools=[fx_rate],
)

# --- Triage agent -----------------------------------------------------------------------------

triage_agent = Agent[BunqAgentContext](
    name="Triage Agent",
    handoff_description="Routes bunq questions to the correct specialist agent.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are Finn’s traffic‑controller. Decide which specialist agent should handle the request.
If a question spans multiple areas, choose the *closest* match or ask a follow‑up question.""",
    handoffs=[
        accounts_agent,
        transactions_agent,
        payment_agent,
        fx_agent,
    ],
)

# Make hand‑offs bidirectional so each specialist can send control back
for specialist in [accounts_agent, transactions_agent, payment_agent, fx_agent]:
    specialist.handoffs.append(triage_agent)


# --- Demo CLI loop ---------------------------------------------------------------------------


async def main() -> None:
    current_agent: Agent[BunqAgentContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = BunqAgentContext()
    conversation_id = uuid.uuid4().hex[:16]

    print("Type 'quit' or 'exit' to leave.")

    while True:
        try:
            user_text = await asyncio.to_thread(input, "\nYou: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_text.lower() in {"quit", "exit"}:
            break

        with trace("bunq session", group_id=conversation_id):
            input_items.append({"role": "user", "content": user_text})
            result = await Runner.run(current_agent, input_items, context=context)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off: {new_item.source_agent.name} ➜ {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: calling tool …")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: ➜ {new_item.output}")

            input_items = result.to_input_list()
            current_agent = result.last_agent

    print("Goodbye! 👋")


if __name__ == "__main__":
    asyncio.run(main())
