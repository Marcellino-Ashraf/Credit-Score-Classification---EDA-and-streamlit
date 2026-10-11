"""Gemini Live voice bridge, served as a WebSocket route on the Streamlit server itself.

    Browser mic (PCM 16 kHz)  ──►  /voice-ws  ──►  Gemini Live API
    Browser speaker (PCM 24 kHz) ◄──  /voice-ws  ◄──  Gemini Live API

app.py mounts ``voice_ws`` with ``st.App(..., routes=[WebSocketRoute("/voice-ws", voice_ws)])``, so the bridge uses
the same address and port as the app. That is what makes the assistant work on Streamlit Community Cloud,
where only the app's own port is reachable (a separate server on localhost:8765 is not).
"""

from __future__ import annotations

import asyncio
import json
import os

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from starlette.websockets import WebSocket

from utils import voice_visuals

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))  # local runs; on Streamlit Cloud the key comes from Secrets

LIVE_MODELS = ["gemini-3.8-live", "gemini-3.1-flash-live-preview"]


def api_key() -> str:
    """GEMINI_API_KEY from the environment / .env, or from Streamlit secrets (Streamlit Cloud)."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            key = ""
    return key


_df = pd.read_parquet(os.path.join(ROOT, "cleaned_data.parquet"))


def _build_summary(df) -> str:
    if df is None:
        return "البيانات غير متاحة."
    try:
        score_share = (df["Credit_Score"].value_counts() / len(df) * 100).round(1).to_dict()
        poor_by_job = df.groupby("Occupation")["Credit_Score"].agg(lambda s: round((s == "Poor").mean() * 100, 1))
        medians = df.groupby("Credit_Score")[[
            "Annual_Income", "Outstanding_Debt", "Interest_Rate", "Delay_from_due_date",
            "Num_of_Delayed_Payment", "Num_Credit_Card", "Num_Bank_Accounts", "Num_of_Loan",
            "Credit_History_Age_months",
        ]].agg("median").round(1).to_dict(orient="index")
        mix = df.groupby(["Credit_Mix", "Credit_Score"]).size().unstack(fill_value=0)
        mix = (mix.div(mix.sum(axis=1), axis=0) * 100).round(1).to_dict(orient="index")
        min_pay = df.groupby(["Payment_of_Min_Amount", "Credit_Score"]).size().unstack(fill_value=0)
        min_pay = (min_pay.div(min_pay.sum(axis=1), axis=0) * 100).round(1).to_dict(orient="index")
        return (
            f"بيانات تصنيف الجدارة الائتمانية - {len(df):,} سجل شهري لـ {df['Customer_ID'].nunique():,} عميل "
            f"من يناير لأغسطس:\n"
            f"توزيع التقييم الائتماني (%): {score_share}\n"
            f"نسبة التقييم الضعيف Poor لكل مهنة (%): {poor_by_job.sort_values(ascending=False).to_dict()}\n"
            f"القيم الوسيطة لكل تقييم: {medians}\n"
            f"توزيع التقييم حسب Credit Mix (%): {mix}\n"
            f"توزيع التقييم حسب دفع الحد الأدنى فقط Payment_of_Min_Amount (%): {min_pay}\n"
            f"متوسط العمر: {round(df['Age'].mean(), 1)} سنة | المهن: {list(df['Occupation'].unique())}"
        )
    except Exception as e:
        return f"خطأ في تحليل البيانات: {e}"


DATA_SUMMARY = _build_summary(_df)

SYSTEM_PROMPT = f"""
أنت مساعد صوتي احترافي متخصص في تحليل بيانات الجدارة الائتمانية لعملاء البنك، وأسلوبك أسلوب محلل بيانات في اجتماع عمل.
تتحدث باللهجة المصرية الواضحة بأسلوب مهني ومحترم، وتخاطب المستخدم بـ "حضرتك".
ممنوع تماماً استخدام أي ألفاظ عامية أو ودية زي: يا باشا، يا صاحبي، يا عم، يا معلم، يا سيدي، زي الفل، أو أي هزار.
تجيب بشكل موجز ودقيق لا يتجاوز ثلاث إلى أربع جمل مناسباً للاستماع الصوتي المباشر.
ابدأ بالإجابة مباشرة، وبعدها الرقم أو الدليل اللي بيدعمها.
قرّب الأرقام عند نطقها: الفلوس لأقرب دولار والنسب لأقرب رقم عشري واحد، ومتنطقش كسور زي القروش.
لا تستخدم أي رموز ماركداون أو نجوم أو هاشات لأن ردك ينطق صوتياً مباشرة.
التقييم الائتماني له ثلاث مستويات: Poor يعني ضعيف، Standard يعني متوسط، Good يعني جيد.
أمثلة على أسلوب كلامك: "بالنسبة لسؤال حضرتك...", "الأرقام بتوضح إن...", "زي ما حضرتك شايف في الرسم تحت..."

عندك أدوات بتعرض رسومات وأرقام (KPIs) على الشاشة تحت المساعد.
كل ما السؤال يكون عن مقارنة أو توزيع أو أرقام والرسم هيوضح الإجابة، استدعي الأداة المناسبة الأول قبل ما ترد.
استخدم الأرقام اللي بترجعها الأداة في ردك بالظبط، وقول للمستخدم إن الرسم ظهر تحت.
لو السؤال عادي ومش محتاج رسم (سلام، شرح مفهوم زي يعني إيه Credit Mix) رد من غير أدوات.

بيانات العملاء المتاحة:
{DATA_SUMMARY}
"""


async def _send_json(websocket: WebSocket, message: dict) -> bool:
    """Send a JSON message to the browser; False if the browser is gone."""
    try:
        await websocket.send_text(json.dumps(message))
        return True
    except Exception:
        return False


async def voice_ws(websocket: WebSocket) -> None:
    """One browser WebSocket connection = one Gemini Live session."""
    await websocket.accept()

    # ── 1. Read voice preference and the page session id from the browser ──
    voice, session_id = "Puck", ""
    try:
        cfg = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=5.0))
        voice = cfg.get("voice", "Puck")
        session_id = cfg.get("session", "")
    except Exception:
        pass

    key = api_key()
    if not key:
        await _send_json(websocket, {"type": "error", "message": "GEMINI_API_KEY مش موجود في الإعدادات (Secrets)."})
        await websocket.close()
        return

    # ── 2. Build Gemini Live config ──
    client = genai.Client(api_key=key)
    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))
        ),
        system_instruction=types.Content(parts=[types.Part.from_text(text=SYSTEM_PROMPT)]),
        tools=voice_visuals.TOOLS,  # functions Gemini can call to show KPIs and charts on the page
    )

    # ── 3. Connect to Gemini Live, bridge audio both ways ──
    connected = False
    for model_name in LIVE_MODELS:
        try:
            async with client.aio.live.connect(model=model_name, config=live_config) as session:
                connected = True
                await _send_json(websocket, {"type": "ready", "model": model_name})

                async def mic_to_gemini():
                    """Forward browser PCM → Gemini until the browser disconnects."""
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            return
                        if message.get("bytes"):
                            await session.send_realtime_input(
                                audio=types.Blob(data=message["bytes"], mime_type="audio/pcm;rate=16000")
                            )

                async def gemini_to_speaker():
                    """Forward Gemini PCM → browser.

                    ``session.receive()`` stops at the end of every turn, and a tool call ends a turn
                    before Gemini speaks the answer, so keep reading turn after turn.
                    """
                    while True:
                        got_message = False
                        async for response in session.receive():
                            got_message = True
                            # Gemini asked for a visual: build it for this page session, send the real numbers back
                            if response.tool_call:
                                replies = [
                                    types.FunctionResponse(
                                        id=fc.id, name=fc.name,
                                        response=voice_visuals.run_tool(fc.name, fc.args or {}, _df, session_id),
                                    )
                                    for fc in response.tool_call.function_calls
                                ]
                                await session.send_tool_response(function_responses=replies)
                                if not await _send_json(websocket, {"type": "visual"}):
                                    return
                            sc = response.server_content
                            if sc and sc.model_turn:
                                for part in sc.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        try:
                                            await websocket.send_bytes(part.inline_data.data)
                                        except Exception:
                                            return
                            if sc and sc.turn_complete:
                                if not await _send_json(websocket, {"type": "turn_complete"}):
                                    return
                        if not got_message:  # the Gemini session was closed
                            return

                mic_task = asyncio.create_task(mic_to_gemini())
                speak_task = asyncio.create_task(gemini_to_speaker())

                # Run both until one finishes (e.g. browser disconnects)
                done, pending = await asyncio.wait([mic_task, speak_task], return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass
            break  # clean exit from Gemini session
        except Exception as e:
            await _send_json(websocket, {"type": "error", "message": str(e)[:300]})

    if not connected:
        await _send_json(websocket, {"type": "error", "message": "النموذج مش متاح دلوقتي، جرب بعد شوية."})
    try:
        await websocket.close()
    except Exception:
        pass
