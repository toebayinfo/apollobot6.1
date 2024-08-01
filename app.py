from flask import Flask, request, Response
from botbuilder.core import BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from bot import IngramMicroBot
import logging
import os
import asyncio

# Set up logging
log_level = os.environ.get('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use environment variables for App ID and Password
APP_ID = os.environ.get("MicrosoftAppId", "")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")

logger.info(f"App ID: {APP_ID}, App Password: {'Set' if APP_PASSWORD else 'Not Set'}")

# Set up CloudAdapter
SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
AUTHENTICATION = ConfigurationBotFrameworkAuthentication(SETTINGS)
ADAPTER = CloudAdapter(AUTHENTICATION)

# Create bot instance
bot = IngramMicroBot()

@app.route("/api/messages", methods=["POST"])
def messages():
    if "application/json" in request.headers.get("Content-Type", ""):
        body = request.json
        logger.debug(f"Received body: {body}")
    else:
        return Response(status=415)

    async def call_bot(inner_adapter, inner_req, inner_res):
        activity = Activity().deserialize(inner_req.json)
        context = TurnContext(inner_adapter, activity)
        await bot.on_turn(context)

    try:
        logger.debug("Processing activity")
        task = asyncio.ensure_future(ADAPTER.process(request, Response, call_bot))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task)
        logger.debug("Activity processed")
        return Response(status=200)
    except Exception as e:
        logger.error(f"Error processing activity: {str(e)}", exc_info=True)
        return Response(status=500)

@app.route("/", methods=["GET"])
def index():
    return "Your bot is ready!"

if __name__ == "__main__":
    is_production = os.environ.get('WEBSITE_HOSTNAME') is not None
    if is_production:
        app.run()
    else:
        app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))