from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio, os, uuid, base64, time
from pathlib import Path
from agents import trace
from gemini_agent import (
    conversation,
    finn_loop,
    synthesize_speech,
    transcribe_audio_file,
    drop_emojis,
    context,
    BankAgentContext,
)

app = Flask(__name__)
CORS(app)


@app.post("/chat")
async def chat():
    user_msg = request.json.get("message", "").strip()
    voice_bool = request.json.get("requestAudio", False)
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    conversation.append({"role": "user", "content": user_msg})
    with trace("Bank-REST"):
        time.sleep(3)  # simulate latency for demo
        res = await finn_loop()

    if voice_bool:
        last_message = drop_emojis(res["messages"][-1]["text"])
        audio_bytes = await synthesize_speech(last_message)
        res["audio"] = base64.b64encode(audio_bytes).decode("utf-8")
    return jsonify(res)


@app.post("/reset")
def reset():
    conversation.clear()
    context.__dict__.update(BankAgentContext().__dict__)
    return jsonify({"ok": True})


@app.post("/voice")
async def process_voice():
    audio_file = request.files.get("audio")  # multipart/form‑data file field
    voice_bool = request.form.get("requestAudio", False)
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    # ── save temporarily ──
    temp_path = Path(f"temp_audio_{uuid.uuid4()}.webm")
    audio_file.save(temp_path)

    try:

        transcribed_text = await transcribe_audio_file(str(temp_path), language="en")

        if not transcribed_text:
            return jsonify({"error": "Could not transcribe audio"}), 400

        conversation.append({"role": "user", "content": transcribed_text})
        with trace("Bank-REST"):
            result = await finn_loop()

        res = {**result, "transcription": transcribed_text}

        if voice_bool:
            last_message = drop_emojis(res["messages"][-1]["text"])
            audio_bytes = await synthesize_speech(last_message)
            res["audio"] = base64.b64encode(audio_bytes).decode("utf-8")
        return jsonify(res)

    finally:
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
