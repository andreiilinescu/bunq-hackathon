from __future__ import annotations

import asyncio
import os
import uuid


from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    OpenAIChatCompletionsModel,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    trace,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

from bunq_api import (
    BunqAgentContext,
    list_bunq_accounts,
    get_bunq_balance,
    get_transaction_history,
    create_payment,
    get_exchange_rate,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(disabled=True)


COMMON_RULES = """
Core rules ⬇️ (inherits into every specialist)
• Be concise by default; ask follow‑ups if anything you need is missing.
• Do NOT fabricate data. If unknown, apologise and offer next steps.
• End all educational answers with: “This is not financial advice.”
"""

account_agent = Agent[BunqAgentContext](
    name="Account‑Info Agent",
    handoff_description="Lists accounts and balances.",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    instructions=f"""{COMMON_RULES}
You help users see what accounts exist and what each holds.
Routine:
1. If user hasn’t picked an account, list them with list_bunq_accounts.
2. When they ask for balance, call get_bunq_balance.
3. Any other request → hand off back to Triage.""",
    tools=[list_bunq_accounts, get_bunq_balance],
)

transactions_agent = Agent[BunqAgentContext](
    name="Transaction Agent",
    handoff_description="Shows recent payments on an account.",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    instructions=f"""{COMMON_RULES}
Routine:
1. Ask which account they want the history for.
2. Ask how many items (default 10).
3. Call get_transaction_history.
4. Unknown question → hand off back to Triage.""",
    tools=[get_transaction_history],
)

payment_agent = Agent[BunqAgentContext](
    name="Payment Agent",
    handoff_description="Sets up and executes payments, with confirmation.",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    instructions=f"""{COMMON_RULES}
Routine:
1. Collect ➜ from‑account, destination IBAN, amount.
2. Summarise: “You’re sending X EUR from A to B. Confirm?”
3. Wait for explicit yes/no.
   • If yes → call create_payment.
   • If no → cancel and transfer back to Triage.""",
    tools=[create_payment],
)

fx_agent = Agent[BunqAgentContext](
    name="FX Agent",
    handoff_description="Gets live exchange rates.",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    instructions=f"""{COMMON_RULES}
Routine:
1. Identify requested currency pair.
2. Call get_exchange_rate.
3. If user asks anything else → back to Triage.""",
    tools=[get_exchange_rate],
)

faq_agent = Agent[BunqAgentContext](
    name="FAQ Agent",
    handoff_description="Answers general bunq FAQs (not account‑specific).",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    instructions=f"""{COMMON_RULES}
Use your own model knowledge to answer common bunq questions (card limits,
fees, etc.). If the question is about a specific account or payment,
handoff to Triage.""",
)

# ------------------------------------------------------------------------------
# 5.  Triage / Router agent
# ------------------------------------------------------------------------------

triage_agent = Agent[BunqAgentContext](
    name="Triage Agent",
    handoff_description="Decides which specialist should handle the request.",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    instructions=f"""{COMMON_RULES}
Decide who should help:
• Balance / list accounts → Account‑Info
• “Transactions”, “history”, “spent” → Transaction
• “Send”, “transfer”, “pay” → Payment
• “Rate”, “EUR to USD”, “FX” → FX
• Anything like “fee”, “card”, “IBAN format” → FAQ
When a specialised topic is finished, they may hand back to you.""",
    handoffs=[
        account_agent,
        transactions_agent,
        payment_agent,
        fx_agent,
        faq_agent,
    ],
)

for a in (account_agent, transactions_agent, payment_agent, fx_agent, faq_agent):
    a.handoffs.append(triage_agent)


async def main():
    current_agent: Agent[BunqAgentContext] = triage_agent
    input_items: list = []
    context = BunqAgentContext()
    convo_id = uuid.uuid4().hex[:8]

    print("Type 'quit' to exit.")
    while True:
        user_input = await asyncio.to_thread(input, "\nYou: ")
        if user_input.strip().lower() in {"quit", "exit"}:
            break

        with trace("Bunq Chat", group_id=convo_id):
            input_items.append({"role": "user", "content": user_input})
            result = await Runner.run(
                current_agent,
                input_items,
                context=context,
            )

            # --- display & move state forward ----
            for item in result.new_items:
                src = item.agent.name
                if isinstance(item, MessageOutputItem):
                    print(f"{src}: {ItemHelpers.text_message_output(item)}")
                elif isinstance(item, HandoffOutputItem):
                    print(f"🔄 Handoff ➜ {item.target_agent.name}")
                elif isinstance(item, ToolCallItem):
                    print(f"{src}: …calling tool")
                elif isinstance(item, ToolCallOutputItem):
                    print(f"{src}: {item.output}")

            input_items = result.to_input_list()
            current_agent = result.last_agent


if __name__ == "__main__":
    asyncio.run(main())
