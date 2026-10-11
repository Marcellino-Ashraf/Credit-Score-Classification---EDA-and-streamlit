"""
Voice Assistant Page — Gemini Live API bidirectional voice bridge.
Architecture:
  Browser Mic (PCM 16kHz) ──► WebSocket Server ──► Gemini Live API
  Browser Speaker ◄────────── WebSocket Server ◄── Gemini Live API (PCM 24kHz)
"""

import os
import asyncio
import threading
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv, find_dotenv

from utils import voice_visuals
from utils.components import page_header, sidebar_label

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

from google import genai
from google.genai import types

# ─────────────────────────────────────────────────────────
# Load .env at MODULE level (runs once per server start)
# ─────────────────────────────────────────────────────────
_dotenv = find_dotenv()
if not _dotenv:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _cand = os.path.join(_base, ".env")
    if os.path.exists(_cand):
        _dotenv = _cand
if _dotenv:
    load_dotenv(_dotenv)

API_KEY = os.getenv("GEMINI_API_KEY", "")
WS_PORT = 8765

# ─────────────────────────────────────────────────────────
# Load dataset & build data summary (once at module level)
# ─────────────────────────────────────────────────────────
def _load_data():
    candidates = [
        "cleaned_data.csv",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cleaned_data.csv"),
        "cleaned_data.parquet",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cleaned_data.parquet"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return pd.read_csv(p) if p.endswith(".csv") else pd.read_parquet(p)
    return None


_df = _load_data()


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

# ─────────────────────────────────────────────────────────
# Gemini Live ↔ WebSocket Bridge  (runs in background thread)
# ─────────────────────────────────────────────────────────
LIVE_MODELS = ["gemini-3.8-live", "gemini-3.1-flash-live-preview"]


async def _handle_ws_connection(websocket):
    """One browser WebSocket connection = one Gemini Live session."""
    # ── 1. Read voice preference from browser ──
    voice = "Puck"
    try:
        first = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        if isinstance(first, str):
            cfg = json.loads(first)
            voice = cfg.get("voice", "Puck")
    except Exception:
        pass

    # ── 2. Build Gemini Live config ──
    local_client = genai.Client(api_key=API_KEY)
    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=SYSTEM_PROMPT)]
        ),
        tools=voice_visuals.TOOLS,  # functions Gemini can call to show KPIs and charts on the page
    )

    # ── 3. Connect to Gemini Live, bridge audio ──
    connected = False
    for model_name in LIVE_MODELS:
        try:
            async with local_client.aio.live.connect(model=model_name, config=live_config) as session:
                connected = True
                await websocket.send(json.dumps({"type": "ready", "model": model_name}))

                async def mic_to_gemini():
                    """Forward browser PCM → Gemini."""
                    async for msg in websocket:
                        if isinstance(msg, bytes) and len(msg) > 0:
                            await session.send_realtime_input(
                                audio=types.Blob(data=msg, mime_type="audio/pcm;rate=16000")
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
                            # Gemini asked for a visual: build it for the page, send the real numbers back
                            if response.tool_call:
                                replies = [
                                    types.FunctionResponse(id=fc.id, name=fc.name,
                                                           response=voice_visuals.run_tool(fc.name, fc.args or {}, _df))
                                    for fc in response.tool_call.function_calls
                                ]
                                await session.send_tool_response(function_responses=replies)
                                try:
                                    await websocket.send(json.dumps({"type": "visual"}))
                                except Exception:
                                    return
                            sc = response.server_content
                            if sc and sc.model_turn:
                                for part in sc.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        try:
                                            await websocket.send(part.inline_data.data)
                                        except Exception:
                                            return
                            if sc and sc.turn_complete:
                                try:
                                    await websocket.send(json.dumps({"type": "turn_complete"}))
                                except Exception:
                                    return
                        if not got_message:  # the Gemini session was closed
                            return

                mic_task = asyncio.create_task(mic_to_gemini())
                speak_task = asyncio.create_task(gemini_to_speaker())

                # Run both until one finishes (e.g. browser disconnects)
                done, pending = await asyncio.wait(
                    [mic_task, speak_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass
            break  # clean exit from Gemini session
        except Exception as e:
            try:
                await websocket.send(json.dumps({"type": "error", "message": str(e)[:300]}))
            except Exception:
                pass

    if not connected:
        try:
            await websocket.send(
                json.dumps({"type": "error", "message": "النموذج مش متاح دلوقتي، جرب بعد شوية."})
            )
        except Exception:
            pass


_ws_started = False
_ws_lock = threading.Lock()


def _ensure_ws_server():
    global _ws_started
    with _ws_lock:
        if _ws_started:
            return
        _ws_started = True

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _serve():
            try:
                server = await websockets.serve(_handle_ws_connection, "localhost", WS_PORT)
                await server.wait_closed()
            except OSError:
                pass  # Port already bound by another worker

        loop.run_until_complete(_serve())

    t = threading.Thread(target=_run, daemon=True, name="gemini-live-ws-bridge")
    t.start()


if HAS_WS and API_KEY:
    _ensure_ws_server()

# ─────────────────────────────────────────────────────────
# HTML / JS Live Conversation Component (markup lives in assets/voice_widget.html)
# ─────────────────────────────────────────────────────────
_WIDGET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "voice_widget.html")


def _make_component(voice: str, ws_port: int) -> str:
    with open(_WIDGET_PATH, encoding="utf-8") as f:
        return f.read().replace("__WS_PORT__", str(ws_port)).replace("__VOICE__", voice)


# ─────────────────────────────────────────────────────────
# Streamlit Page
# ─────────────────────────────────────────────────────────
page_header("Voice Assistant", "Ask questions about the credit score data out loud (Egyptian Arabic, Gemini Live).",
            "microphone-lines")

# ── Sidebar ──
with st.sidebar:
    sidebar_label("Gemini Live Voice")
    voice_sel = st.selectbox(
        "نبرة الصوت:",
        options=["Puck", "Aoede", "Kore", "Fenrir", "Charon"],
        index=0,
        help="أصوات Gemini Live الطبيعية المدمجة في النموذج"
    )
    st.divider()
    if not API_KEY:
        st.error("`GEMINI_API_KEY` غير موجودة في `.env`")
    elif not HAS_WS:
        st.error("`websockets` غير مثبتة")
    else:
        st.success("Gemini Live Bridge جاهز")

    rows = len(_df) if _df is not None else 0
    st.caption(f"البيانات: **{rows:,}** سجل  |  `gemini-3.8-live`")

# ── Main component ──
_, center, _ = st.columns([1, 2, 1])
with center:
    components.html(_make_component(voice_sel, WS_PORT), height=520, scrolling=False)


# ── Live visuals: KPIs and charts the assistant decides to show ──
@st.fragment(run_every=2)
def _live_visuals():
    """Re-runs every 2 seconds (only this part of the page) and draws the newest visual from the assistant."""
    visual = voice_visuals.latest_visual()
    if visual is None:
        st.html('<div class="empty"><i class="fa-solid fa-chart-column"></i>'
                '<p class="empty__msg">الرسومات والأرقام هتظهر هنا</p>'
                '<p class="empty__hint">اسأل مثلاً: أنهي مهنة فيها أكتر تقييم ضعيف؟ أو: العملاء الكويسين دخلهم أعلى؟</p></div>')
    else:
        voice_visuals.render(visual)


_live_visuals()
