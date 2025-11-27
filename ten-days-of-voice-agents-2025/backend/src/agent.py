
import logging
import json
import os
from datetime import datetime
from typing import Annotated, Optional
from dataclasses import dataclass, asdict

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)

# Plugins
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ======================================================
# 💾 DATABASE (JSON)
# ======================================================

DB_FILE = "fraud_db.json"

@dataclass
class FraudCase:
    userName: str
    securityIdentifier: str
    cardEnding: str
    transactionName: str
    transactionAmount: str
    transactionTime: str
    transactionSource: str
    case_status: str = "pending_review"
    notes: str = ""

def load_db():
    path = os.path.join(os.path.dirname(__file__), DB_FILE)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    path = os.path.join(os.path.dirname(__file__), DB_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ======================================================
# 🧠 STATE
# ======================================================

@dataclass
class Userdata:
    active_case: Optional[FraudCase] = None

# ======================================================
# 🛠️ TOOLS (FIXED)
# ======================================================

@function_tool
async def lookup_customer(
    ctx: RunContext[Userdata],
    name: Annotated[str, Field(description="Customer first name")]
) -> str:
    """
    Loads the fraud case from JSON by username.
    """
    
    data = load_db()
    name = name.strip().lower()

    # Fuzzy match: "John", "john", "john doe"
    found_record = next(
        (item for item in data if item["userName"].lower() in name or name in item["userName"].lower()), 
        None
    )

    if not found_record:
        return "NO_MATCH"

    ctx.userdata.active_case = FraudCase(**found_record)

    return (
        f"FOUND|SecurityID={found_record['securityIdentifier']}|"
        f"Amount={found_record['transactionAmount']}|"
        f"Name={found_record['transactionName']}|"
        f"Source={found_record['transactionSource']}|"
        f"Time={found_record['transactionTime']}"
    )


@function_tool
async def resolve_fraud_case(
    ctx: RunContext[Userdata],
    status: Annotated[str, Field(description="'confirmed_safe' or 'confirmed_fraud'")],
    notes: Annotated[str, Field(description="Summary note")]
) -> str:
    """
    Updates the fraud case in the JSON DB.
    """

    if not ctx.userdata.active_case:
        return "ERROR: No case loaded."

    case = ctx.userdata.active_case
    case.case_status = status
    case.notes = notes

    data = load_db()

    # update the JSON database
    for i, item in enumerate(data):
        if item["userName"] == case.userName:
            data[i] = asdict(case)
            break

    save_db(data)

    if status == "confirmed_fraud":
        return f"UPDATED_FRAUD|Card {case.cardEnding} has been blocked."
    else:
        return "UPDATED_SAFE|Transaction marked legitimate."

# ======================================================
# 🤖 AGENT LOGIC (IMPROVED)
# ======================================================

class FraudAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
You are ALEX, Senior Fraud Specialist at Global Bank.

FOLLOW THIS EXACT FLOW:

-------------------------------------------------------
STEP 1 — GREETING & NAME COLLECTION
-------------------------------------------------------
Say: “Hello, this is the Fraud Department at Global Bank. May I have your first name?”

WAIT for the user’s name.
THEN IMMEDIATELY call:

lookup_customer(name="<name>")

-------------------------------------------------------
STEP 2 — PROCESS LOOKUP RESULT
-------------------------------------------------------

If lookup_customer returns "NO_MATCH":
    Say: "I couldn't find your record. Please repeat your name clearly."

If lookup_customer returns "FOUND|SecurityID=xxx|...":
    Extract security ID.
    Say: “To verify your identity, please tell me your Security Identifier.”

WAIT for user response.
Compare with SecurityID.
- If incorrect → say “Verification failed.” and END call.
- If correct → proceed.

-------------------------------------------------------
STEP 3 — SUSPICIOUS TRANSACTION REVIEW
-------------------------------------------------------

Read fields EXACTLY from the lookup response:
- Amount
- Name
- Source
- Time

Say:
“We flagged a transaction of [Amount] at [Name] from [Source] around [Time]. Did you make this transaction?”

WAIT for yes/no.

-------------------------------------------------------
STEP 4 — RESOLUTION
-------------------------------------------------------

If user says YES:
    call resolve_fraud_case(status="confirmed_safe", notes="User confirmed.")

If user says NO:
    call resolve_fraud_case(status="confirmed_fraud", notes="User denied transaction.")

-------------------------------------------------------
STEP 5 — CLOSING
-------------------------------------------------------
After tool result:
- If fraud → “Your card has been blocked and a new one will be issued.”
- If safe → “Great, your account is secure.”

END CALL.

IMPORTANT:
- NEVER ask for PIN, password, CVV, full card number.
- ALWAYS use the tools.
            """,
            tools=[lookup_customer, resolve_fraud_case],
        )

# ======================================================
# 🎬 ENTRYPOINT
# ======================================================

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-marcus",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )

    await session.start(
        agent=FraudAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC())
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
