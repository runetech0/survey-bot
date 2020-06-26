from telethon import TelegramClient, Button, events
from telethon.tl.types import KeyboardButtonCallback
import socks
import conf
import logging
from box import Box
API_ID = '1219125'
API_HASH = 'd15e36f952698015e9f8384b2d0c547d'
bot_token = '1205226796:AAF7YbFu4r95UZ8CQWH41IwezalzYiG5QyE'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s :: %(levelname)s :: %(message)s')


client = TelegramClient('new', API_ID, API_HASH, proxy=(socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))


async def filterAdmin(e):
    e = Box(e.to_dict())
    if e.message.from_id == conf.ADMIN_ID:
        return True
    else:
        return False


@client.on(events.CallbackQuery)
async def handler(event):
    print('Clicked')
    await event.edit(buttons=[
        Button.inline("First option", b"1"),
        Button.inline("Second option", b"2")
    ])


@client.on(events.NewMessage(pattern='/options'))
async def handler(event):
    en = await client.get_entity('me')
    print(en)

    keyboard = [
        [
            Button.inline("First option", b"1"),
            Button.inline("Second option", b"2")
        ],
        [
            Button.inline("Third option", b"3"),
            Button.inline("Fourth option", b"4")
        ],
        [
            Button.inline("Fifth option", b"5")
        ]
    ]

    await client.send_message("@telenot1337", "Choose an option:", buttons=keyboard)


client.start(bot_token=bot_token)
print('Started!')
client.run_until_disconnected()
