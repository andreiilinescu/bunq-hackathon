# bunq_single_agent.py – May 2025
# --------------------------------
# One‑agent Bunq assistant (“Finn”) with all money tools attached.

from __future__ import annotations

import asyncio, os, uuid
from typing import Any, List
import time
import base64
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
from openai import AsyncOpenAI  # ← unchanged import
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud.texttospeech_v1 import TextToSpeechClient
from google.cloud.texttospeech_v1.types import (
    SynthesisInput,
    VoiceSelectionParams,
    SsmlVoiceGender,
    AudioConfig,
    AudioEncoding,
)

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
    get_user_info,
)

# ---------------------------------------------------------------------------
# 1  Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# 2  OpenAI client (ChatGPT)          ← **CHANGED SECTION**
# ---------------------------------------------------------------------------
# SDK hits api.openai.com by default, so we don’t need base_url.
# Set OPENAI_API_KEY in your env.
MODEL_NAME = "gpt-4o"  # or "gpt-4o", "gpt-4-turbo", etc.

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    # timeout=30.0,          # optional tweaks
    # max_retries=3,
)

# ---------------------------------------------------------------------------
# 3  The **single** Finn agent
# ---------------------------------------------------------------------------
FINN_PROMPT = """
You are **Finn**, bunq’s AI money assistant.

╭───────────────────────────┐
│  YOUR TOOLBOX (READ ME)   │
├───────────────────────────┤
│  ─ lookup tools           │
│    • list_bunq_accounts()             →  “<id>: <name> …”            │
│    • get_bunq_account(name)           →  “Account id: <id>”          │
│    • get_exchange_rate(base, target)  →  “1 <base> = <rate> <target>”│
│    • get_user_info()                  →  user profile string         │
│                                                                    │
│  ─ data tools (require an account_id)                               │
│    • get_bunq_balance(account_id)                                   │
│    • get_transaction_history(account_id, limit=10)                  │
│                                                                    │
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
8. When I say Alice, refer to "main" account. . Handle finding the ids using the list_bunq_accounts tool. Don't mention that it is my account. Refer to it as alice's account.
Be concise and friendly (emojis welcome 👍) unless the user asks for detail.
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
        get_user_info,
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


# … everything else below this point is **unchanged** …


def finn_loop():
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
    return {"messages": messages, "events": events}


def drop_emojis(text: str) -> str:
    """
    Remove emojis from the text.

    Args:
        text (str): The input text.

    Returns:
        str: The text without emojis.
    """
    return "".join(c for c in text if c.isascii() or c.isspace())


def synthesize_speech(
    text: str,
    output_file: str = None,
    language_code: str = "en-US",
    voice_name: str = "en-US-Studio-O",
):
    """
    Synthesize speech from text using Google Cloud Text-to-Speech API.

    Args:
        text (str): The text to synthesize.
        output_file (str, optional): Output file path. If None, audio data is returned.
        language_code (str, optional): Language code. Defaults to "en-US".
        voice_name (str, optional): Voice name. Defaults to "en-US-Studio-O" (natural female voice).

    Returns:
        bytes or str: Audio content as bytes if output_file is None, otherwise the file path.
    """
    try:
        # Create the Text-to-Speech client
        client = TextToSpeechClient()

        # Set the text input to be synthesized
        synthesis_input = SynthesisInput(text=text)

        # Build the voice request
        voice = VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=SsmlVoiceGender.MALE,
        )

        # Select the audio format - MP3 for browser compatibility
        audio_config = AudioConfig(
            audio_encoding=AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=5.0,  # Default pitch
        )

        # Perform the synthesis request
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # If output file is specified, save the audio
        if output_file:
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            print(f"Audio content written to '{output_file}'")
            return output_file

        # Otherwise, return the audio content
        return response.audio_content

    except Exception as e:
        print(f"Error synthesizing speech: {str(e)}")
        raise e


# ---------------------------------------------------------------------------
# 6  Flask REST endpoints
# ---------------------------------------------------------------------------
@app.post("/chat")
def chat():
    user_msg = request.json.get("message", "").strip()
    voice_bool = request.json.get("requestAudio", False)
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    conversation.append({"role": "user", "content": user_msg})
    with trace("Bunq‑REST"):
        time.sleep(3)
        res = finn_loop()

    if voice_bool:

        # Get the last message from the response
        last_message = res["messages"][-1]["text"]
        # Remove emojis from the text
        last_message = drop_emojis(last_message)
        # Synthesize speech and save to a file
        audio_file = synthesize_speech(
            text=last_message,
            language_code="en-US",
            voice_name="en-US-Studio-O",
        )
        # Add the audio file path to the response
        res["audio"] = base64.b64encode(audio_file).decode("utf-8")
        return jsonify(res)
    else:
        return jsonify(res)


@app.post("/reset")
def reset():
    conversation.clear()
    context.__dict__.update(BunqAgentContext().__dict__)  # re‑init
    return jsonify({"ok": True})


@app.post("/voice")
def process_voice():
    audio = request.files.get("audio")  # Use files.get instead of form.get
    voice_bool = request.form.get("requestAudio", False)
    print(voice_bool)
    if not audio:
        return jsonify({"error": "No audio file provided"}), 400

    try:
        # Save the audio file temporarily
        temp_filename = f"temp_audio_{uuid.uuid4()}.webm"
        audio.save(temp_filename)

        print(f"Saved audio file: {temp_filename}")

        speech_client = SpeechClient()

        # Configure audio
        with open(temp_filename, "rb") as audio_file:
            time.sleep(3)
            content = audio_file.read()

        speech_client = SpeechClient()

        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=["en-US"],
            model="latest_long",
        )

        # Use recognizer that already exists instead of creating a new one
        recognizer_name = (
            f"projects/gen-lang-client-0093539692/locations/global/recognizers/_"
        )

        with open(temp_filename, "rb") as audio_file:
            content = audio_file.read()

        speech_recognize_request = cloud_speech.RecognizeRequest(
            recognizer=recognizer_name,
            config=config,
            content=content,  # Use content instead of uri
        )

        response = speech_client.recognize(request=speech_recognize_request)
        transcribed_text = ""
        for result in response.results:
            transcribed_text += result.alternatives[0].transcript

        print(f"Transcribed text: {transcribed_text}")

        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        # If transcription is empty, return an error
        if not transcribed_text:
            return jsonify({"error": "Could not transcribe audio"}), 400

        # Process the transcribed text through the chat system
        conversation.append({"role": "user", "content": transcribed_text})

        with trace("Bunq‑REST"):
            result = finn_loop()

        # Return the same response format as the chat endpoint
        res = {
            **result,
            "transcription": transcribed_text,  # Include the transcription for debugging
        }
        if voice_bool:

            # Get the last message from the response
            last_message = res["messages"][-1]["text"]
            # Remove emojis from the text
            last_message = drop_emojis(last_message)
            # Synthesize speech and save to a file
            audio_file = synthesize_speech(
                text=last_message,
                language_code="en-US",
                voice_name="en-US-Studio-O",
            )
            # Add the audio file path to the response
            res["audio"] = base64.b64encode(audio_file).decode("utf-8")
            return jsonify(res)
        else:
            return jsonify(res)

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Error processing voice: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# 7  Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if os.getenv("SERVER_MODE", "1") in {"1", "true", "yes"}:
        print("Serving on :5005 …")
        app.run(host="0.0.0.0", port=5005, debug=True)
    else:
        asyncio.run(cli_main())
