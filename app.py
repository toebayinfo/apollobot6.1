import os
import json
import logging
from quart import Quart, request, Response
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext
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

bot_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
bot_adapter = BotFrameworkAdapter(bot_settings)
bot = IngramMicroBot()

def create_app():
    app = Quart(__name__)

    @app.route("/", methods=["GET"])
    async def root():
        return Response(response="Welcome to IngramMicroBot", status=200)

    @app.route("/api/messages", methods=["POST"])
    async def messages():
        headers = {"Access-Control-Allow-Origin": "*"}
        if request.content_type != "application/json":
            logger.error(f"Unsupported Media Type: Content-Type must be application/json. Received: {request.content_type}")
            return Response(response="Unsupported Media Type: Content-Type must be application/json", status=415, headers=headers)

        try:
            body = await request.get_json()
            logger.info(f"Received request body: {json.dumps(body, indent=2)}")
        except Exception as e:
            logger.error(f"Error parsing request body: {e}")
            return Response(response=f"Error parsing request body: {e}", status=400, headers=headers)

        try:
            activity = Activity().deserialize(body)
            logger.info(f"Deserialized activity: {activity}")
        except Exception as e:
            logger.error(f"Failed to deserialize activity: {e}")
            return Response(response=f"Failed to deserialize activity: {e}", status=400, headers=headers)

        # Check if required fields are present
        required_fields = ['service_url', 'channel_id', 'from_property', 'conversation']
        missing_fields = [field for field in required_fields if getattr(activity, field, None) is None]
        if missing_fields:
            logger.error(f"Missing required fields in activity: {missing_fields}")
            return Response(response=f"Missing required fields: {missing_fields}", status=400, headers=headers)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            logger.error("Authorization header is missing")
            return Response(response="Unauthorized: Authorization header is missing", status=401, headers=headers)

        async def turn_call(turn_context: TurnContext):
            await bot.on_turn(turn_context)

        try:
            await bot_adapter.process_activity(activity, auth_header, turn_call)
            return Response(status=201, headers=headers)
        except Exception as e:
            logger.error(f"Error processing activity: {e}")
            return Response(response=str(e), status=500, headers=headers)

    @app.route("/health", methods=["GET"])
    async def health_check():
        return Response(status=200)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
