from quart import Quart, request, Response
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter
from botbuilder.schema import Activity
import asyncio
from bot import IngramMicroBot
import logging
import os
import signal

# Set up logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = Quart(__name__)

bot_settings = BotFrameworkAdapterSettings("", "")
bot_adapter = BotFrameworkAdapter(bot_settings)
bot = IngramMicroBot()
asyncio.run(bot.load_excel_data())

def signal_handler():
    logger.info("Received shutdown signal, closing application...")
    # Add any cleanup code here (e.g., closing database connections)

app.signal_handler = signal_handler

@app.route("/api/messages", methods=["POST"])
async def messages():
    if "application/json" in request.headers["Content-Type"]:
        body = await request.get_json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    async def turn_call(turn_context):
        await bot.on_turn(turn_context)

    try:
        logger.debug("Processing activity")
        await bot_adapter.process_activity(activity, auth_header, turn_call)
        logger.debug("Activity processed")
        return Response(status=201)
    except Exception as e:
        logger.error(f"Error processing activity: {str(e)}")
        return Response(status=500)