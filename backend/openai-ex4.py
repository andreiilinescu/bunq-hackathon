# bunq_single_agent.py – May 2025
# --------------------------------
# One‑agent Bunq assistant (“Finn”) with all money tools attached.

from __future__ import annotations

import asyncio, os, uuid
from typing import Any, List

from agents import (
    Agent,
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
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---------------------------------------------------------------------------
# 0  Import Bunq tools & context model from your helper module
# ---------------------------------------------------------------------------
from bunq_api import (
    BunqAgentContext,
    list_bunq_accounts,
    get_bunq_balance,
    get_transaction_history,
    create_payment,
    bunqme_tab,
    get_exchange_rate,
)

# ---------------------------------------------------------------------------
# 1  Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# 2  OpenAI / Gemini client
# ---------------------------------------------------------------------------
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
API_KEY = os.getenv("GEMINI_API_KEY")
print(f"API key: {API_KEY}")
MODEL_NAME = "gemini-2.0-flash"

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(disabled=True)

# ---------------------------------------------------------------------------
# 3  The **single** Finn agent
# ---------------------------------------------------------------------------
FINN_PROMPT = """
You are **Finn**, bunq’s AI money assistant embedded in the app.
Your mission is to give users quick, privacy‑first answers about their money
and to execute actions through the tools you have.

Core rules:
• Be concise unless the user asks for detail.
• Ask follow‑up questions when information is missing.
• Never fabricate balances or transactions. If unavailable, say so.
• Always append: “This is not financial advice.” to educational content.
• Before moving money, summarise the details and ask for an explicit yes/no.
• Refuse anything outside scope (loans, tax, investments, etc.) politely.

Capabilities you have:
• list_bunq_accounts – list account IDs & names
• get_bunq_balance – balance for an account
• get_transaction_history – recent payments
• create_payment – send money (IBAN / e‑mail / phone)
• bunqme_tab – create public payment link
• get_exchange_rate – FX spot rate (indicative)

Use tools whenever factual data or an action is required.  Otherwise,
answer from your general bunq knowledge.
"""

finn_agent = Agent[BunqAgentContext](
    name="Finn",
    instructions=FINN_PROMPT.strip(),
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    tools=[
        list_bunq_accounts,
        get_bunq_balance,
        get_transaction_history,
        create_payment,
        bunqme_tab,
        get_exchange_rate,
    ],
)

# ---------------------------------------------------------------------------
# 4  Shared state for each conversation (in‑memory demo)
# ---------------------------------------------------------------------------
current_agent = finn_agent
conversation: List[dict] = []  # [{'role': 'user'|'assistant', 'content': …}]
context = BunqAgentContext()


# ---------------------------------------------------------------------------
# 5  CLI mode (optional, keep for dev)
# ---------------------------------------------------------------------------
async def cli_main():
    print("Type 'quit' to exit.")
    while True:
        user_input = await asyncio.to_thread(input, "\nYou: ")
        if user_input.lower() in {"quit", "exit"}:
            break

        conversation.append({"role": "user", "content": user_input})
        with trace("Bunq‑CLI"):
            result = await Runner.run(finn_agent, input=conversation, context=context)

        # show assistant reply and any tool call outputs
        for new in result.new_items:
            if isinstance(new, MessageOutputItem):
                print(f"Finn: {ItemHelpers.text_message_output(new)}")
            elif isinstance(new, ToolCallItem):
                print("…calling tool")
            elif isinstance(new, ToolCallOutputItem):
                print(new.output)

        conversation[:] = result.to_input_list()  # clean history


# ---------------------------------------------------------------------------
# 6  Flask REST endpoints
# ---------------------------------------------------------------------------
@app.post("/chat")
def chat():
    user_msg = request.json.get("message", "").strip()
    print(f"User: {user_msg}")
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    conversation.append({"role": "user", "content": user_msg})

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            Runner.run(
                finn_agent,
                input=conversation,
                context=context,
            )
        )
    finally:
        loop.close()

    # Build response payload
    messages, events = [], []
    for i in result.new_items:
        if isinstance(i, MessageOutputItem):
            messages.append({"text": ItemHelpers.text_message_output(i)})
        elif isinstance(i, ToolCallItem):
            events.append({"type": "tool_call", "tool": i.type})
        elif isinstance(i, ToolCallOutputItem):
            events.append({"type": "tool_result", "output": i.output})

    conversation[:] = result.to_input_list()
    print(f"Finn: {messages[-1]['text']}")
    return jsonify({"messages": messages, "events": events})


@app.post("/reset")
def reset():
    conversation.clear()
    context.__dict__.update(BunqAgentContext().__dict__)  # re‑init
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# 7  Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if os.getenv("SERVER_MODE", "1") in {"1", "true", "yes"}:
        print("Serving on :5005 …")
        app.run(host="0.0.0.0", port=5005, debug=True)
    else:
        asyncio.run(cli_main())
