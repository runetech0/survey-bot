from telethon import TelegramClient, Button, events, errors
import socks
import conf
import shelve
import logging
from box import Box
from pymongo import MongoClient
from colorama import Back, Fore, Style, init


# #######################################################< Global Variables >#######################################################

api_id = conf.API_ID
api_hash = conf.API_HASH
bot_token = conf.BOT_TOKEN

expectingQuestion = False
expectingAnswers = False
openGetSeqName = False
openGetPollResult = False
openGetSurveyUserName = False
openGetDeploySeqName = False
deploySeqName = None
pollResExpected = []
pollChosenMultiAnswers = []
currentPollIndex = 0
pollsList = []
currentSurveyingUser = ''
poll = Box({})
status = Box({
    'inDeploy': False,
    'inPollCreate': False
})

dr = '-------------------------------------------\n'
nl = '\n'


# #######################################################< Initialisations >#######################################################

adminButtons = Box({
    'home': Button.inline("Home", b'home'),
    'deploy': Button.inline("Deploy Sequence", b'deploy'),
    'deploy_start': Button.inline("Deploy Sequence", b'deploy_start'),
    'list_sequences': Button.inline("List Sequences", b'list_sequences'),
    'new_poll': Button.inline("New Poll", b'new_poll'),
    'remove_sequence': Button.inline("Remove Sequence", b'remove_sequence'),
    'exit': Button.inline('Exit', b'exit'),
    'list_users': Button.inline('List Users in Database', b'list_users'),
    'cancel_deploy': Button.inline('Cancel Deploy', b'cancel_deploy'),
    'add_another_poll': Button.inline('Add Another Poll', b'add_another_poll'),
    'finish_seq': Button.inline('Finish', b'finish_seq'),
    'test': Button.inline('Test Button', b'test'),
    'single_answer': Button.inline('Single Answer', b'single_answer'),
    'multi_answer': Button.inline('Multi Answer', b'multi_answer'),
    'discard': Button.inline('Discard Poll', b'poll_discard'),
    'save': Button.inline('Save Poll', b'save_poll'),
    'begin_survey': Button.inline('Start Survey', b'begin_survey'),
    'multi_poll_submit': Button.inline('Submit Poll', b'multi_poll_submit')
})

init(autoreset=True)
TC = Box({
    'SUCCESS': f'{Back.BLACK}{Fore.GREEN}{Style.BRIGHT}',
    'FAIL': f'{Back.BLACK}{Fore.RED}{Style.BRIGHT}',
    'WARNING': f'{Back.BLACK}{Fore.YELLOW}{Style.BRIGHT}'
})


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s :: %(levelname)s :: %(message)s')

client = TelegramClient('new', api_id, api_hash, proxy=(socks.SOCKS5, conf.SOCKS5_SERVER, conf.SOCKS5_PORT))

# #######################################################< Database Setup >#######################################################


dbClient = MongoClient(conf.DB_URL, conf.DB_PORT)
db = dbClient.seqDB         # Database
allSeq = db.allSeq          # Collection for storing all the surveys
allUsers = db.allUsers      # Users collection


# #######################################################< Helper functions >#######################################################

async def resetAllVars():
    global expectingQuestion, expectingAnswers, openGetSeqName, openGetPollResult
    global openGetSurveyUserName, openGetDeploySeqName, deploySeqName
    global pollResExpected, pollChosenMultiAnswers, currentPollIndex
    global pollsList, currentSurveyingUser, poll, status
    expectingQuestion = False
    expectingAnswers = False
    openGetSeqName = False
    openGetPollResult = False
    openGetSurveyUserName = False
    openGetDeploySeqName = False
    deploySeqName = ''
    pollResExpected = []
    pollChosenMultiAnswers = []
    currentPollIndex = 0
    pollsList = []
    currentSurveyingUser = ''
    poll = Box({})
    status = Box({
        'inDeploy': False,
        'inPollCreate': False
    })


async def sendMsg(msg, btns=None, chat=conf.ADMIN_ID):
    sent_msg = await client.send_message(chat, msg, buttons=btns)
    return sent_msg


async def sendMsgPersonal(msg, btns=None, chat=conf.ADMIN_ID):
    try:
        await client.send_message(chat, msg, buttons=btns)
        btns = [[adminButtons.home]]
        sendMsg('Sequence deployed successfully to user!', btns)
    except errors.rpcerrorlist.UserIsBlockedError:
        await client.send_message(conf.ADMIN_ID, 'User has blocked the bot!', buttons=[[adminButtons.home]])


async def getMsg():
    @client.on(events.NewMessage())
    async def getQ(msg):
        return Box(msg.to_dict())


def getContent(msg):
    m = Box(msg.to_dict())
    return m.message.message


# #######################################################< Poll Creation >#######################################################


async def fGetSeqName(msg):
    global openGetSeqName
    return openGetSeqName


@client.on(events.NewMessage(func=fGetSeqName))
async def getSeqName(msg):
    global openGetSeqName, poll
    poll.seqName = getContent(msg)
    openGetSeqName = False
    btns = [
        [
            adminButtons.multi_answer,
            adminButtons.single_answer
        ],
        [
            adminButtons.discard
        ]
    ]
    await msg.respond(f'{dr}Select the type of poll.', buttons=btns)


async def answerFilter(msg):
    return expectingAnswers


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
    await msg.respond(f'{dr}Sequence Name: {poll.seqName}{nl}Question: {poll.question}{nl}\
                        Answers: {nl}{nl.join(poll.answers)}', buttons=[adminButtons.discard, adminButtons.save])


async def questionFilter(msg):
    return expectingQuestion


@client.on(events.NewMessage(func=questionFilter))
async def questionHandler(msg):
    global poll, expectingQuestion, expectingAnswers
    m = Box(msg.to_dict())
    poll.question = m.message.message
    expectingQuestion = False
    expectingAnswers = True
    btns = [
        [
            adminButtons.discard
        ]
    ]
    await msg.respond(f'{dr}Enter the answers separated with commas each answer!', buttons=btns)


@client.on(events.CallbackQuery(data=b'finish_seq'))
async def finish_seq(e):
    await resetAllVars()
    await e.delete()
    await homePage()


@client.on(events.CallbackQuery(data=b'add_another_poll'))
async def add_another_poll(e):
    global openGetSeqName
    if 'seqName' not in poll.keys():
        btns = [
            [adminButtons.discard]
        ]
        await e.edit('Enter the sequence name:', buttons=btns)
        openGetSeqName = True
        return
    seqName = poll.seqName
    poll.clear()
    poll.seqName = seqName
    msg = 'Select the type of new poll.'
    btns = [
        [
            adminButtons.multi_answer,
            adminButtons.single_answer
        ],
        [
            adminButtons.discard
        ]
    ]
    await e.edit(msg, buttons=btns)


@client.on(events.CallbackQuery(data=b'poll_discard'))
async def poll_discard(event):
    btns = [
        [
            adminButtons.add_another_poll,
            adminButtons.finish_seq
        ]
    ]
    await event.edit('Poll discarded!', buttons=btns)


@client.on(events.CallbackQuery(data=b'single_answer'))
async def single_answer(event):
    global expectingQuestion, poll
    if 'props' not in poll.keys():
        poll.props = Box({})
    poll.props.single_answer = True
    poll.props.multi_answer = False
    expectingQuestion = True
    btns = [
        [
            adminButtons.discard
        ]
    ]
    await event.edit(f'{dr}Send the question for the poll.', buttons=btns)


@client.on(events.CallbackQuery(data=b'multi_answer'))
async def multi_answer(event):
    global expectingQuestion, poll
    if 'props' not in poll.keys():
        poll.props = Box({})
    poll.props.multi_answer = True
    poll.props.single_answer = False
    expectingQuestion = True
    btns = [
        [
            adminButtons.discard
        ]
    ]
    await event.edit(f'{dr}Send the question for the poll.', buttons=btns)


@client.on(events.CallbackQuery(data=b'save_poll'))
async def save_poll(e):
    global poll
    foundSeq = allSeq.find_one({'name': poll.seqName})
    allPolls = []
    newPoll = Box({
        'seqName': poll.seqName,
        'question': poll.question,
        'answers': poll.answers,
        'props': poll.props
    })
    if foundSeq:
        foundSeq = Box(foundSeq)
        allPolls = foundSeq.allPolls
        allPolls.append(newPoll)
        allSeq.update_one({'name': newPoll.seqName}, {'$set': {
            'allPolls': allPolls
        }})
        msg = f'Poll added to sequence {foundSeq.name}.'
    else:
        allPolls.append(newPoll)
        print(allPolls)
        allSeq.insert_one({
            'name': poll.seqName,
            'allPolls': allPolls
        })
        msg = f'Poll added to sequence {newPoll.seqName}.'

    btns = [
        [
            adminButtons.add_another_poll,
            adminButtons.finish_seq
        ]
    ]
    await e.edit(msg, buttons=btns)


# #######################################################< Poll Deployment >#######################################################


@client.on(events.CallbackQuery(data=b'multi_poll_submit'))
async def multiPollSubmit(e):
    global openGetPollResult, pollResExpected
    global currentPollIndex, pollsList, currentSurveyingUser
    global pollChosenMultiAnswers
    print(pollChosenMultiAnswers)
    poll = Box(pollsList[currentPollIndex])
    q = poll.question
    await e.edit(f'{q}{nl}{pollChosenMultiAnswers}')
    openGetPollResult = False
    pollResExpected.clear()
    pollChosenMultiAnswers.clear()
    currentPollIndex += 1
    try:
        pollsList[currentPollIndex]
        await survey_user()
    except IndexError:
        await sendMsg('Thank you for survey!', chat=currentSurveyingUser)
        currentPollIndex = 0
        pollsList = []
        currentSurveyingUser = ''
        return


async def filterPoll(e):
    if openGetPollResult:
        if e.data in pollResExpected:
            return True
    else:
        return False


@client.on(events.CallbackQuery(func=filterPoll))
async def getPollResult(e):
    global openGetPollResult, pollResExpected, currentPollIndex
    global pollsList, currentSurveyingUser, pollChosenMultiAnswers
    data = e.data
    chosenAns = data.decode()
    poll = Box(pollsList[currentPollIndex])
    if poll.props.multi_answer:
        pollChosenMultiAnswers.append(chosenAns)
        await e.answer('Choose one or more then submit.')
    else:
        q = poll.question
        await e.edit(f'{q}{nl}{chosenAns}')
        openGetPollResult = False
        pollResExpected = []
        currentPollIndex += 1
        try:
            pollsList[currentPollIndex]
            await survey_user()
        except IndexError:
            await sendMsg('Thank you for survey!', chat=currentSurveyingUser)
            currentPollIndex = 0
            pollsList = []
            currentSurveyingUser = ''
            return


@client.on(events.CallbackQuery(data=b'begin_survey'))
async def startSurvey(e):
    await e.edit('Starting the survey now!')
    await survey_user()


async def survey_user():
    print('starting survey')
    global openGetPollResult, currentPollIndex, pollsList, pollResExpected, currentSurveyingUser
    try:
        poll = pollsList[currentPollIndex]
        openGetPollResult = True
    except IndexError:
        currentPollIndex = 0
        pollsList = []
        return
    poll = Box(poll)
    btns = []
    li = []
    for an in poll.answers:
        an = str(an)
        b_an = an.encode()
        btn = Button.inline(an, b_an)
        pollResExpected.append(b_an)
        li.append(btn)
        btns.append(li.copy())
        li.clear()
    if poll.props.multi_answer:
        subBtn = [adminButtons.multi_poll_submit]
        btns.append(subBtn.copy())
    await sendMsg(poll.question, btns, currentSurveyingUser)


@client.on(events.CallbackQuery(data=b'list_users'))
async def list_users(e):
    listOfUsers = ['@ali', '@raza', '@suqlain', '@sufyan']
    msg = f'Users list in the database.{nl}{nl.join(listOfUsers)}{nl}Please enter username:'
    btns = [
        [adminButtons.cancel_deploy]
    ]
    await e.edit(msg, buttons=btns)


# #######################################################< Admin Tasks Handlers >#######################################################

@client.on(events.CallbackQuery(data=b'cancel_deploy'))
async def cancelDeploy(e):
    await e.delete()
    await resetAllVars()
    await homePage()


async def fGetDeploySeqName(msg):
    return openGetDeploySeqName


@client.on(events.NewMessage(func=fGetDeploySeqName))
async def getDeploySeqName(msg):
    global deploySeqName, openGetDeploySeqName
    deploySeqName = getContent(msg)
    openGetDeploySeqName = False
    msg = f'Deploy sequence {deploySeqName} to username {currentSurveyingUser}?'
    btns = [
        [
            adminButtons.deploy,
            adminButtons.cancel_deploy
        ]
    ]
    await sendMsg(msg, btns)


async def fGetSurveyUserName(e):
    if openGetSurveyUserName:
        return True
    else:
        return False


@client.on(events.NewMessage(func=fGetSurveyUserName))
async def getSurveyUserName(e):
    global currentSurveyingUser, openGetSurveyUserName
    global openGetDeploySeqName
    currentSurveyingUser = getContent(e)
    btns = [
        [
            adminButtons.list_sequences,
            adminButtons.cancel_deploy
        ]
    ]
    status.inDeploy = True
    msg = 'Enter the sequence name to deploy?'
    await sendMsg(msg, btns)
    openGetDeploySeqName = True
    openGetSurveyUserName = False


@client.on(events.CallbackQuery(data=b'deploy_start'))
async def deploy_start(event):
    global openGetSurveyUserName
    btns = [
        [
            adminButtons.list_users,
            adminButtons.cancel_deploy
        ]
    ]
    openGetSurveyUserName = True
    await event.edit('Please enter username of the user you want to deploy the sequence.', buttons=btns)


async def homePage():
    msg = f'{dr}\nAdmin pannel\n{dr}'
    buttons = [
        [
            adminButtons.new_poll,
            adminButtons.list_sequences
        ],
        [
            adminButtons.remove_sequence,
            adminButtons.deploy_start
        ],
        [
            adminButtons.exit
        ]
    ]
    await sendMsg(msg, buttons)


@client.on(events.CallbackQuery(data=b'home'))
async def home(event):
    await resetAllVars()
    await homePage()


@client.on(events.CallbackQuery(data=b'deploy'))
async def deploy(event):
    global pollsList, currentSurveyingUser
    foundSeq = allSeq.find_one({'name': deploySeqName})
    if foundSeq:
        foundSeq = Box(foundSeq)
        pollsList = foundSeq.allPolls
        btn = [
            [adminButtons.begin_survey]
        ]
        status.inDeploy = False
        try:
            await client.send_message(currentSurveyingUser, 'Welcome to this.\nThis is blah blah survey!', buttons=btn)
            await event.answer('Sequence deployed successfully to user!', alert=True)
            # await home(event)
            await homePage()
        except errors.rpcerrorlist.UserIsBlockedError:
            await event.answer('Blocked!!!\nUser has blocked the bot!', alert=True)


@client.on(events.CallbackQuery(data=b'list_sequences'))
async def list_sequences(e):
    found = allSeq.find({})
    seqNames = []
    for seq in found:
        seq = Box(seq)
        seqNames.append(seq.name)
    if status.inDeploy:
        btns = [
            [
                adminButtons.cancel_deploy
            ]
        ]
        status.inDeploy = False
        msg = f'Available sequences{nl}{nl.join(seqNames)}{nl}{nl}Enter sequence name:'
    elif status.inPollCreate:
        btns = [
            [
                adminButtons.discard
            ]
        ]
        status.inPollCreate = False
        msg = f'Available sequences{nl}{nl.join(seqNames)}{nl}{nl}Enter Sequence name:'
    else:
        btns = [
            [adminButtons.home]
        ]
        msg = f'Available sequences{nl}{nl.join(seqNames)}{nl}{nl}'

    await e.edit(msg, buttons=btns)


@client.on(events.CallbackQuery(data=b'new_poll'))
async def new_poll(event):
    global openGetSeqName
    btns = [
        [
            adminButtons.discard,
            adminButtons.list_sequences
        ]
    ]
    status.inPollCreate = True
    await event.edit(f'{dr}Enter the sequence name.', buttons=btns)
    openGetSeqName = True


@client.on(events.CallbackQuery(data=b'remove_sequence'))
async def remove_sequence(event):
    await event.edit('Thanks for using! Bye!')


@client.on(events.CallbackQuery(data=b'exit'))
async def exit_handler(event):
    await resetAllVars()
    await event.delete()


@client.on(events.CallbackQuery(data=b'test'))
async def test(event):
    clear = client.build_reply_markup(Button.switch_inline('Hello', 'qrrr'))
    await sendMsg('Clear', clear)

# #######################################################< Message Events >#######################################################


async def filterAdmin(e):
    e = Box(e.to_dict())
    if e.message.from_id == conf.ADMIN_ID:
        return True
    else:
        return False


@client.on(events.NewMessage(pattern='/start'))
async def adminHandler(msg):
    en = await client.get_input_entity(msg.from_id)
    print(en)
    await resetAllVars()
    await homePage()
    await msg.delete()


try:
    client.start(bot_token=bot_token)
    print(f"{TC.SUCCESS}\n-------------------------\nBot is up!\n-------------------------\n")
    print("To run in the background type 'nohup python /path/to/app &' command. Thanks!\n")
    client.run_until_disconnected()
except KeyboardInterrupt:
    print("\nQuiting bot!")
except errors.rpcerrorlist.ApiIdInvalidError:
    print("Invalid API_ID/API_HASH")
