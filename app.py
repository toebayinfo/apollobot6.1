import os
import json
import logging
from quart import Quart, request, Response
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter
from botbuilder.schema import Activity
from dotenv import load_dotenv
from bot import IngramMicroBot

# Load environment variables
load_dotenv()

# Set up logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use environment variables for App ID and Password
APP_ID = os.getenv("MicrosoftAppId", "")
APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")

# Set up the adapter
SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create the bot
BOT = IngramMicroBot()

app = Quart(__name__)

@app.route("/", methods=["GET"])
async def root():
    return Response(response="Welcome to IngramMicroBot", status=200)

@app.route("/api/messages", methods=["POST"])
async def messages():
    if "application/json" not in request.headers.get("Content-Type", ""):
        return Response(response="Unsupported Media Type", status=415)

    body = await request.get_data()
    
    try:
        activity = Activity().deserialize(json.loads(body))
    except Exception as e:
        logger.error(f"Failed to deserialize activity: {e}")
        return Response(status=400)

    auth_header = request.headers.get("Authorization", "")

    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        if response:
            return Response(json.dumps(response), status=200, mimetype='application/json')
        return Response(status=200)
    except Exception as e:
        logger.error(f"Error processing activity: {e}")
        return Response(status=500)

@app.route("/health", methods=["GET"])
async def health_check():
    return Response(status=200)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))