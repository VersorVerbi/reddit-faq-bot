import praw
import mysql.connector
import re
import sys
import traceback
from config import constants as config


# region enums
ADMIN_COMMANDS = {
    'DATA': 'command_ok()',
    'HELP': 'command_ok()',
    'MODFAVE': 'add_favorite(cmd[1])',
    'MODUNFAVE': 'remove_favorite(cmd[1])',
    'NUMKEYS': 'update_numkeys(cmd[1])',
    'NUMLINKS': 'update_numlinks(cmd[1])',
    'QUERY': 'process_query(msg)',
    'REDUCEUNIQUENESS': 'ignore_token(cmd[1])'
}

ADMIN_REPLIES = {
    'DATA': 'quick_analytics()',
    'HELP': 'help_text()',
    'MODFAVE': 'favorite_added(cmd[1])',
    'MODUNFAVE': 'favorite_removed(cmd[1])',
    'NUMKEYS': 'new_numkeys(cmd[1])',
    'NUMLINKS': 'new_numlinks(cmd[1])',
    'QUERY': 'query_results()',
    'REDUCEUNIQUENESS': 'token_ignored(cmd[1])'
}

ADMIN_DESCRIPTIONS = {
    'DATA': 'Return a high-level summary of the database and settings as they are now.',
    'HELP': 'Return a list of functions, options, and behavior for admins.',
    'MODFAVE id': 'Where `id` is the string immediately after `/comments/` in the URL of a thread, e.g., `cdgbpv`. Use '
                  'this command to mark a particular thread as a moderator favorite. It will be set apart and '
                  'highlighted whenever it scores highly in keyword matching. The quoted top comment will come from '
                  'the most closely matched mod favorite thread instead of being pulled from all possible matches.',
    'MODUNFAVE id': 'Where `id` is the string immediately after `/comments/` in the URL of a thread, e.g., `cdgbpv`. '
                    'Use this command to **un**mark a particular thread as a moderator favorite. It will **no longer** '
                    'be set apart and highlighted, but will appear normally whenever it scores highly in keyword '
                    'matching. The quoted top comment will come from the most closely matched mod favorite thread '
                    'instead of being pulled from all possible matches.',
    'NUMKEYS #': 'Where `#` is a positive integer less than or equal to ten (<=10). Indicates the number of keywords to'
                 ' use for thread matching. The default is 5.',
    'NUMLINKS #': 'Where `#` is a positive integer less than or equal to ten (<=10). Indicates the maximum number of '
                  'matching links to provide when responding to new posts.',
    'QUERY': 'Where `QUERY` is the subject and your query is the body of the message; works exactly like non-'
             'administrative users querying the bot.',
    'REDUCEUNIQUENESS word': 'Where `word` is the word/token you want to reduce the influence of. This is appropriate '
                             'only for obvious misspellings or otherwise rare (but irrelevant) words that, due to '
                             'their uniqueness, score as keywords more often than they should. **THIS ACTION CANNOT '
                             'BE REVERSED. PROCEED WITH CAUTION.**'
}
# endregion


# region globals
VALID_ADMINS = [config.ADMIN_USER]
reply_message = ''
cmd_result = 0
# endregion


# region basic functions
def switch(dictionary, default, value):
    return dictionary.get(value, default)


def remove_nonalpha(matchobj):
    return ''


def command_ok():
    return 0


def post_is_processed(post_id):
    global db
    cursor = db.cursor()
    query = "SELECT isKwProcessed FROM faq_posts WHERE id=%s"
    cursor.execute(query, post_id)
    is_processed = cursor.fetchone().isKwProcessed > 0
    cursor.close()
    return is_processed
# endregion


# region command functions
def add_favorite(new_favorite):
    global db
    if new_favorite is None:
        return -1

    sql = 'UPDATE posts SET posts.modFavorite = 1 WHERE posts.id = %(pid)s'
    cursor = db.cursor()
    cursor.execute(sql, {'pid': new_favorite})
    return 0


def remove_favorite(fav_to_remove):
    return 0


def update_numkeys(numkeys):
    return 0


def update_numlinks(numlinks):
    return 0


def process_query(message):
    return 0


def ignore_token(token):
    return 0
# endregion


# region reply functions
def admin_signature():
    output = '\n\nThank you for using the ' + config.BOT_NAME + '!\n\n------\n\n'
    output += 'Remember that you can reply to this message,'
    output += ' or send a new private message to this bot, in order to make adjustments to how'
    output += ' it operates. Send a single command per message. (Every message will be interpeted'
    output += ' based on the first command parsed only.)\n\nEach of these commands is case-'
    output += 'insensitive:\n\n'
    for cmd, desc in ADMIN_DESCRIPTIONS.items():
        output += '* `' + cmd + '`: ' + desc + '\n'
    output += '\nPlease send a message to /u/' + config.ADMIN_USER + ' with questions, comments, or bug reports.'
    return output


def user_signature(is_public=False):
    output = '\n\n------\n\n'
    output += '^^I ^^am ^^only ^^trying ^^to ^^help'
    if is_public:
        output += '; ^^if ^^I ^^have ^^failed, ^^the ^^original ^^recipient ^^of ^^this ^^response ^^or ^^a '
        output += '^^subreddit ^^moderator ^^should ^^reply ^^to ^^this ^^comment ^^with ^^precisely ^^`delete`. '
    else:
        output += '. '
    output += '^^If ^^you ^^want ^^my ^^input ^^in ^^a ^^thread, '
    output += '^^tag ^^/u/' + config.REDDIT_USER + ' ^^with ^^a ^^query ^^or ^^question. ^^Alternatively, '
    output += '^^include ^^**no** ^^other ^^text ^^and ^^tag ^^me ^^to ^^get ^^my ^^response ^^based ^^on '
    output += '^^the ^^parent ^^comment ^^or ^^post. ^^If ^^you ^^have ^^a ^^private ^^question, ^^always '
    output += '^^feel ^^free ^^to ^^send ^^a ^^message ^^to ^^me ^^with ^^your ^^short ^^query.\n\n^^Please '
    output += '^^send ^^a ^^message ^^to ^^/u/' + config.ADMIN_USER + ' ^^with ^^questions, ^^comments, '
    output += '^^or ^^bug ^^reports.'
    return output


def invalid_command(cmd):
    output = 'You have attempted to send me a command, but I didn\'t recognize it. The command you entered was `' + cmd
    output += '`.\n\nIf you\'re trying to query me like a "regular" user, remember that you must (1) start a **new** '
    output += 'private message conversation, (2) make the subject `QUERY` (case-insensitive, but just that alone), and '
    output += '(3) make the body of the message your query.'
    return output


def invalid_params():
    return 'You have entered invalid parameters for your command (alpha instead of numeric, for example). ' \
           'Don\'t do that.'


def improper_params(cmd):
    if 'MOD' in cmd.upper():
        output = 'You have attempted to favorite or unfavorite a thread, but one of the following '
        output += 'was true:\n\n*the indicated id did not exist,\n*the thread was not on r/'
        output += config.SUBREDDIT + ', or\n*the specified thread was already on (or off) the '
        output += 'favorites list. Please try again with an appropriate thread.'
    else:
        output = 'You have attempted to change a number setting, but have supplied a negative '
        output += 'number or one greater than 10 (>10). Please try again with an appropriate '
        output += 'number.'
    return output


def quick_analytics():
    global db
    message = ''
    return message


def help_text():
    message = ''
    return message


def favorite_added(new_favorite):
    message = ''
    return message


def favorite_removed(fav_to_remove):
    message = ''
    return message


def new_numkeys(numkeys):
    message = ''
    return message


def new_numlinks(numlinks):
    message = ''
    return message


def query_results():
    message = ''
    return message


def token_ignored(token):
    message = ''
    return message
# endregion


# region analysis functions
def process_post(post):
    global db
    post_id = post.id

    # if already processed, quit
    if post_is_processed(post_id):
        return

    # TODO: decide whether we want to deal with link posts at all
    post_text = post.title + chr(7) + post.selftext
    post_keywords = find_keywords(post_text)
    relevent_posts = relevant_posts(post_keywords)
    # TODO: do other stuff, like add a comment with links and a quote
    # TODO: mark the post as processed
    return


def process_comment(cmt):
    global subr
    global r
    if 'u/' + config.REDDIT_USER.lower() not in cmt.body.lower():
        if cmt.parent().author == r.redditor(config.REDDIT_USER):
            for mod in subr.moderator():
                VALID_ADMINS.append(str(mod))
            if cmt.author == cmt.parent().parent().author or cmt.author in VALID_ADMINS:
                if cmt.body.lower() == 'delete':
                    cmt.parent().delete()
    else:  # we have been summoned
        pass  # TODO: handle a comment
    return


def retrieve_token_counts(submissions):
    global db
    for post in submissions:
        if not post.is_self:
            continue
        post_id = post.id
        # if in posts SQL table already, do nothing
        cursor = db.cursor()
        query = "SELECT id FROM posts WHERE id = %(pid)s"
        cursor.execute(query, {'pid': post_id})
        cursor.fetchall()
        if cursor.rowcount > 0:
            cursor.close()
            continue
        # print(post_id)
        cursor.close()
        # get post text data
        post_title = post.title
        post_text = post.selftext
        # split strings, reduce to alpha-numeric only, get counts
        replace_pattern = r'[^a-zà-öø-ÿ ]'  # get rid of non-alpha, non-space characters
        post_text = re.sub(replace_pattern, remove_nonalpha, post_text.lower())
        post_title = re.sub(replace_pattern, remove_nonalpha, post_title.lower())
        # note to self: potential bug with special-char-concatenated words (don't, super-heated, etc.)
        text_array = post_title.split() + post_text.split()
        text_set = set(text_array)
        # add post_id to posts SQL table (have to do this first so foreign keys in other SQL tables don't complain)
        cursor = db.cursor()
        add_to_posts = "INSERT INTO posts (id) VALUES (%(pid)s)"
        cursor.execute(add_to_posts, {'pid': post_id})
        db.commit()
        cursor.close()
        # loop through tokens and add them to the database
        for token in text_set:
            # print(' ' + token)
            new_token_id = 0
            count = text_array.count(token)
            # add counts to SQL database (use Jaccard scoring to determine "source" keyword, or add new ?)
            cursor = db.cursor()
            get_token = "SELECT tokens.id FROM tokens WHERE tokens.token LIKE %(wrd)s"
            cursor.execute(get_token, {'wrd': token})
            row = cursor.fetchone()
            # check for match
            # print ('  ',cursor.rowcount)
            if cursor.rowcount <= 0:
                # if no match, get closestMatch()
                matched_token_set = cursor.callproc('closestMatch', (token, (0, 'CHAR'), 0, 0))
                matched_token = matched_token_set[1]
                matched_id = matched_token_set[2]
                matched_proximity = matched_token_set[3]
                # if match is insufficient, add it to the token table
                token_length = len(token)
                # if length <= 3, only 100% is sufficient (won't this still cause bugs -- e.g., fig vs gif?)
                # as length increases, required match decreases (+1/-5?)
                required_match = max(1 - (0.05 * (token_length - 3)), 0.6)
                # print(matched_token_set)
                if False:  # matched_proximity > required_match:
                    new_token_id = matched_id
                    # update tokens table
                    add_to_tokens = "UPDATE tokens SET document_count = document_count + 1 WHERE id=%(tid)s"
                    cursor.execute(add_to_tokens, {'tid': matched_id})
                    db.commit()
                else:
                    # print('new token!')
                    # add to tokens table
                    add_to_tokens = "INSERT INTO tokens (token, document_count) VALUES (%(str)s, 1)"
                    cursor.execute(add_to_tokens, {'str': token})
                    db.commit()
                    new_token_id = cursor.lastrowid
            else:
                new_token_id = row[0]
                # update tokens table
                add_to_tokens = "UPDATE tokens SET document_count = document_count + 1 WHERE id=%(tid)s"
                cursor.execute(add_to_tokens, {'tid': new_token_id})
                db.commit()
            # add to keywords table
            add_to_keywords = "INSERT INTO keywords (tokenId, postId, num_in_post) VALUES (%(tid)s, %(pid)s, %(count)s)"
            cursor.execute(add_to_keywords, {'tid': new_token_id, 'pid': post_id, 'count': count})
            db.commit()
            cursor.close()
    return


# endregion

def relevant_posts(keywords):  # TODO
    # with all keywords do SQL:
    # SELECT postId,COUNT(*) as sameKeywords
    # FROM `tfIdfTable`
    # WHERE tokenId in (keywords)
    # AND tfIdfScore > KEYWORD_THRESHOLD
    # GROUP BY postId
    # ORDER BY sameKeywords DESC
    # return list where sameKeywords > 25%? of number of keywords
    return ''


def find_keywords(post_text):  # TODO
    # split by chr(7); if nothing after, use query calculation; otherwise, just remove chr(7) and
    # pretend all are together
    # split text, reduce to lower-case alpha-numeric only
    # count instances (get tf)
    # loop through unique
    # get idf
    # calculate_tfidf
    # sort by score
    # top scorers = keywords (top 5 or all >keyword threshold, whichever is more, along with scores)
    return ''


# region retrieval functions
def initial_data_load(subreddit):
    # Reddit limits the results of each of these calls to 1000 posts; there will undoubtedly be some overlap between
    # these, but by using all of them, we're likely to get a larger number of total posts for analysis (although,
    # unfortunately, only a very small number of the total submissions on the subreddit)
    global db
    global fromCrash
    submissions = []
    if not fromCrash:
        # top
        submissions.append(subreddit.top())
        # hot
        submissions.append(subreddit.hot())
        # gilded
        submissions.append(subreddit.gilded())
        # controversial
        submissions.append(subreddit.controversial())
        # search1
        submissions.append(subreddit.search("title:? self:1", 'relevance'))
        submissions.append(subreddit.search("title:? self:1", 'hot'))
        submissions.append(subreddit.search("title:? self:1", 'top'))
        submissions.append(subreddit.search("title:? self:1", 'new'))
        # search2
        submissions.append(subreddit.search("title:question self:1", 'relevance'))
        submissions.append(subreddit.search("title:question self:1", 'hot'))
        submissions.append(subreddit.search("title:question self:1", 'top'))
        submissions.append(subreddit.search("title:question self:1", 'new'))
    # new
    submissions.append(subreddit.new())
    for post_list in submissions:
        retrieve_token_counts(post_list)
    return


def get_stream(**kwargs) -> praw.models.util.stream_generator:
    global r
    target_sub = r.subreddit(config.SUBREDDIT)
    results = []
    results.extend(target_sub.new(**kwargs))
    results.extend(r.inbox.messages())
    results.extend(r.inbox.comment_replies())
    results.extend(r.inbox.mentions())
    results.sort(key=lambda post: post.created_utc, reverse=True)
    return praw.models.util.stream_generator(lambda **kwargs: results, **kwargs)


# endregion

def handle_command_message(msg):
    global r
    global db
    global subr
    global cmd_result
    global reply_message
    for mod in subr.moderator():
        VALID_ADMINS.append(str(mod))
    if msg.author not in VALID_ADMINS:
        if msg.subject.split()[0].upper() == 'HELP':
            reply_message = help_text()
        else:
            reply_message = handle_query(msg.subject + ' ' + msg.body) + user_signature(False)
    else:
        cmd = msg.subject.split()
        if cmd[0].upper() == 'QUERY':
            reply_message = handle_query(msg.body) + admin_signature()
        elif cmd[0].upper() not in ADMIN_COMMANDS:
            cmd = msg.body.split()
        if cmd[0].upper() not in ADMIN_COMMANDS:
            reply_message = invalid_command(cmd[0]) + admin_signature()
        else:
            code_to_exec = 'global cmd_result; cmd_result = ' + switch(ADMIN_COMMANDS, '-1', cmd[0])
            exec(code_to_exec, globals(), locals())
            if cmd_result < 0:
                reply_message = invalid_params() + admin_signature()
            elif cmd_result > 0:
                reply_message = improper_params(cmd[0]) + admin_signature()
            else:
                code_to_exec = 'global reply_message; reply_message = ' + switch(ADMIN_REPLIES, '-1', cmd[0])
                exec(code_to_exec, globals(), locals())
                reply_message += admin_signature()
    msg.reply(reply_message)
    msg.delete()
    return


# main -----------------------------------
r = praw.Reddit(user_agent=config.USER_AGENT, client_id=config.CLIENT_ID, client_secret=config.CLIENT_SECRET,
                username=config.REDDIT_USER, password=config.REDDIT_PW)
db = mysql.connector.connect(user=config.SQL_USER, password=config.SQL_PW, host='localhost',
                             database=config.SQL_DATABASE)
if len(sys.argv) > 1:
    fromCrash = (sys.argv[1] != 'initial')
else:
    fromCrash = True

try:
    subr = r.subreddit(config.SUBREDDIT)
    initial_data_load(subr)
    raise Exception('quit before "constant" loop')
    while True:
        callers = get_stream(**kwargs)
        for caller in callers:
            if isinstance(caller, praw.models.Message):
                handle_command_message(caller)
            elif isinstance(caller, praw.models.Submission):
                process_post(caller)
            else:
                process_comment(caller)
            if len(VALID_ADMINS) > 1:
                VALID_ADMINS.clear()
                VALID_ADMINS.append(config.ADMIN_USER)
except Exception as e:
    db.close()
    err_data = sys.enc_info()
    err_msg = str(err_data[1]) + '\n\n'  # error message
    traces = traceback.format_list(traceback.extract_tb(err_data[2]))
    for trace in traces:
        err_msg += '    ' + trace + '\n'  # stack trace
    r.redditor(config.ADMIN_USER).message('FAQ CRASH', err_msg)
