import logging
import os
import zipfile

import redis
import requests
import yt_dlp as youtube_dl
from telegram import *
from telegram.error import TimedOut
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
PAYMENT_TOKEN = '284685063:TEST:NjE4ZTUwZjU3YjI3'


# basic start function
async def start(update: Update, context: CallbackContext) -> None:
    # gets user info and number of uses ect
    userName = update.effective_user.first_name
    userID = update.effective_user.id

    numUses = r.zscore('YTtoMP3Bot', userID)
    numUses = 0 if numUses is None else int(numUses)

    if numUses == 0:
        await update.message.reply_text(f'Hello {userName}\n\nWelcome to Youtube Video to MP3 Bot!\n\nThis bot is'
                                        f' used convert a Youtube video _(ie a music video)_ to an MP3 file!\n\n'
                                        f'To begin, simply send a Youtube video link, and the file will be '
                                        f'sent to you.\n\n', parse_mode='Markdown')

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


# help and support for user
async def helpInfo(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Help')
    # to expand


# arbitrary function
async def sendURL(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Send a Youtube Video URL to convert to an MP3 file:')


# unknown command function
async def unknownCommand(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Unknown command\n\nPlease use /help for help, or send a YouTube Video URL to extra'
                                    'ct the subtitle transcript!')


# checks that the url is a valid youtube video link
async def checkURL(update: Update, context: CallbackContext, url) -> bool:
    # if this url is valid, it returns true (status code 200, 404 means not true)
    testURL = f'https://www.youtube.com/oembed?url={url}'
    checkLink = requests.get(testURL)

    return checkLink.status_code == 200


# downloads YouTube video as mp3 file and sends it to the user
async def getMP3(update: Update, context: CallbackContext) -> None:
    userID = update.effective_user.id
    numUses = r.zscore('YTtoMP3Bot', userID)
    numUses = 0 if numUses is None else int(numUses)

    if numUses > 7 and not r.sismember('premium', userID):
        await update.message.reply_text('Sorry, you have reached the free trial limit.\n\nPlease update to premium '
                                        'for unlimited use')
        # sends inline keyboard to upgrade - callback data as keyboard used for other things
        inlineKeyboard = [[InlineKeyboardButton('Upgrade to Premium', callback_data='upgrade')]]
        reply_markup = InlineKeyboardMarkup(inlineKeyboard)

        await update.message.reply_text('Click:', reply_markup=reply_markup)
        return

    url = update.effective_message.text

    # if url is not valid, alerts the user then returns
    if not await checkURL(update, context, url):
        await update.message.reply_text('Sorry, this is not a valid YouTube video link.\nPlease send a valid link, '
                                        'use /help for support or contact me @JacobJEdwards')
        return

    message = await context.bot.send_message(chat_id=userID, text='_fetching video data..._', parse_mode='Markdown')
    messageID: int = message['message_id']

    try:
        # gets video info
        video_info = youtube_dl.YoutubeDL().extract_info(
            url=url, download=False
        )

        filename = f"{video_info['title']}.mp3"
        zipfilename = f"{video_info['title']}.zip"

        options = {
            'format': 'bestaudio/mp3',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'keepvideo': False,
            'outtmpl': filename,
        }

        await context.bot.edit_message_text(chat_id=userID, message_id=messageID,
                                            text='_Downloading file..._', parse_mode='Markdown')

        # downloads wav file with specified options
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([video_info['webpage_url']])

        await context.bot.edit_message_text(chat_id=userID, message_id=messageID,
                                            text='_Zipping file..._', parse_mode='Markdown')

        with zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(filename)

        await context.bot.edit_message_text(chat_id=userID, message_id=messageID,
                                            text='_Sending file..._', parse_mode='Markdown')
        await context.bot.send_document(chat_id=userID, document=open(zipfilename, 'rb'),
                                        pool_timeout=5, connect_timeout=30, read_timeout=30, write_timeout=45)
        await context.bot.edit_message_text(chat_id=userID, message_id=messageID, text='MP3 File Zipped:')
        # logs use to database
        r.zincrby('YTtoMP3Bot', 1, userID)

    except TimedOut:
        logger.error('TimedOut error')
        await context.bot.edit_message_text(chat_id=userID, message_id=messageID,
                                            text='Sorry, I\'m having a difficult time sending that video.'
                                                 '\nPlease try again:')

    except Exception as e:
        logger.error('unexpected error while running handler callback: %s', str(e), exc_info=True)
        await context.bot.edit_message_text(chat_id=userID, message_id=messageID,
                                            text='Sorry, I\'m having a difficult time sending that video.'
                                                 '\nPlease try again:')

    finally:
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(zipfilename):
            os.remove(zipfilename)


# handles inline keyboard callbacks
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    await query.answer()

    if query.data == 'upgrade':
        await query.edit_message_text(text="Thank you for choosing to upgrade!\nPay below:")
        await upgrade(update, context)
    else:
        await query.edit_message_text(text="Invalid option")


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
    application = Application.builder().token(***REMOVED***).build()

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
