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
    userName = update.effective_user.first_name
    userID = update.effective_user.id
    userKey = f'video2mp3:{userID}'
    numUses = r.scard(userKey)

    if numUses == 0:
        await update.message.reply_text(f'Hello {userName}\n\nWelcome to Youtube Video to MP3 Bot!\n\nThis bot is'
                                        f' used convert a Youtube video _(ie a music video)_ to an MP3 file!\n\n'
                                        f'To begin, simply send a Youtube video link, and the transcript will be '
                                        f'sent to you.\n\n', parse_mode=Mark)

    if not r.sismember('premium', userID):
        await update.message.reply_text(f'You have {8 - numUses} uses remaining on your free trial.\n\nOr upgrade to '
                                        f'Premium for unlimited use across a number of different bots!')
        keyboard = [
            [KeyboardButton("YouTube Video to MP3", callback_data="1")],
            [
                KeyboardButton("Premium", callback_data="2"),
                KeyboardButton("Support!", callback_data="3"),
            ],
        ]
    else:
        await update.message.reply_text('Your account is premium!\n\nUnlimited use!')
        keyboard = [
            [KeyboardButton("YouTube Video to MP3", callback_data="1")],
            [KeyboardButton("Support!", callback_data="3")],
        ]

    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text('Send a URL to get started, or select an option below:', reply_markup=menu_markup)


async def helpInfo(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Help')
    # to expand


async def sendURL(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Send a Youtube Video URL to convert to an MP3 file:')


# unknown command function
async def unknownCommand(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Unknown command\n\nPlease use /help for help, or send a YouTube Video URL to extra'
                                    'ct the subtitle transcript!')


async def checkURL(update: Update, context: CallbackContext, url) -> bool:
    # if this url is valid, if returns true (status code 200, 404 means not true)
    testURL = f'https://www.youtube.com/oembed?url={url}'
    checkLink = requests.get(testURL)

    return checkLink.status_code == 200


async def getMP3(update: Update, context: CallbackContext) -> None:
    userID = update.effective_user.id
    userKey = f'video2mp3:{userID}'
    numUses = r.scard(userKey)

    if numUses > 7 and not r.sismember('premium', userID):
        # send message to user
        return

    url = update.effective_message.text
    if not checkURL(update, context, url):
        # inform user not video link
        return


async def button(update: Update, context: CallbackContext) -> None:



# sends invoice to upgrade user to premium
async def upgrade(update: Update, context: CallbackContext) -> None:
    # checks that the user is premium or not
    if r.sismember('premium', update.effective_user.id):
        keyboard = [
            [KeyboardButton("YouTube Video to MP3", callback_data="1")],
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
        [KeyboardButton("YouTube Video to MP3", callback_data="1")],
        [KeyboardButton("Support!", callback_data="3")],
    ]
    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text('Upgrade successful! Welcome to premium.', reply_markup=menu_markup)



def main() -> None:
    application = Application.builder().token("").build()

    # basic command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', helpInfo))

    # handles inline keyboard
    application.add_handler(CallbackQueryHandler(button))

    # handles the pre-made keyboard
    application.add_handler(MessageHandler(filters.Regex('Support!'), helpInfo))
    application.add_handler(MessageHandler(filters.Regex('YouTube Video to MP3'), sendURL))
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
