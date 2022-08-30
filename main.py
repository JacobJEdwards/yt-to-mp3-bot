import redis
import requests
import logging
import os

from telegram import *

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ContextTypes,
    PreCheckoutQueryHandler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

r = redis.Redis()
PAYMENT_TOKEN = ''


async def start(update: Update, context: CallbackContext) -> None:
    pass


async def helpInfo(update: Update, context: CallbackContext) -> None:
    pass


async def unknownCommand(update: Update, context: CallbackContext) -> None:
    pass


async def checkURL(update: Update, context: CallbackContext, url) -> bool:
    # if this url is valid, if returns true (status code 200, 404 means not true)
    testURL = f'https://www.youtube.com/oembed?url={url}'
    checkLink = requests.get(testURL)

    return checkLink.status_code == 200


async def getMP3(update: Update, context: CallbackContext) -> None:
    userID = update.effective_user.id
    userKey = f''


# sends invoice to upgrade user to premium
async def upgrade(update: Update, context: CallbackContext) -> None:
    # checks that the user is premium or not
    if r.sismember('premium', update.effective_user.id):
        keyboard = [
            [KeyboardButton("Get youtube video transcript!", callback_data="1")],
            [KeyboardButton("Support!", callback_data="3")],
        ]

        menu_markup = ReplyKeyboardMarkup(keyboard)
        await update.message.reply_text('You are premium!', reply_markup=menu_markup)

    # generates and sends the invoice to user
    else:
        chat_id = update.effective_message.chat_id
        title = "Premium Upgrade - Limitless Use!"
        description = 'Get unlimited uses, and full access to a range of bots now, and upcoming bots!\n\nContact ' \
                      '@JacobJEdwards for details '
        payload = 'Youtube to MP3 Bot Premium'
        currency = "USD"
        price = 15
        prices = [LabeledPrice('Upgrade', price * 10)]
        await context.bot.send_invoice(
            chat_id, title, description, payload, PAYMENT_TOKEN, currency, prices
        )


# checks that the data is correct after user agrees to pay
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != "Youtube to MP3 Bot Premium":
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


# called when the payment is successful
async def upgradeSuccessful(update: Update, context: CallbackContext) -> None:
    # saves user as premium - accessible from all bots linked to the database
    r.sadd('premium', update.effective_user.id)

    keyboard = [
        [KeyboardButton("Extract subtitles!", callback_data="1")],
        [KeyboardButton("Support!", callback_data="3")],
    ]
    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text('Upgrade successful! Welcome to premium.', reply_markup=menu_markup)



def main() -> None:
    application = Application.builder().token("5561745160:AAHLaEHPUZ1QGfdxcUrxnmJUKiI4WDo8pFY").build()

    # basic command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', helpInfo))

    # handles inline keyboard
    application.add_handler(CallbackQueryHandler(button))

    # handles the pre-made keyboard
    application.add_handler(MessageHandler(filters.Regex('Support!'), helpInfo))
    application.add_handler(MessageHandler(filters.Regex('Extract subtitles!'), sendURL))
    application.add_handler(MessageHandler(filters.Regex('Premium'), upgrade))

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    # post checkout handler
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, upgradeSuccessful))

    # handles a url being sent
    application.add_handler(MessageHandler(filters.ALL &
                                           (filters.Entity(MessageEntity.URL) | filters.Entity(
                                               MessageEntity.TEXT_LINK)),
                                           getMP3))

    # catch all handler
    application.add_handler(MessageHandler(filters.ALL, unknownCommand))

    # runs the bot
    application.run_polling()


# calls main
if __name__ == '__main__':
    main()
