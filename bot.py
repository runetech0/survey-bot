from telethon import TelegramClient, types, errors, events, functions
from telethon.tl.types import InputMediaPoll, Poll, PollAnswer
from telethon.tl.custom import Button
from telethon.tl.types import UpdateMessagePoll
from telethon.tl.types import UpdateMessagePollVote
from pymongo import MongoClient
import conf as conf
import logging
import socks
import time
from datetime import datetime as dt
import re
from box import Box
from colorama import Back, Fore, Style, init

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s :: %(levelname)s :: %(message)s')
# logging.disable(logging.CRITICAL)
logging.disable(logging.DEBUG)


#------------------------------------------- < Global Variables > -------------------------------------------

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




#------------------------------------------- < Database Setup > -------------------------------------------

dbClient = MongoClient(conf.DB_URL, conf.DB_PORT)
db = dbClient.surveyDB        #Database
allSurveys = db.allSurveys      #Collection for storing all the surveys



#------------------------------------------- < Proxy Setup > -------------------------------------------
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
        client = TelegramClient('anon', api_id, api_hash, proxy=(socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))
        bot = TelegramClient('bot', api_id, api_hash, proxy=(socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))
else:
    client = TelegramClient('anon', api_id, api_hash) 

#------------------------------------------- < Helper Functions > -------------------------------------------
#Get the answer from user if sent a single answer poll


async def guideRes(dict, list):
    retList = []
    for k,v in dict.items():
        if k in list:
            tmp_list = [k,v]
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

#------------------------------------------- < Events Handling > -------------------------------------------


async def survey_user(user_chat_id):
    await client.send_message(user_chat_id, '''Welcome to survey!\nPlease reply with
                                    'start' to begin the survey!''')
    @client.on(events.NewMessage(pattern='Start'))
    async def newMessageHandler(msg):
        poll1 = Poll(
                id=1224554526,
                question="Is it 2020?",
                answers=[PollAnswer('Yes', b'Yes'), PollAnswer('No', b'No')]
            )
        date = dt(dt.utctimetuple(dt.utcnow()).tm_year,
                    dt.utctimetuple(dt.utcnow()).tm_mon,
                    dt.utctimetuple(dt.utcnow()).tm_mday,
                    dt.utctimetuple(dt.utcnow()).tm_hour,
                    dt.utctimetuple(dt.utcnow()).tm_min+2)
        # print(date)
        # print(dt.utcnow)
        poll2 = Poll(
                id=13567654346,
                close_date=date,
                multiple_choice=True,
                question="Is it 2021?",
                answers=[PollAnswer('Yes', b'Yes'), PollAnswer('No', b'No')]
            )
        pollsList = [poll1, poll2]
        for poll in pollsList:
            sent_msg = await client.send_message(-426645236, file=InputMediaPoll(poll=poll))
            sent_msg = Box(sent_msg.to_dict())
            chat_id = sent_msg.to_id.chat_id
            msg_id = sent_msg.id
            # print(f'{chat_id} : {msg_id}')
            answer = await getPollAnswer(chat_id, msg_id)
            print(f'{answer}')
            # TODO: Store Answer in database

        await client.send_message(user_chat_id, 'Thank you for the survey!')


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


async def deploy(parameter_list):
    pass

@client.on(events.NewMessage(func=filterAdmin))
async def nMessageHandler(msg):
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
                await deploy()

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


#------------------------------------------- < Bot Startup > -------------------------------------------
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
