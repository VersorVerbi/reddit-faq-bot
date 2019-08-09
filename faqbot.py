from typing import Dict, List, Any, Union
import praw
import mysql.connector
import re
import sys
import time
import traceback
import nltk
from config import constants as config
from config import faqhelper


# region globals
VALID_ADMINS: List[str] = [config.ADMIN_USER]
reply_message: str = ''
replacement: str = ''
# endregion


# region basic functions
def switch(dictionary: Dict, default, value):
    return dictionary.get(value, default)


def remove_nonalpha(matchobj):
    global replacement
    return replacement


def command_ok():
    return 0


def post_is_processed(post_id: str):
    global db
    cursor = db.cursor()
    query = "SELECT isKwProcessed FROM posts WHERE id=%(pid)s"
    cursor.execute(query, {'pid': post_id})
    row = cursor.fetchone()
    if row is not None:
        is_processed = row[0] > 0
    else:
        is_processed = False
    cursor.close()
    return is_processed


def past_is_prologue():
    global db
    cursor = db.cursor()
    query = "UPDATE posts SET isKwProcessed = 1 WHERE isKwProcessed = 0;"
    cursor.execute(query)
    db.commit()
    cursor.close()
    return


def execute_sql_file(filename):
    global db
    fd = open(filename, 'r')
    file = fd.read()
    fd.close()
    commands = file.split(';')  # FIXME: how will this work with the function/procedures files?
    for cmd in commands:
        cursor = db.cursor()
        cursor.execute(cmd)
        db.commit()
        cursor.close()
    return


def update_setting(setting_name, setting_value):
    global db
    cursor = db.cursor()
    sql = "REPLACE INTO settings (`descriptor`, `value`) VALUES (%(desc)s, %(val)s)"
    cursor.execute(sql, {'val': setting_value, 'desc': setting_name})
    db.commit()
    cursor.close()
    return 0


def reset_all_settings():
    update_setting('numlinks', 5)
    update_setting('numkeys', 5)
    return


def post_from_our_subreddit(post):
    return post.subreddit.display_name.lower() == config.SUBREDDIT.lower()


def get_mysql_connection():
    return mysql.connector.connect(user=config.SQL_USER, password=config.SQL_PW, host=config.HOSTNAME,
                                   database=config.SQL_DATABASE)


def get_reddit():
    return praw.Reddit(user_agent=config.USER_AGENT, client_id=config.CLIENT_ID, client_secret=config.CLIENT_SECRET,
                       username=config.REDDIT_USER, password=config.REDDIT_PW)


def get_numbers(string: str):
    return [int(i) for i in string.split() if i.isdigit()]
# endregion


# region command functions
def add_favorite(new_favorite):
    global db, r
    if new_favorite is None:
        raise faqhelper.MissingParameter
    elif r.submission(new_favorite) is None:
        raise faqhelper.MismatchedParameter
    elif not post_from_our_subreddit(r.submission(new_favorite)):
        raise faqhelper.WrongSubreddit
    sql = 'SELECT SUM(posts.modFavorite) FROM posts WHERE posts.id = %(pid)s'
    cursor = db.cursor()
    cursor.execute(sql, {'pid': new_favorite})
    if cursor.fetchone()[0] > 0:
        raise faqhelper.IncorrectState
    cursor.fetchall()
    sql = 'UPDATE posts SET posts.modFavorite = 1 WHERE posts.id = %(pid)s'
    cursor.execute(sql, {'pid': new_favorite})
    db.commit()
    cursor.close()
    return 0


def remove_favorite(fav_to_remove):
    global db, r
    if fav_to_remove is None:
        raise faqhelper.MissingParameter
    elif r.submission(fav_to_remove) is None:
        raise faqhelper.MismatchedParameter
    elif not post_from_our_subreddit(r.submission(fav_to_remove)):
        raise faqhelper.WrongSubreddit
    sql = 'SELECT SUM(posts.modFavorite) FROM posts WHERE posts.id = %(pid)s'
    cursor = db.cursor()
    cursor.execute(sql, {'pid': fav_to_remove})
    if cursor.fetchone()[0] <= 0:
        raise faqhelper.IncorrectState
    cursor.fetchall()
    sql = 'UPDATE posts SET posts.modFavorite = 0 WHERE posts.id = %(pid)s'
    cursor.execute(sql, {'pid': fav_to_remove})
    db.commit()
    cursor.close()
    return 0


def update_numkeys(numkeys):
    if numkeys is None:
        raise faqhelper.MissingParameter
    elif not isinstance(numkeys, int):
        raise faqhelper.MismatchedParameter
    elif numkeys <= 0:
        raise faqhelper.BadParameter
    return update_setting('numkeys', numkeys)
    

def update_numlinks(numlinks):
    if numlinks is None:
        raise faqhelper.MissingParameter
    elif not isinstance(numlinks, int):
        raise faqhelper.MismatchedParameter
    elif numlinks <= 0:
        raise faqhelper.BadParameter
    return update_setting('numlinks', numlinks)


def process_query(message):
    # TODO: do this
    return 0


def ignore_token(token):
    global db
    if token is None:
        raise faqhelper.MissingParameter
    sql = 'UPDATE tokens SET tokens.document_count = tokens.document_count + 1000 WHERE tokens.token LIKE %(tok)s'
    cursor = db.cursor()
    cursor.execute(sql, {'tok': token})
    db.commit()
    cursor.close()
    return 0


def process_test(pid_to_test):
    # TODO: do this
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
    for cmd, desc in faqhelper.ADMIN_DESCRIPTIONS.items():
        output += '* `' + cmd + '`: ' + desc + '\n'
    output += '\nPlease send a message to /u/' + config.ADMIN_USER + ' with questions, comments, or bug reports.'
    return output


def user_signature(is_public=False):
    output = '\n\n------\n\n'
    if is_public:
        output += '^^Reply ^^with ^^`delete` ^^to ^^delete ^^\(mods ^^and ^^OP ^^only.)\n\n'
    output += '^^Tag ^^me ^^with ^^a ^^query ^^to ^^get ^^my ^^response, ^^or ^^just ^^tag ^^me ^^to ^^get ^^my ' \
              '^^response ^^to ^^the ^^parent ^^comment/post.\n\n'
    output += '^^PM ^^me ^^a ^^query ^^for ^^a ^^private ^^response.\n\n'
    output += '^^PM ^^/u/' + config.ADMIN_USER + ' ^^with ^^questions, ^^comments, ^^or ^^bug ^^reports.'
    return output


def invalid_command(cmd):
    output = 'You have attempted to send me a command, but I didn\'t recognize it. The command you entered was `' + cmd
    output += '`.\n\nIf you\'re trying to query me like a "regular" user, remember that you must (1) start a **new** '
    output += 'private message conversation, (2) make the subject `QUERY` (case-insensitive, but just that alone), and '
    output += '(3) make the body of the message your query.'
    return output


def invalid_params(cmd):
    output = 'You entered `' + ' '.join(cmd) + '`.\n\n'
    output += 'You have entered invalid parameters for your command (alpha instead of numeric, for example). ' \
              'Don\'t do that.'
    return output


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


def sql_failure():
    return 'Something went wrong with the SQL query. The command has not been processed. Please try again.'


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


def test_results(pid_to_test):
    message = ''
    return message
# endregion


# region analysis functions
def related_posts(post_id):
    global db
    cursor = db.cursor()
    query = "SELECT relatedPosts(%(pid)s);"
    cursor.execute(query, {'pid': post_id})
    row = cursor.fetchone()
    cursor.close()
    return row[0].split(',')


def post_keywords(post_id):
    global db
    cursor = db.cursor()
    query = "SELECT keywordList(%(pid)s);"
    cursor.execute(query, {'pid': post_id})
    row = cursor.fetchone()
    cursor.close()
    return row[0]


def process_post(post):
    global db, r
    post_id = post.id
    print("Beginning processing for post %s" % (post_id))

    # don't reply to mod posts or specified flaired posts or non-self-text posts
    if post.link_flair_text is not None:
        if post.link_flair_text.lower() in config.FLAIRS_TO_IGNORE:
            raise faqhelper.IgnoredFlair
    if post.stickied or not post.is_self:
        raise faqhelper.IncorrectPostType
    
    # if not even on our subreddit, ignore
    if not post_from_our_subreddit(post):
        raise faqhelper.WrongSubreddit

    # if already processed, quit
    if post_is_processed(post_id):
        raise faqhelper.AlreadyProcessed
        
    print("Processing necessary for post %s" % (post_id))

    # we don't have to count this again if we already have
    cursor = db.cursor()
    cursor.execute("SELECT id FROM posts WHERE `id`=%(pid)s",{'pid': post_id})
    row = cursor.fetchone()
    if row is None:
        token_counting(post)
    cursor.close()
    keyword_list: str = post_keywords(post_id)
    list_of_related_posts: List[str] = related_posts(post_id)
    output_data: Dict[str, Union[Union[List[Any], int, praw.models.Comment], Any]] = {
        'title': [],
        'url': [],
        'top_cmt_votes': 0,
        'top_cmt': None
    }
    for pid in list_of_related_posts:
        thread: praw.models.Submission = r.submission(pid)
        thread.comment_sort = 'confidence'
        if len(thread.comments) > 0:
            top_comment: praw.models.Comment = thread.comments[0]
            # TODO: skip deleted comments and get next top comment
        else:
            top_comment = None
        output_data['title'].append(thread.title)
        output_data['url'].append('https://np.reddit.com' + thread.permalink)
        if top_comment is not None:
            if top_comment.score > output_data['top_cmt_votes']:
                output_data['top_cmt_votes'] = top_comment.score
                output_data['top_cmt'] = top_comment
    reply_body = post_analysis_message(keyword_list, output_data)
    # TESTING ONLY
    reply_body = "Test reply for [" + post.title + "](" + post.permalink + ")\n\n------\n\n" + reply_body
    r.submission('co5du1').reply(reply_body); # test post for examining replies in public
    # TODO: do other stuff, like add a comment with links and a quote
    cursor = db.cursor()
    sql = 'UPDATE posts SET isKwProcessed = 1 WHERE id = %(pid)s;'
    cursor.execute(sql, {'pid': post_id})
    db.commit()
    cursor.close()
    return


def post_analysis_message(keyword_list, output_data):
    global replacement
    reply_body = 'Our analysis of this post indicates that the keywords are: ' + keyword_list + '\n\n'
    reply_body += 'Here are some other posts that are related:\n\n'
    for title, url in zip(output_data['title'], output_data['url']):
        reply_body += '* [' + title + '](' + url + ')\n'
    reply_body += '\nThe top-voted comment from those threads is this one:\n\n'
    comment_body = output_data['top_cmt'].body
    replacement = '\n\n> '
    replace_pattern = '\n\n'
    comment_body = re.sub(replace_pattern, remove_nonalpha, comment_body)
    reply_signature = user_signature(True)
    if len(reply_body) + len(comment_body) + len(reply_signature) > 9999:
        # don't have multi-line links, but don't have too many characters, either
        comment_body = comment_body.split('\n')[0]
        reply_body += '* [' + comment_body[:50] + '...](https://np.reddit.com' + output_data['top_cmt'].permalink + ')'
    else:
        # the first line didn't have any line breaks, so we need to add another quote marker there
        reply_body += '>' + comment_body
    reply_body += reply_signature
    return reply_body


def process_comment(cmt):
    global subr
    global r
    if 'u/' + config.REDDIT_USER.lower() not in cmt.body.lower():  # no tag, so a private message
        if cmt.parent().author == r.redditor(config.REDDIT_USER):
            for mod in subr.moderator():
                VALID_ADMINS.append(str(mod))
            if cmt.author == cmt.parent().parent().author or cmt.author in VALID_ADMINS:
                if cmt.body.lower() == 'delete':
                    cmt.parent().delete()
    else:  # we have been summoned
        pass  # TODO: handle a comment
    return


def handle_query(short_str: str):
    # TODO: actually implement this
    return short_str


def retrieve_token_counts(submissions):
    global db
    for post in submissions:
        # "gilded" returns both comments and submissions, so exclude the comments
        if not isinstance(post, praw.models.Submission) or not post.is_self:
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
        cursor.close()
        # otherwise, count the tokens
        token_counting(post)
        # TODO: mark initial-load posts as processed to prevent later processing
    return


def token_counting(post):
    global db, replacement, english_vocab
    # get post text data
    post_id = post.id
    post_title = post.title
    post_text = post.selftext
    # this regex finds "http" followed by an unknown number of letters and not-letters until, looking ahead, we see a
    # closing parenthesis, a horizontal space, or a vertical space
    # we want to replace links with nothing so that they don't mess with our word analysis
    replacement = ''
    replace_pattern = r'http(\w|\W)+?(?=\)| |\t|\v)'
    post_text = re.sub(replace_pattern, remove_nonalpha, post_text.lower())
    post_title = re.sub(replace_pattern, remove_nonalpha, post_title.lower())
    # this regex finds any character that is NOT lowercase a-z or diacritically marked variants of the same or an
    # apostrophe or a space
    # we want to replace these characters with spaces so that words separated by only a slash, dash, line break, etc.,
    # aren't smushed together
    replacement = ' '
    replace_pattern = r'[^0-9a-zà-öø-ÿ\'’ ]'  # get rid of non-alpha, non-space characters
    post_text = re.sub(replace_pattern, remove_nonalpha, post_text)
    post_title = re.sub(replace_pattern, remove_nonalpha, post_title)
    # this regex is the same as the last one minus the apostrophe
    # we want to replace apostrophes with nothing to minimize the effect of the ridiculously inordinate amount of
    # apostrophe-based typos in the world
    replacement = ''
    replace_pattern = r'[^0-9a-zà-öø-ÿ ]'
    post_text = re.sub(replace_pattern, remove_nonalpha, post_text)
    post_title = re.sub(replace_pattern, remove_nonalpha, post_title)
    # now split the strings by spaces and combine them into a single array
    text_array = post_title.split() + post_text.split()
    text_set = set(text_array)  # gets only one instance of each unique token
    # add post_id to posts SQL table (have to do this first so foreign keys in other SQL tables don't complain)
    cursor = db.cursor()
    add_to_posts = "INSERT IGNORE INTO posts (id) VALUES (%(pid)s)"
    cursor.execute(add_to_posts, {'pid': post_id})
    db.commit()
    cursor.close()
    # loop through tokens and add them to the database
    print("Adding tokens for post %s: \"%s\"" % (post_id, post_title))
    for token in text_set:
        # print(' ' + token)
        # new_token_id = 0
        count = text_array.count(token)
        # add counts to SQL database (use Jaccard scoring to determine "source" keyword, or add new ?)
        cursor = db.cursor()
        get_token = "SELECT tokens.id FROM tokens WHERE tokens.token LIKE %(wrd)s"
        cursor.execute(get_token, {'wrd': token})
        row = cursor.fetchone()
        # check for match
        if cursor.rowcount <= 0:
            make_new_word = token in english_vocab
            if not make_new_word:
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
                print(matched_token_set)
                if False:  # matched_proximity > required_match:
                    new_token_id = matched_id
                    # update tokens table
                    add_to_tokens = "UPDATE tokens SET document_count = document_count + 1 WHERE id=%(tid)s"
                    cursor.execute(add_to_tokens, {'tid': matched_id})
                    db.commit()
            else:
                # add to tokens table
                add_to_tokens = "INSERT IGNORE INTO tokens (token, document_count) VALUES (%(str)s, 1)"
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
        add_to_keywords = "INSERT IGNORE INTO keywords (tokenId, postId, num_in_post) " \
                          "VALUES (%(tid)s, %(pid)s, %(count)s)"
        cursor.execute(add_to_keywords, {'tid': new_token_id, 'pid': post_id, 'count': count})
        db.commit()
        cursor.close()


# endregion


# region retrieval functions
def initial_data_load(subreddit):
    # Reddit limits the results of each of these calls to 1000 posts; there will undoubtedly be some overlap between
    # these, but by using all of them, we're likely to get a larger number of total posts for analysis (although,
    # unfortunately, only a very small number of the total submissions on the subreddit)
    global db, fromCrash
    submissions = []
    if not fromCrash:
        print("Doing initial load")
        # top
        submissions.append(subreddit.top(limit=1000))
        print("Got from top")
        # hot
        submissions.append(subreddit.hot(limit=1000))
        print("Got from hot")
        # gilded
        submissions.append(subreddit.gilded(limit=1000))
        print("Got from gilded")
        # controversial
        submissions.append(subreddit.controversial(limit=1000))
        print("Got from controversial")
        # search1
        params = {'limit': 1000}
        submissions.append(subreddit.search("title:? self:1", 'relevance', **params))
        print("Got from ? relevance")
        submissions.append(subreddit.search("title:? self:1", 'hot', **params))
        print("Got from ? hot")
        submissions.append(subreddit.search("title:? self:1", 'top', **params))
        print("Got from ? top")
        submissions.append(subreddit.search("title:? self:1", 'new', **params))
        print("Got from ? new")
        # search2
        submissions.append(subreddit.search("title:question self:1", 'relevance', **params))
        print("Got from q relevance")
        submissions.append(subreddit.search("title:question self:1", 'hot', **params))
        print("Got from q hot")
        submissions.append(subreddit.search("title:question self:1", 'top', **params))
        print("Got from q top")
        submissions.append(subreddit.search("title:question self:1", 'new', **params))
        print("Got from q new")
    # new
    submissions.append(subreddit.new(limit=1000))
    print("Got from new")
    for post_list in submissions:
        retrieve_token_counts(post_list)
    if not fromCrash:
        past_is_prologue()
    return


def get_stream(**kwargs) -> praw.models.util.stream_generator:
    global r
    target_sub = r.subreddit(config.SUBREDDIT)
    results = []
    results.extend(target_sub.new())
    results.extend(r.inbox.messages())
    results.extend(r.inbox.comment_replies())
    results.extend(r.inbox.mentions())
    results.sort(key=lambda post: post.created_utc, reverse=True)
    return praw.models.util.stream_generator(lambda **kwargs: results, **kwargs)
# endregion


def handle_command_message(msg):
    global r, db, subr, reply_message
    for mod in subr.moderator():
        VALID_ADMINS.append(str(mod))
    if msg.author not in VALID_ADMINS:
        if msg.author == config.REDDIT_USER:
            # ignore myself
            msg.delete()
            return
        if msg.subject.split()[0].upper() == 'HELP':
            reply_message = help_text()
        else:
            if msg.subject is not None and msg.body is not None:
                reply_message = handle_query(msg.subject + ' ' + msg.body) + user_signature(False)
            else:
                return
    else:
        cmd = msg.subject.split()
        if cmd[0].upper() == 'QUERY':
            reply_message = handle_query(msg.body)
        elif cmd[0].upper() not in faqhelper.ADMIN_COMMANDS:
            cmd = msg.body.split()
        if cmd[0].upper() not in faqhelper.ADMIN_COMMANDS:
            reply_message = invalid_command(cmd[0])
        else:
            try:
                code_to_exec = switch(faqhelper.ADMIN_COMMANDS, '-1', cmd[0].upper())
                exec(code_to_exec, globals(), locals())
            except mysql.connector.Error:
                reply_message = sql_failure()
                pass
            except (faqhelper.MissingParameter, faqhelper.MismatchedParameter):
                reply_message = invalid_params(cmd)
                pass
            except (faqhelper.BadParameter, faqhelper.IncorrectState, faqhelper.WrongSubreddit):
                reply_message = improper_params(cmd[0])
                pass
            code_to_exec = 'global reply_message; reply_message = ' + switch(faqhelper.ADMIN_REPLIES, '-1', cmd[0].upper())
            exec(code_to_exec, globals(), locals())
        reply_message += admin_signature()
    msg.reply(reply_message)
    return


# main -----------------------------------
r = get_reddit()
db = get_mysql_connection()

if len(sys.argv) > 1:
    fromCrash = (sys.argv[1] != 'initial')
    fullReset = (sys.argv[1] == 'reset')
else:
    fromCrash = True
    fullReset = False

exists_cursor = db.cursor()
exists_cursor.execute('SHOW TABLES LIKE %(tbl)s', {'tbl': 'keywords'})
exists = exists_cursor.fetchone()
if not exists:
    fullReset = False
    fromCrash = False
    execute_sql_file('tables.sql')
    execute_sql_file('procedures.sql')
    execute_sql_file('functions.sql')
    reset_all_settings()
exists_cursor.close()
    
if fullReset:
    fromCrash = False
    reset_cursor = db.cursor()
    sql = "TRUNCATE keywords; TRUNCATE tokens;"
    reset_cursor.execute(sql, multi=True)
    db.commit()
    sql = "SELECT id FROM posts;"
    reset_cursor.execute(sql)
    for row in reset_cursor:
        token_counting(r.submission(row[0]))
    reset_cursor.close()
    reset_all_settings()

nltk.download('words')
english_vocab = set(w.lower() for w in nltk.corpus.words.words())

main_loop()

def main_loop():
    global r, db
    try:
        subr = r.subreddit(config.SUBREDDIT)
        initial_data_load(subr)
        while True:
            callers = get_stream()
            for caller in callers:
                if isinstance(caller, praw.models.Message):
                    handle_command_message(caller)
                elif isinstance(caller, praw.models.Submission):
                    try:
                        process_post(caller)
                    except faqhelper.IgnoredFlair:
                        print("Ignored as free friday post")
                        pass
                    except faqhelper.IncorrectPostType:
                        print("Ignored as sticky or link")
                        pass
                    except faqhelper.WrongSubreddit:
                        print("Ignored as on wrong subreddit")
                        pass
                    except faqhelper.AlreadyProcessed:
                        print("Ignored as already processed")
                        pass
                else:
                    process_comment(caller)
                if len(VALID_ADMINS) > 1:
                    VALID_ADMINS.clear()
                    VALID_ADMINS.append(config.ADMIN_USER)
                if isinstance(caller, praw.models.Message):
                    caller.delete()
    except mysql.connector.OperationalError:
        db.close()
        db = get_mysql_connection()
        pass
    except praw.exceptions.APIException as apie:
        minutes_str = "".join(get_numbers(apie.message))
        if len(minutes_str) > 0:
            minutes = int(minutes_str)
            time.sleep(minutes * 60)
        else:
            r = None
            r = get_reddit()
        pass
    except praw.Exceptions.ClientException:
        r = None
        r = get_reddit()
        pass
    except Exception as e:
        db.close()
        err_data = sys.exc_info()
        err_msg = str(err_data[1]) + '\n\n'  # error message
        traces = traceback.format_list(traceback.extract_tb(err_data[2]))
        for trace in traces:
            err_msg += '    ' + trace + '\n'  # stack trace
        r.redditor(config.ADMIN_USER).message('FAQ CRASH', err_msg)
        # DON'T PASS HERE -- we want uncaught exceptions to crash the bot and tell us
    main_loop()
    return
