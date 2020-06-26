from telethon import TelegramClient, errors, events, functions
from telethon.tl.types import InputMediaPoll, Poll, PollAnswer
# from telethon.tl.types import UpdateMessagePoll, UpdateMessagePollVote
from pymongo import MongoClient
import conf as conf
import time
import random
import logging
import socks
# from datetime import datetime as dt
import re
from box import Box
from colorama import Back, Fore, Style, init

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s :: %(levelname)s :: %(message)s')
# logging.disable(logging.CRITICAL)
logging.disable(logging.DEBUG)


# ------------------------------------------- < Global Variables > -------------------------------------------

api_id = conf.API_ID
api_hash = conf.API_HASH
bot_token = '1205226796:AAF7YbFu4r95UZ8CQWH41IwezalzYiG5QyE'

known_commands = Box({
    '/help': 'Get this help message',
    '/deploy': '/deploy survey_name userid/groupid',
    '/sequence': '/sequence sequenceName',
    '/remove': '/remove survey_name',
    '/confirm': 'Confirm/Verify/Preview poll sequence',
    '/save': 'Save the current poll sequence to database',
    '/cancel': 'Discard the changes to poll sequence.',
    '/question': 'Enter question. i.e. /question What is your name?',
    '/answers': 'List of answers separated by commas. i.e. /answers Ali, John, Micheal Farady',
    '/new_poll': '',
    '/finish': '',
    '/change': '',
    '/list_polls': '',
    '/list_surveys': '',
    '/enable_anon_voting': '',
    '/disable_anon_voting': '',
    '/enable_multiple_answers': '',
    '/disable_multiple_answers': '',
    '/enable_quiz_mode': '',
    '/disable_quiz_mode': ''
})


nl = '\n'


currentSurvey = Box({})
pollsList = []
pollSchema = Box({})
poll = Box({})
pollAnswers = []
userData = Box({})


init(autoreset=True)
TC = Box({
    'SUCCESS': f'{Back.BLACK}{Fore.GREEN}{Style.BRIGHT}',
    'FAIL': f'{Back.BLACK}{Fore.RED}{Style.BRIGHT}',
    'WARNING': f'{Back.BLACK}{Fore.YELLOW}{Style.BRIGHT}'
})


# ------------------------------------------- < Database Setup > -------------------------------------------

dbClient = MongoClient(conf.DB_URL, conf.DB_PORT)
db = dbClient.surveyDB        # Database
allSurveys = db.allSurveys      # Collection for storing all the surveys


# ------------------------------------------- < Proxy Setup > -------------------------------------------
if conf.AUTHENTICATION:
    sockProxy = {
        "proxy_type": socks.SOCKS5,
        "addr": conf.SOCKS5_SERVER,
        "port": conf.SOCKS5_PORT,
        "rdns": True,
        "username": conf.USERNAME,
        "password": conf.PASSWORD
    }


if conf.PROXY:
    if conf.AUTHENTICATION:
        if conf.USERNAME != None and conf.PASSWORD != None:
            client = TelegramClient('anon', api_id, api_hash, proxy=sockProxy)
            bot = TelegramClient('bot', api_id, api_hash, proxy=sockProxy)
    elif not conf.AUTHENTICATION:
        print(f'Using proxy server {conf.SOCKS5_SERVER}:{conf.SOCKS5_PORT}')
        client = TelegramClient('anon', api_id, api_hash, proxy=(
            socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))
        bot = TelegramClient('bot', api_id, api_hash, proxy=(
            socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))
else:
    client = TelegramClient('anon', api_id, api_hash)

# ------------------------------------------- < Helper Functions > -------------------------------------------
# Get the answer from user if sent a single answer poll


async def guideRes(dict, list):
    retList = []
    for k, v in dict.items():
        if k in list:
            tmp_list = [k, v]
            st = ' : '.join(tmp_list)
            retList.append(st)
    return nl.join(retList)


async def getPollAnswer(chat_id, msg_id):
    while True:
        result = await client(functions.messages.GetPollResultsRequest(
            peer=chat_id,
            msg_id=msg_id
        ))
        result = Box(result.to_dict())
        if not result.updates[0].results.results:
            # print('No answer choosen!')
            time.sleep(1)
            continue
        for answer in result.updates[0].results.results:
            if answer.chosen:
                return answer
                break


async def filterAdmin(e):
    e = Box(e.to_dict())
    if e.message.from_id == conf.ADMIN_ID:
        return True
    else:
        return False


async def cmd_help():
    to_send = await guideRes(known_commands, ['/sequence', '/remove', '/list', '/deploy', '/help'])
    await sendMsg(to_send)


async def cmd_new_seq(seqName):
    cmdRegex = re.compile(r'/\w+')
    survey = Box({})
    survey.survey_name = seqName


async def cmd_remove(parameter_list):
    pass


async def cmd_list(parameter_list):
    pass


async def getCmd(fullCommand):
    regex = re.compile(r'(/\w+)')
    mo = regex.search(fullCommand)
    if mo == None:
        return None
    else:
        command = mo.groups()[0]
        return command


async def sendMsg(msg):
    sent_msg = await client.send_message(conf.BOT_CHAT_ID, msg)
    return sent_msg

# ------------------------------------------- < Events Handling > -------------------------------------------


async def createPolls(survey_polls):
    finalPollsList = []
    for cpoll in survey_polls:
        cpoll = Box(cpoll)
        answers = []
        # print(cpoll)
        for ans in cpoll.answers:
            b_ans = ans.encode()
            answers.append(PollAnswer(ans, b_ans))
        poll = Poll(
            id=random.choice(range(10000000, 100000000000)),
            question=cpoll.question,
            answers=answers
            # public_voters=cpoll.properties.anon_voting,
            # multiple_choice=cpoll.properties.multiple_answers,
            # quiz=cpoll.properties.quiz_mode
        )
        finalPollsList.append(poll)
    return finalPollsList


async def survey_user(user_chat_id, polls):
    to_send = '''Welcome to survey!
Please click on /start to begin survey.

                    /start
    '''
    await client.send_message(user_chat_id, to_send)

    @client.on(events.NewMessage(pattern='/start'))
    async def newMessageHandler(msg):
        pollsList = polls
        for poll in pollsList:
            sent_msg = await client.send_message(user_chat_id, file=InputMediaPoll(poll=poll))
            sent_msg = Box(sent_msg.to_dict())
            chat_id = sent_msg.to_id.chat_id
            msg_id = sent_msg.id
            # print(f'{chat_id} : {msg_id}')
            answer = await getPollAnswer(chat_id, msg_id)
            print(f'{answer}')
            # TODO: Store Answer in database

        await client.send_message(user_chat_id, 'Thank you for the survey!')
        return
    return


async def sequence(fullCommand):
    currentSurvey.clear()
    regex = re.compile(r'/sequence (\w+)')
    mo = regex.search(fullCommand)
    seqName = mo.groups()[0]
    foundDoc = allSurveys.find_one({'name': seqName})
    to_send = await guideRes(known_commands, ['/new_poll', '/cancel'])
    foundDoc = Box(foundDoc)
    if not foundDoc:
        currentSurvey.name = seqName
        finalMsg = f'Sequence not exists already new will be created!{nl}{to_send}'
        await sendMsg(f'{finalMsg}')
    else:
        currentSurvey.name = foundDoc.name
        finalMsg = f'Sequence already exists already, Existing will be updated!{nl}{to_send}'
        await sendMsg(f'{finalMsg}')


async def question(fullCommand):
    global poll, currentSurvey
    if 'name' not in currentSurvey.keys():
        to_send = await guideRes(known_commands, ['/help'])
        await sendMsg(f'Please select or creat a sequence before poll{nl}{to_send}')
        return
    if 'question' in poll.keys():
        if 'answers' in poll.keys():
            currentSurvey.polls.append(poll)
            poll.clear()
    qRegex = re.compile(r'/question (.*)')
    mo = qRegex.search(fullCommand)
    question = mo.groups()[0]
    poll.question = question
    to_send = await guideRes(known_commands, ['/answers', '/cancel'])
    await sendMsg(to_send)


async def answers(fullCommand, command):
    if 'question' in poll.keys():
        fullCommand = fullCommand.replace(command, '')
        answers = fullCommand.split(',')
        newAnswersList = []
        for an in answers:
            an = an.strip()
            newAnswersList.append(an)
        poll.answers = newAnswersList
        to_send = f'{poll.question}{nl}Answers:{nl}{poll.answers}{nl}{nl}   /save    /change    {nl}{nl}'
        await sendMsg(to_send)
    else:
        to_send = await guideRes(known_commands, ['/question', ''])
        await sendMsg(f'No question added for the poll.')


async def new_poll():
    if 'name' not in currentSurvey.keys():
        to_send = await guideRes(known_commands, ['/sequence', '/help'])
        await sendMsg(f'Please select poll sequence first{nl}{to_send}')
        return
    poll.clear()
    to_send = f'Anonymous Voting for new pole: {nl}Anonymous Voting:{nl}/enable_anon_voting     /disable_anon_voting'
    await sendMsg(f'{nl}{to_send}')
    return


async def save(fullCommand):
    global poll
    pollsList.append(poll)
    currentSurvey.allPolls = pollsList

    foundDoc = allSurveys.find_one({
        'name': currentSurvey.name
    })
    if not foundDoc:
        allSurveys.insert_one({
            'name': currentSurvey.name,
            'allPolls': currentSurvey.allPolls
        })
        custom_msg = f'Created new sequence, saved poll to sequence and updated the database.'
    else:
        foundDoc = Box(foundDoc)
        for poll in pollsList:
            foundDoc.allPolls.append(poll)

        allSurveys.update_one({
            'name': currentSurvey.name
        }, {'$set': {
            'allPolls': foundDoc.allPolls
        }})
        custom_msg = f'Updated sequence, saved poll to sequence and updated the database.'
    to_send = f'Click below commands to continue{nl}/new_poll       /finish'
    await sendMsg(f'{custom_msg}{nl}{to_send}')


async def change():
    poll.clear()
    to_send = await guideRes(known_commands, ['/question', '/cancel', '/help'])
    custom_msg = 'Please Recreat the poll using commands below'
    await sendMsg(f'{custom_msg}{nl}{to_send}')


async def finish():
    poll.clear()
    currentSurvey.clear()
    pollsList.clear()
    custom_msg = f'Finished sequence creation/update!'
    to_send = await guideRes(known_commands, ['/sequence', '/remove',
                                              '/list_surveys', '/list_polls', '/deploy', '/help'])
    await sendMsg(f'{custom_msg}{nl}{to_send}')


async def list_surveys():
    foundDocs = allSurveys.find({})
    seqList = []
    for index, doc in enumerate(foundDocs):
        doc = Box(doc)
        seqList.append(f'{index+1}. {doc.name}')
    to_send = nl.join(seqList)
    custom_msg = f'List of the sequences in the database.'
    await sendMsg(f'{custom_msg}{nl}{to_send}')


async def list_polls():
    pass


async def anon_voting(status: bool):
    if 'properties' not in poll.keys():
        poll.properties = Box({})
    poll.properties.anon_voting = status
    to_send = f'Multiple answers : {nl}/enable_multiple_answers         /disable_multiple_answers'
    await sendMsg(to_send)


async def multiple_answers(status: bool):
    poll.properties.multiple_answers = status
    to_send = f'Quiz Mode : {nl}/enable_quiz_mode         /disable_quiz_mode'
    await sendMsg(to_send)


async def quiz_mode(status: bool):
    if poll.properties.multiple_answers:
        poll.properties.quiz_mode = False
    else:
        poll.properties.quiz_mode = status
    to_send = f'Enter the question for poll using /question command: {nl}i.e. /question Your favourite food?'
    await sendMsg(to_send)


async def deploy(seqName, chat):
    foundDoc = allSurveys.find_one({'name': seqName})
    foundDoc = Box(foundDoc)
    finalPollsList = await createPolls(foundDoc.allPolls)
    await survey_user(chat, finalPollsList)


async def get_chat_id(o_msg):
    msg = Box(o_msg.to_dict())
    chat_id = msg.message.to_id.user_id
    return chat_id


async def get_sender_id(o_msg):
    msg = Box(o_msg.to_dict())
    sender_id = msg.message.from_id
    return sender_id


# This fuunction gets username or userid any resolves it to
# telegram entity
async def resolveEntity(entity):
    try:
        en = await client.get_entity(entity)
        return Box(en.to_dict())
    except ValueError:
        return None


def seq_exists(seqName):
    foundDoc = allSurveys.find_one({'name': seqName})
    if foundDoc:
        return True
    else:
        return False

# async def filterCmd(msg):
#     msg = Box(msg.to_dict())
#     fullCommand = msg.message.message
#     cmd = await getCmd(fullCommand)
#     expectedCmds = ['/qq', '/vv', '/dd']
#     if cmd in expectedCmds:
#         return True
#     else:
#         return False


# @client.on(events.NewMessage(func=filterCmd))
# async def cHandler(msg):
#     await sendMsg('Command matched!')


@client.on(events.NewMessage(func=filterAdmin))
async def nMessageHandler(msg):
    o_msg = msg
    msg = Box(msg.to_dict())
    # admin_id = msg.message.from_id
    fullCommand = msg.message.message
    command = await getCmd(fullCommand)
    if command:
        if command in known_commands.keys():
            if command == '/help':
                await cmd_help()
                return

            elif command == '/sequence':
                await sequence(fullCommand)
                return

            elif command == '/remove':
                await cmd_remove()

            elif command == '/list_polls':
                await list_polls()
                return

            elif command == '/list_surveys':
                await list_surveys()
                return

            elif command == '/deploy':
                data = fullCommand.replace(command, '')
                data = data.strip()
                data = data.split(' ')
                seqName = data[0]
                user_name = data[1]
                if not seq_exists(seqName):
                    await sendMsg(f'Sequence does not exist with name {seqName}')
                    return
                en = await resolveEntity(user_name)
                if not en:
                    await sendMsg(f'No user with name {user_name} exists on telegram!')
                    return
                await deploy(seqName, en.id)
                return

            elif command == '/question':
                await question(fullCommand)
                return

            elif command == '/answers':
                await answers(fullCommand, command)
                return

            elif command == '/single':
                pass

            elif command == '/cancel':
                pass

            elif command == '/new_poll':
                await new_poll()
                return

            elif command == '/save':
                await save(fullCommand)
                return

            elif command == '/change':
                await change()
                return

            elif command == '/finish':
                await finish()
                return

            elif command == '/enable_anon_voting':
                await anon_voting(True)
                return

            elif command == '/disable_anon_voting':
                await anon_voting(False)
                return

            elif command == '/enable_multiple_answers':
                await multiple_answers(True)
                return

            elif command == '/disable_multiple_answers':
                await multiple_answers(False)
                return

            elif command == '/enable_quiz_mode':
                await quiz_mode(True)
                return

            elif command == '/disable_quiz_mode':
                await quiz_mode(False)
                return

            else:
                pass
        else:
            print(f'{TC.FAIL}Unknown command!')


# @client.on(events.Raw(UpdateMessagePollVote))
# async def polls(msg):
#     print(msg)

# @client.on(events.Raw(UpdateMessagePoll))
# async def polls(msg):
#     print(msg)


# ------------------------------------------- < Bot Startup > -------------------------------------------
try:
    client.start()
    # bot.start(bot_token=bot_token)
    print(f"{TC.SUCCESS}\n-------------------------\nBot is up!\n-------------------------\n")
    print("To run in the background type 'nohup python /path/to/app &' command. Thanks!\n")
    client.run_until_disconnected()
    # bot.run_until_disconnected()
except KeyboardInterrupt:
    print("\nQuiting bot!")
except errors.rpcerrorlist.ApiIdInvalidError:
    print("Invalid API_ID/API_HASH")
