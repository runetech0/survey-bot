from telethon import TelegramClient, Button, events, errors
from telethon.tl.types import KeyboardButtonCallback
import socks
import conf
import logging
from box import Box
from pymongo import MongoClient
import random
import re
import time
from colorama import Back, Fore, Style, init


# #######################################################< Global Variables >#######################################################

API_ID = '1219125'
API_HASH = 'd15e36f952698015e9f8384b2d0c547d'
bot_token = '1205226796:AAF7YbFu4r95UZ8CQWH41IwezalzYiG5QyE'

dr = '-------------------------------------------\n'
nl = '\n'

expectingQuestion = False
expectingAnswers = False
exSeqName = False
exPollResult = False
pollResExpected = []
currentPollIndex = 0
pollsList = []

poll = Box({})

adminButtons = Box({
    'home': Button.inline("Home", b'home'),
    'deploy': Button.inline("Deploy Sequence", b'deploy'),
    'list_sequences': Button.inline("List Sequences", b'list_sequences'),
    'new_poll': Button.inline("New Poll", b'new_poll'),
    'remove_sequence': Button.inline("Remove Sequence", b'remove_sequence'),
    'exit': Button.inline('Exit', b'exit'),
})

pollButtons = Box({
    'single_answer': Button.inline('Single Answer', b'single_answer'),
    'multi_answer': Button.inline('Multi Answer', b'multi_answer'),
    'discard': Button.inline('Discard Poll', b'poll_discard'),
    'save': Button.inline('Save Poll', b'poll_save')
})


# #######################################################< Initialisations >#######################################################


init(autoreset=True)
TC = Box({
    'SUCCESS': f'{Back.BLACK}{Fore.GREEN}{Style.BRIGHT}',
    'FAIL': f'{Back.BLACK}{Fore.RED}{Style.BRIGHT}',
    'WARNING': f'{Back.BLACK}{Fore.YELLOW}{Style.BRIGHT}'
})


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s :: %(levelname)s :: %(message)s')

client = TelegramClient('new', API_ID, API_HASH, proxy=(socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))


# #######################################################< Helper functions >#######################################################


async def sendMsg(msg, btns):
    sent_msg = await client.send_message(conf.ADMIN_ID, msg, buttons=btns)
    return sent_msg


async def getMsg():
    @client.on(events.NewMessage())
    async def getQ(msg):
        return Box(msg.to_dict())


async def homePage():
    msg = f'{dr}\nAdmin pannel\n{dr}'
    buttons = [
        [
            adminButtons.new_poll,
            adminButtons.list_sequences
        ],
        [
            adminButtons.remove_sequence,
            adminButtons.deploy
        ],
        [
            adminButtons.exit
        ]
    ]
    await sendMsg(msg, buttons)


def getContent(msg):
    m = Box(msg.to_dict())
    return m.message.message


# #######################################################< Poll Creation >#######################################################


async def fSeqName(msg):
    global exSeqName
    if exSeqName:
        return True
    else:
        return False


@client.on(events.NewMessage(func=fSeqName))
async def getSeqName(msg):
    global exSeqName, poll
    poll.seqName = getContent(msg)
    exSeqName = False
    btns = [
        [
            pollButtons.multi_answer,
            pollButtons.single_answer
        ],
        [
            pollButtons.discard
        ]
    ]
    await sendMsg(f'{dr}Select the type of poll.', btns)


async def answerFilter(msg):
    if expectingAnswers:
        return True
    else:
        return False


@client.on(events.NewMessage(func=answerFilter))
async def getAnswers(msg):
    global poll, expectingAnswers
    m = Box(msg.to_dict())
    ans = m.message.message
    poll.answers = ans.split(',')
    tmp_list = []
    for an in poll.answers:
        an = an.strip()
        tmp_list.append(an)
    poll.answers = tmp_list
    expectingAnswers = False
    await sendMsg(f'{dr}Sequence Name: {poll.seqName}{nl}Question: {poll.question}{nl}Answers:{nl}{nl.join(poll.answers)}', [pollButtons.discard, pollButtons.save])


async def questionFilter(msg):
    if expectingQuestion:
        return True
    else:
        return False


@client.on(events.NewMessage(func=questionFilter))
async def questionHandler(msg):
    global poll, expectingQuestion, expectingAnswers
    m = Box(msg.to_dict())
    poll.question = m.message.message
    expectingQuestion = False
    expectingAnswers = True
    btns = [
        [
            pollButtons.discard
        ]
    ]
    await sendMsg(f'{dr}Enter the answers separated with commas each answer!', btns)


@client.on(events.CallbackQuery(data=b'poll_discard'))
async def poll_discard(event):
    await event.delete()
    await homePage()


@client.on(events.CallbackQuery(data=b'single_answer'))
async def single_answer(event):
    global expectingQuestion, poll
    if 'properties' not in poll.keys():
        poll.properties = Box({})
    poll.properties.single_answer = True
    expectingQuestion = True
    btns = [
        [
            pollButtons.discard
        ]
    ]
    await event.edit(f'{dr}Send the question for the poll.', buttons=btns)


@client.on(events.CallbackQuery(data=b'multi_answer'))
async def multi_answer(event):
    global expectingQuestion, poll
    if 'properties' not in poll.keys():
        poll.properties = Box({})
    poll.properties.multi_answer = True
    expectingQuestion = True
    btns = [
        [
            pollButtons.discard
        ]
    ]
    await event.edit(f'{dr}Send the question for the poll.', buttons=btns)


# #######################################################< Poll Deployment >#######################################################

async def filterPoll(e):
    print(pollResExpected)
    if exPollResult:
        if e.data in pollResExpected:
            return True
    else:
        return False


@client.on(events.CallbackQuery(func=filterPoll))
async def getPollResult(e):
    global exPollResult, pollResExpected, currentPollIndex, pollsList
    await e.edit('Got poll answer!')
    exPollResult = False
    pollResExpected = []
    currentPollIndex += 1
    try:
        pollsList[currentPollIndex]
        await survey_user()
    except IndexError:
        currentPollIndex = 0
        pollsList = []
        return


async def createPolls(raw_polls):
    pass


async def survey_user():
    global exPollResult, currentPollIndex, pollsList, pollResExpected
    try:
        poll = pollsList[currentPollIndex]
        exPollResult = True
    except IndexError:
        currentPollIndex = 0
        pollsList = []
        return
    poll = Box(poll)
    btns = []
    for an in poll.answers:
        an = str(an)
        b_an = an.encode()
        print(b_an)
        btn = Button.inline(an, b_an)
        pollResExpected.append(b_an)
        btns.append(btn)

    await sendMsg(poll.question, btns)

# #######################################################< Admin Tasks Handlers >#######################################################


@client.on(events.CallbackQuery(data=b'home'))
async def home(event):
    await homePage()


@client.on(events.CallbackQuery(data=b'deploy'))
async def deploy(event):
    global pollsList
    poll1 = {
        'question': 'What is your age?',
        'answers': [12, 18, 20, 22]
    }
    poll2 = {
        'question': 'Your Favourite Programming language?',
        'answers': ['python', 'java', 'javascript', 'c++']
    }
    pollsList = [poll1, poll2]
    await survey_user()


@client.on(events.CallbackQuery(data=b'list_sequences'))
async def list_sequences(event):
    await event.edit('\n\nThanks for using! Bye!')


@client.on(events.CallbackQuery(data=b'new_poll'))
async def new_poll(event):
    global exSeqName
    btns = [
        [
            pollButtons.discard
        ]
    ]
    await event.edit(f'{dr}Enter the sequence name.', buttons=btns)
    exSeqName = True


@client.on(events.CallbackQuery(data=b'remove_sequence'))
async def remove_sequence(event):
    await event.edit(f'Thanks for using! Bye!')


@client.on(events.CallbackQuery(data=b'exit'))
async def exit_handler(event):
    await event.edit(f'Thanks for using! Bye!{dr}{dr}{dr}')


# #######################################################< Message Events >#######################################################

async def filterAdmin(e):
    e = Box(e.to_dict())
    if e.message.from_id == conf.ADMIN_ID:
        return True
    else:
        return False


@client.on(events.NewMessage(func=filterAdmin, pattern='/start'))
async def adminHandler(event):
    e = Box(event.to_dict())
    print(e.message.from_id)
    print(conf.ADMIN_ID)
    await homePage()


try:
    client.start(bot_token=bot_token)
    print(f"{TC.SUCCESS}\n-------------------------\nBot is up!\n-------------------------\n")
    print("To run in the background type 'nohup python /path/to/app &' command. Thanks!\n")
    client.run_until_disconnected()
except KeyboardInterrupt:
    print("\nQuiting bot!")
except errors.rpcerrorlist.ApiIdInvalidError:
    print("Invalid API_ID/API_HASH")
