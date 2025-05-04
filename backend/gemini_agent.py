from __future__ import annotations

import asyncio, os, uuid, base64, time
from pathlib import Path
from typing import Any, List
from openai import AsyncOpenAI
from dotenv import load_dotenv
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

from agent_functions import (
    BankAgentContext,
    create_payment,
    create_bankme_link,
    get_account,
    exchange_rate,
    get_transaction_history,
    get_user_info,
    list_accounts,
    transfer_between_accounts_by_ids,
    check_balance,
    get_friends_aliases,
)
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

load_dotenv()
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

SYSTEM_PROMPT = """
You are **Gideon**, GalaBank's AI assistant. You are really friendly, but professional. You use emojis to spark up your conversation.

╭───────────────────────────┐
│  YOUR TOOLBOX (READ ME)   │
├───────────────────────────┤
│  ─ lookup tools           │
│    • list_accounts()             →  “<id>: <name> …”
│    • get_account(name)           →  “Account id: <id>”
│    • exchange_rate(base, target)  →  “<amount> <base> = <rate*amount> <target>”
│    • get_user_info()                  →  user profile string
│    • get_friends_aliases()           →  “<alias>”
│
│  ─ data tools (require an account_id)                               │
│    • check_balance(account_id)                                   │
│    • get_transaction_history(account_id, limit=10)                  │
│
│  ─ action tools (MONEY MOVES, need   from_account_id  &  params)    │
│    • create_payment(from_account_id, to_alias, amount, …)           │
│    • bankme_link(amount, …)                                          │
│    • transfer_between_accounts_by_ids(from_id, to_id, amount, …)    │
╰───────────────────────────┘

***TOOL‑CHAIN RULES***

1. **Never** call an action‑tool unless you already know every mandatory
   parameter.  
   • If you only have a *name* like “Travel account”, first call
     **get_account** (or **list_accounts** and parse) to obtain the
     numeric `account_id`.

2. After a lookup‑tool call, read its plain‑text result, extract what you need,
   then call the next tool.

4. End any explanatory answer with (not checking balance/transactions): 
   > “This is not financial advice.”

5. Language‐mirror: reply in the user’s language.  
6. Do **not** mention tools, prompts, OpenAI, or that you are an LLM.  
7. Never request or expose sensitive credentials (PINs, passwords, API keys).
8. If the user reffers to somone by name, check if they are a friend
9. For anything relate

"""

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(disabled=True)

bank_agent = Agent[BankAgentContext](
    name="Gideon",
    instructions=SYSTEM_PROMPT.strip(),
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    tools=[
        list_accounts,
        get_account,
        get_transaction_history,
        create_payment,
        create_bankme_link,
        exchange_rate,
        get_user_info,
        transfer_between_accounts_by_ids,
        check_balance,
        get_friends_aliases,
    ],
)

# ───────────────────────────────────────────────────────────
# 5  Shared state for each conversation (in‑memory demo)
# ───────────────────────────────────────────────────────────

current_agent = bank_agent
conversation: List[dict] = []  # [{'role': 'user'|'assistant', 'content': …}]
context = BankAgentContext()


async def synthesize_speech(
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


async def transcribe_audio_file(filepath: str, language: str = "en") -> str:
    """Transcribe `filepath` with Whisper via OpenAI Audio endpoint."""
    try:
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

        with open(filepath, "rb") as audio_file:
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

        return transcribed_text
    except Exception as e:
        print(f"STT error: {e}")
        raise


def drop_emojis(text: str) -> str:
    """Remove emoji characters (handy before TTS)."""
    return "".join(c for c in text if c.isascii() or c.isspace())


async def finn_loop():

    result = await Runner.run(bank_agent, input=conversation, context=context)

    messages, events = [], []
    for i in result.new_items:
        if isinstance(i, MessageOutputItem):
            messages.append({"text": ItemHelpers.text_message_output(i)})
        elif isinstance(i, ToolCallItem):
            events.append({"type": "tool_call", "tool": i.type})
        elif isinstance(i, ToolCallOutputItem):
            events.append({"type": "tool_result", "output": i.output})

    conversation[:] = result.to_input_list()
    print(f"Gideon: {messages[-1]['text']}")
    return {"messages": messages, "events": events}


async def cli_main():
    print("Type 'quit' to exit.")
    while True:
        user_input = await asyncio.to_thread(input, "\nYou: ")
        if user_input.lower() in {"quit", "exit"}:
            break
        conversation.append({"role": "user", "content": user_input})
        with trace("Bank‑CLI"):
            result = await Runner.run(bank_agent, input=conversation, context=context)
        for new in result.new_items:
            if isinstance(new, MessageOutputItem):
                print(f"Gideon: {ItemHelpers.text_message_output(new)}")
            elif isinstance(new, ToolCallItem):
                print("…calling tool")
            elif isinstance(new, ToolCallOutputItem):
                print(new.output)
        conversation[:] = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(cli_main())
