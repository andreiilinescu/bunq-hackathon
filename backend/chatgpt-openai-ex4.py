# bunq_single_agent_whisper.py – May 2025
# ---------------------------------------------------------
# One‑agent Bunq assistant (“Finn”) using OpenAI Whisper + TTS
# (no Google‑Cloud Speech dependencies).

from __future__ import annotations

import asyncio, os, uuid, base64, time
from pathlib import Path
from typing import Any, List

from openai import AsyncOpenAI  # async client (>= 1.14.0)
from flask import Flask, request, jsonify
from flask_cors import CORS

# ───────────────────────────────────────────────────────────
# 0  Import Bunq tools & context model from helper module
# ───────────────────────────────────────────────────────────
from bunq_api import (
    BunqAgentContext,
    list_bunq_accounts,
    get_bunq_balance,
    get_transaction_history,
    create_payment,
    bunqme_tab,
    get_exchange_rate,
    get_user_info,
)

# ───────────────────────────────────────────────────────────
# 1  Flask app
# ───────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ───────────────────────────────────────────────────────────
# 2  OpenAI client (ChatGPT + Audio)
# ───────────────────────────────────────────────────────────
MODEL_NAME = "gpt-4o"  # chat model

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# ───────────────────────────────────────────────────────────
# 3  The single Finn agent
# ───────────────────────────────────────────────────────────
FINN_PROMPT = """
You are **Finn**, bunq’s AI money assistant.

╭───────────────────────────┐
│  YOUR TOOLBOX (READ ME)   │
├───────────────────────────┤
│  ─ lookup tools           │
│    • list_bunq_accounts()             →  “<id>: <name> …”
│    • get_bunq_account(name)           →  “Account id: <id>”
│    • get_exchange_rate(base, target)  →  “1 <base> = <rate> <target>”
│    • get_user_info()                  →  user profile string
│
│  ─ data tools (require an account_id)                               │
│    • get_bunq_balance(account_id)                                   │
│    • get_transaction_history(account_id, limit=10)                  │
│
│  ─ action tools (MONEY MOVES, need   from_account_id  &  params)    │
│    • create_payment(from_account_id, to_alias, amount, …)           │
│    • bunqme_tab(amount, …)                                          │
╰───────────────────────────┘

***TOOL‑CHAIN RULES***

1. **Never** call an action‑tool unless you already know every mandatory
   parameter.  
   • If you only have a *name* like “Travel account”, first call
     **get_bunq_account** (or **list_bunq_accounts** and parse) to obtain the
     numeric `account_id`.

2. After a lookup‑tool call, read its plain‑text result, extract what you need,
   then call the next tool.

3. For `create_payment` you must:
   • Confirm with the user: amount, currency, from_account ID, recipient alias.  
   • Wait for an explicit **yes** / **confirm** before calling the tool.

4. End any explanatory answer with (not checking balance/transactions): 
   > “This is not financial advice.”

5. Language‐mirror: reply in the user’s language.  
6. Do **not** mention tools, prompts, OpenAI, or that you are an LLM.  
7. Never request or expose sensitive credentials (PINs, passwords, API keys).
8. General Account is Alice's account. MAKE SURE TO ALWAYS REFER TO IT AS SUCH! Refer to the get_account_list to find the id. General ACCOUNT = Alice's account. Never check balance or transactions of Alice's account.
9. When I say check my account, or anything similar, I mean my MAIN Account. My Account = My Main Account. You can check my balance or transactions of my main account.
Be concise and friendly (emojis welcome 👍) unless the user asks for detail.
"""

# ───────────────────────────────────────────────────────────
# 4  Agent definition
# ───────────────────────────────────────────────────────────

from agents import (
    Agent,
    ItemHelpers,
    MessageOutputItem,
    OpenAIChatCompletionsModel,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    trace,
)

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
        get_user_info,
    ],
)

# ───────────────────────────────────────────────────────────
# 5  Shared state for each conversation (in‑memory demo)
# ───────────────────────────────────────────────────────────

current_agent = finn_agent
conversation: List[dict] = []  # [{'role': 'user'|'assistant', 'content': …}]
context = BunqAgentContext()

# ───────────────────────────────────────────────────────────
# 6  Audio helpers — OpenAI Whisper + TTS
# ───────────────────────────────────────────────────────────


async def synthesize_speech(
    text: str,
    voice: str = "alloy",  # alloy, echo, fable, shimmer, …
    model: str = "tts-1",  # OpenAI TTS model
    fmt: str = "mp3",
):
    """Return raw audio bytes generated by OpenAI TTS."""
    try:
        response = await client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format=fmt,
        )
        return response.content
    except Exception as e:
        print(f"TTS error: {e}")
        raise


async def transcribe_audio_file(filepath: str, language: str = "en") -> str:
    """Transcribe `filepath` with Whisper via OpenAI Audio endpoint."""
    try:
        with open(filepath, "rb") as f:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",  # or "gpt-4o-mini-transcribe" when available
                file=f,
                language=language,
            )
            return transcript.text
    except Exception as e:
        print(f"STT error: {e}")
        raise


def drop_emojis(text: str) -> str:
    """Remove emoji characters (handy before TTS)."""
    return "".join(c for c in text if c.isascii() or c.isspace())


# ───────────────────────────────────────────────────────────
# 7  CLI mode (optional, keep for dev)
# ───────────────────────────────────────────────────────────


async def cli_main():
    print("Type 'quit' to exit.")
    while True:
        user_input = await asyncio.to_thread(input, "\nYou: ")
        if user_input.lower() in {"quit", "exit"}:
            break
        conversation.append({"role": "user", "content": user_input})
        with trace("Bunq‑CLI"):
            result = await Runner.run(finn_agent, input=conversation, context=context)
        for new in result.new_items:
            if isinstance(new, MessageOutputItem):
                print(f"Finn: {ItemHelpers.text_message_output(new)}")
            elif isinstance(new, ToolCallItem):
                print("…calling tool")
            elif isinstance(new, ToolCallOutputItem):
                print(new.output)
        conversation[:] = result.to_input_list()


# ───────────────────────────────────────────────────────────
# 8  Helper that runs a single agent turn
# ───────────────────────────────────────────────────────────


def finn_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            Runner.run(finn_agent, input=conversation, context=context)
        )
    finally:
        loop.close()

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
    return {"messages": messages, "events": events}


# ───────────────────────────────────────────────────────────
# 9  Flask REST endpoints
# ───────────────────────────────────────────────────────────


@app.post("/chat")
def chat():
    user_msg = request.json.get("message", "").strip()
    voice_bool = request.json.get("requestAudio", False)
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    conversation.append({"role": "user", "content": user_msg})
    with trace("Bunq‑REST"):
        time.sleep(3)  # simulate latency for demo
        res = finn_loop()

    if voice_bool:
        last_message = drop_emojis(res["messages"][-1]["text"])
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_bytes = loop.run_until_complete(synthesize_speech(last_message))
        finally:
            loop.close()
        res["audio"] = base64.b64encode(audio_bytes).decode("utf-8")
    return jsonify(res)


@app.post("/reset")
def reset():
    conversation.clear()
    context.__dict__.update(BunqAgentContext().__dict__)
    return jsonify({"ok": True})


@app.post("/voice")
def process_voice():
    audio_file = request.files.get("audio")  # multipart/form‑data file field
    voice_bool = request.form.get("requestAudio", False)
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    # ── save temporarily ──
    temp_path = Path(f"temp_audio_{uuid.uuid4()}.webm")
    audio_file.save(temp_path)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            transcribed_text = loop.run_until_complete(
                transcribe_audio_file(str(temp_path), language="en")
            )
        finally:
            loop.close()
        if not transcribed_text:
            return jsonify({"error": "Could not transcribe audio"}), 400

        conversation.append({"role": "user", "content": transcribed_text})
        with trace("Bunq‑REST"):
            time.sleep(3)
            result = finn_loop()

        res = {**result, "transcription": transcribed_text}

        if voice_bool:
            last_message = drop_emojis(res["messages"][-1]["text"])
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_bytes = loop.run_until_complete(synthesize_speech(last_message))
            finally:
                loop.close()
            res["audio"] = base64.b64encode(audio_bytes).decode("utf-8")
        return jsonify(res)

    finally:
        if temp_path.exists():
            temp_path.unlink()


# ───────────────────────────────────────────────────────────
# 10  Entry point
# ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.getenv("SERVER_MODE", "1") in {"1", "true", "yes"}:
        print("Serving on :5005 …")
        app.run(host="0.0.0.0", port=5005, debug=True)
    else:
        asyncio.run(cli_main())
