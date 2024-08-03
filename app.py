import os
import json
import logging
from quart import Quart, request, Response
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, ConversationState, MemoryStorage
from botbuilder.schema import Activity
from dotenv import load_dotenv
from bot import IngramMicroBot

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_ID = os.getenv("MicrosoftAppId", "")
APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")

SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create ConversationState and MemoryStorage
MEMORY = MemoryStorage()
CONVERSATION_STATE = ConversationState(MEMORY)

# Create the Bot
BOT = IngramMicroBot(CONVERSATION_STATE)

app = Quart(__name__)

@app.route("/api/messages", methods=["POST"])
async def messages():
    if "application/json" in request.headers["Content-Type"]:
        body = await request.get_data()
        activity = Activity().deserialize(json.loads(body))
        auth_header = request.headers.get("Authorization", "")
        try:
            response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
            if response:
                return Response(json.dumps(response), status=200, mimetype="application/json")
            return Response(status=201)
        except Exception as e:
            logger.exception(f"Error processing activity: {e}")
            return Response(str(e), status=500)
    else:
        return Response("Unsupported Media Type", status=415)

@app.route("/", methods=["GET"])
async def index():
    return Response("Your bot is ready!", status=200)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))