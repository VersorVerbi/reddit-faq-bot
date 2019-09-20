from typing import Dict, List, Any, Union
import praw
import prawcore
import mysql.connector
import re
import sys
import traceback
from time import sleep
from spell import spell
from config import constants as config
from config import faqhelper


# region globals
VALID_ADMINS: List[str] = [config.ADMIN_USER]
reply_message: str = ''
replacement: str = ''
subr: praw.models.Subreddit = None
MIN_LINKS: int = 3
DISABLE_COMMENT_QUOTING: bool = True
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
    cursor = execute_sql("SELECT isKwProcessed FROM posts WHERE id=%(pid)s", {'pid': post_id})
    process_row = cursor.fetchone()
    if process_row is not None:
        is_processed = process_row[0] > 0
    else:
        is_processed = False
    cursor.close()
    return is_processed


def is_link_only(body):
    link_pattern = r'^http(\w|\W)+?$'
    return re.search(link_pattern, body)


def past_is_prologue():
    global db
    cursor = execute_sql("UPDATE posts SET isKwProcessed = 1 WHERE isKwProcessed = 0;")
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


def execute_sql(sql: str, params: object = None, multi: bool = False):
    global db
    retry = True
    cursor = None
    while retry:
        try:
            cursor = db.cursor()
            cursor.execute(sql, params=params, multi=multi)
            retry = False
        except mysql.connector.errors.OperationalError:
            if cursor is not None:
                cursor.close()
            if db is not None:
                db.close()
            db = get_mysql_connection()
            retry = True
        if not retry:
            break
    return cursor


def update_setting(setting_name: str, setting_value):
    global db
    cursor = execute_sql("REPLACE INTO settings (`descriptor`, `value`) VALUES (%(desc)s, %(val)s)",
                         {'val': setting_value, 'desc': setting_name})
    db.commit()
    cursor.close()
    return 0


def reset_all_settings():
    update_setting('numlinks', 5)
    update_setting('numkeys', 5)
    update_setting('minlinks', 3)
    return


def get_setting(setting_name: str, default_val):
    global db
    cursor = execute_sql("SELECT `value` FROM settings WHERE `descriptor` = %(desc)s;", {'desc': setting_name})
    setting_value = cursor.fetchone()
    if setting_value is None:
        setting_value = default_val
    else:
        setting_value = setting_value[0]
    return setting_value


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


def post_reply(reply_to, reply_with):
    reply_to.reply(reply_with)
    return


def mark_as_processed(post_id: str = None):
    if post_id is None:
        past_is_prologue()
    else:
        cursor = execute_sql('UPDATE posts SET isKwProcessed = 1 WHERE id = %(pid)s;', {'pid': post_id})
        db.commit()
        cursor.close()
    return
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
    cursor = execute_sql('SELECT SUM(posts.modFavorite) FROM posts WHERE posts.id = %(pid)s', {'pid': new_favorite})
    if cursor.fetchone()[0] > 0:
        raise faqhelper.IncorrectState
    cursor.close()
    cursor = execute_sql('UPDATE posts SET posts.modFavorite = 1 WHERE posts.id = %(pid)s', {'pid': new_favorite})
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
    cursor = execute_sql('SELECT SUM(posts.modFavorite) FROM posts WHERE posts.id = %(pid)s', {'pid': fav_to_remove})
    if cursor.fetchone()[0] <= 0:
        raise faqhelper.IncorrectState
    cursor.close()
    cursor = execute_sql('UPDATE posts SET posts.modFavorite = 0 WHERE posts.id = %(pid)s', {'pid': fav_to_remove})
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


def ignore_token(token):
    global db
    if token is None:
        raise faqhelper.MissingParameter
    cursor = execute_sql('UPDATE tokens '
                         'SET tokens.document_count = tokens.document_count + 1000 '
                         'WHERE tokens.token LIKE %(tok)s', {'tok': token})
    db.commit()
    cursor.close()
    return 0
# endregion


# region sig functions
def admin_signature():
    output = '\n\nThank you for using the ' + config.BOT_NAME + '!\n\n------\n\n'
    output += 'Remember that you can reply to this message,'
    output += ' or send a new private message to this bot, in order to make adjustments to how'
    output += ' it operates. To get more information about the available commands, send a '
    output += 'message with the title (or body) `help` (case insensitive).'
    output += '\nPlease send a message to /u/' + config.ADMIN_USER + ' with questions, comments, or bug reports.'
    return output


def user_signature(is_public=False):
    output = '\n\n------\n\n^^I ^^am ^^a ^^robot ^^and ^^this ^^action ^^was ^^performed ^^automatically.\n\n'
    if is_public:
        output += '^^If ^^what ^^I ^^have ^^done ^^is ^^wrong ^^or ^^inappropriate, ^^downvote ^^me ^^below ^^zero ' \
                  '^^and ^^I\'ll ^^delete ^^this ^^comment.'
    output += '^^Tag ^^me ^^with ^^a ^^query ^^to ^^get ^^my ^^response, ^^or ^^just ^^tag ^^me ^^to ^^get ^^my ' \
              '^^response ^^to ^^the ^^parent ^^comment/post.\n\n'
    output += '^^PM ^^me ^^a ^^query ^^for ^^a ^^private ^^response.\n\n'
    output += '^^PM ^^[' + config.ADMIN_USER + '](https://www.reddit.com/u/' + config.ADMIN_USER + ') ^^with ' \
              '^^questions, ^^comments, ^^or ^^bug ^^reports.'
    return output
# endregion


# region error reply functions
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
# endregion


# region command reply functions
def quick_analytics():
    global db
    cursor = execute_sql("SELECT COUNT(*) FROM posts; "
                         "SELECT COUNT(*) FROM tokens; "
                         "SELECT `value` FROM settings WHERE `descriptor`='numkeys'; "
                         "SELECT `value` FROM settings WHERE `descriptor`='numlinks'; "
                         "SELECT COUNT(*) FROM posts WHERE modFavorite=1;", multi=True)
    results = cursor.fetchall()
    num_posts = results[0][0]
    num_tokens = results[1][0]
    num_keys = results[2][0]
    num_links = results[3][0]
    num_favs = results[4][0]
    message = 'Here are some details on the current state of the database:\n\n'\
              'Number of posts analyzed: ' + num_posts + '\n\n'\
              'Number of unique words discovered: ' + num_tokens + '\n\n'\
              'Maximum number of keywords selected for each post: ' + num_keys + '\n\n'\
              'Maximum number of related links selected for each post: ' + num_links + '\n\n'\
              'Number of moderator favorites: ' + num_favs
    return message


def help_text():
    message = 'Send a single command per message. (Every message will be interpeted'\
              ' based on the first command parsed only.)\n\nEach of these commands is case-'\
              'insensitive:\n\n'
    for cmd, desc in faqhelper.ADMIN_DESCRIPTIONS.items():
        message += '* `' + cmd + '`: ' + desc + '\n'
    return message


def favorite_added(new_favorite):
    message = 'You have added the new favorite post ' + new_favorite + '. It will now be highlighted'
    message += ' separately from other posts when it is included in a response.'
    return message


def favorite_removed(fav_to_remove):
    message = 'You have removed the favorite post ' + fav_to_remove + '. It will no longer be '
    message += 'highlighted separately from other posts when it is included in a response.'
    return message


def new_numkeys(numkeys):
    message = 'The number of keywords identified by the bot is now ' + str(numkeys) + '.'
    return message


def new_numlinks(numlinks):
    message = 'The number of links returned by the bot is now ' + str(numlinks) + '.'
    return message


def query_results(msg):
    global r
    subject, text_array, text_set = prepare_post_text(msg)
    # handle cases where someone specifically requested a "query"
    if subject.lower() == "query":
        text_array.remove('query')
        if 'query' not in text_array:
            text_set.remove('query')
    try:
        post_list, impt_words = handle_query(text_array, text_set, True)
        my_reply = 'The keywords of your query seem to be: %s\n\n'\
                   'Here are the related posts I found:' % impt_words
        for pid in ','.split(post_list):
            post = r.submission(pid)
            my_reply += '* [' + post.title + '](' + post.permalink + ')\n'
    except faqhelper.NoRelations:
        my_reply = 'Unfortunately, I was not able to identify any posts that match your query.'
    return my_reply


def token_ignored(token):
    message = 'The word \'' + token + '\' is now considered less important by the bot. This action cannot be reversed.'
    return message


def test_results(pid_to_test):
    global r
    post = r.submission(pid_to_test)
    try:
        message = process_post(post, False, True)
    except faqhelper.IgnoredFlair:
        message = "Post %s has a flair that is set to be ignored." % pid_to_test
    except faqhelper.IgnoredTitle:
        message = "Post %s has text in the title that is set to be ignored." % pid_to_test
    except faqhelper.IncorrectPostType:
        message = "Post %s is a stickied post or a link post, so it is set to be ignored." % pid_to_test
    except faqhelper.WrongSubreddit:
        message = "Post %s is not on the r/%s subreddit." % (pid_to_test, config.SUBREDDIT)
    except faqhelper.NoRelations as nr:
        message = "Post %s has these keywords: %s\n\nBut I could find no related posts." % \
                  (pid_to_test, nr.keyword_list)
    return "Test results for post (%s)[%s] (PID: %s)\n\n------\n\n%s" % \
           (post.title, post.permalink, pid_to_test, message)
# endregion


# region analysis functions
def related_posts(post_id):
    global db, MIN_LINKS, subr
    cursor = db.cursor()
    args = (post_id, None)
    ret = cursor.callproc('relatedPosts', args)
    related = ret[1]
    if related is not None:
        related = related.split(',')
    cursor.close()
    if related is None or len(related) < MIN_LINKS:
        keywords = post_keywords(post_id)
        related = search_instead(keywords, related)
    return related


def post_keywords(post_id):
    global db
    cursor = execute_sql('SELECT keywordList(%(pid)s);', {'pid': post_id})
    keywords = cursor.fetchone()
    cursor.close()
    return keywords[0]


def process_post(post: praw.models.Submission, reply_to_thread: bool = True, reprocess: bool = False):
    global db, r
    post_id = post.id
    print("Beginning processing for post %s" % post_id)

    # don't reply to mod posts or specified flaired posts or non-self-text posts
    if post.link_flair_text is not None:
        if post.link_flair_text.lower() in config.FLAIRS_TO_IGNORE:
            raise faqhelper.IgnoredFlair
    for ignorable in config.TITLE_TEXT_TO_IGNORE:
        if ignorable in post.title.lower():
            raise faqhelper.IgnoredTitle
    if post.stickied or not post.is_self:
        raise faqhelper.IncorrectPostType
    
    # if not even on our subreddit, ignore
    if not post_from_our_subreddit(post):
        raise faqhelper.WrongSubreddit

    # if already processed, quit
    if not reprocess:
        if post_is_processed(post_id):
            raise faqhelper.AlreadyProcessed
        
    print("Processing necessary for post %s" % post_id)

    post_title, text_array, text_set = prepare_post_text(post)

    if len(text_set) > 25:
        # we don't have to count this again if we already have
        cursor = execute_sql("SELECT id FROM posts WHERE `id`=%(pid)s", {'pid': post_id})
        exists_row = cursor.fetchone()
        if exists_row is None:
            token_counting(post, post_title, text_array, text_set)
        cursor.close()
        keyword_list: str = post_keywords(post_id)
        try:
            list_of_related_posts: List[str] = related_posts(post_id)
        except faqhelper.NoRelations as nr:
            # literally nothing is related, so there's nothing we can do here
            if not reply_to_thread:
                raise nr
            print("Ignored with no relations")
            mark_as_processed(post_id)
            return ''
    elif len(text_set) > 0:
        try:
            list_of_related_posts, keyword_list = handle_query(text_array, text_set)
        except faqhelper.NoRelations as nr:
            # nothing is related
            if not reply_to_thread:
                raise nr
            print("Ignored with no relations")
            mark_as_processed(post_id)
            return ''
    else:
        # there's literally nothing in this post
        mark_as_processed(post_id)
        return ''
    output_data: Dict[str, Union[Union[List[Any], int, praw.models.Comment], Any]] = {
        'title': [],
        'url': [],
        'top_cmt_votes': 0,
        'top_cmt': None
    }

    for pid in list_of_related_posts:
        thread: praw.models.Submission = r.submission(pid)
        try:
            exists_check = thread.comments
        except prawcore.exceptions.ResponseException:
            continue
        thread.comment_sort = 'confidence'
        if len(thread.comments) > 0:
            i = 0
            top_comment: praw.models.Comment = thread.comments[i]
            while top_comment.author is None or top_comment.banned_by is not None:
                i += 1
                top_comment = thread.comments[i]
        else:
            top_comment = None
        output_data['title'].append(thread.title)
        output_data['url'].append('https://np.reddit.com' + thread.permalink)
        if top_comment is not None:
            if top_comment.score > output_data['top_cmt_votes']:
                output_data['top_cmt_votes'] = top_comment.score
                output_data['top_cmt'] = top_comment
    reply_body = post_analysis_message(keyword_list, output_data)
    if reply_to_thread:
        retry: bool = True
        while retry:
            try:
                post_reply(post, reply_body)
                retry = False
            except praw.exceptions.APIException as e:
                if e.field.lower() == 'ratelimit':
                    minutes = get_numbers(e.message)[0]
                    sleep((minutes + 1) * 60)
                    retry = True
                else:
                    raise e
            if not retry:
                break
    mark_as_processed(post_id)
    return reply_body


def post_analysis_message(keyword_list, output_data):
    global replacement, DISABLE_COMMENT_QUOTING
    reply_body = 'Our analysis of this post indicates that the keywords are: ' + keyword_list + '\n\n'
    reply_body += 'Here are some other posts that are related:\n\n'
    comment_body = ''
    for title, url in zip(output_data['title'], output_data['url']):
        reply_body += '* [' + title + '](' + url + ')\n'
    reply_signature = user_signature(True)
    if not DISABLE_COMMENT_QUOTING:
        reply_body += '\nThe top-voted comment from those threads is this one:\n\n'
        if output_data['top_cmt'] is not None:
            comment_body = output_data['top_cmt'].body
            replacement = '\n\n> '
            replace_pattern = '\n\n'
            comment_body = re.sub(replace_pattern, remove_nonalpha, comment_body)
        if len(reply_body) + len(comment_body) + len(reply_signature) > 9999 and len(comment_body) > 0:
            # don't have multi-line links, but don't have too many characters, either
            comment_body = comment_body.split('\n')[0]
            reply_body += '* [' + comment_body[:50] + '...](https://np.reddit.com' + \
                          output_data['top_cmt'].permalink + ')'
        else:
            # the first line didn't have any line breaks, so we need to add another quote marker there
            reply_body += '>' + comment_body
    reply_body += reply_signature
    return reply_body


def process_comment(cmt):
    global subr, r, db
    if cmt is None:
        return
    if post_is_processed(cmt.id):
        return
    if post_from_our_subreddit(cmt) or 'u/' + config.REDDIT_USER.lower() not in cmt.body.lower():
        # ignore comments calling us in other subreddits and replying to our comments
        mark_as_processed(cmt.id)
        return
    # we have been summoned
    cursor = execute_sql('INSERT IGNORE INTO posts (id) VALUES (%(pid)s)', {'pid': cmt.id})
    db.commit()
    cursor.close()
    comment_reply, list_of_posts, list_of_keywords = '', '', ''
    ptitle, text_array, text_set = prepare_post_text(cmt)
    print(text_array)
    text_array.remove('u')
    text_array.remove(config.REDDIT_USER.lower())
    if 'u' not in text_array:
        text_set.remove('u')
    if config.REDDIT_USER.lower() not in text_array:
        text_set.remove(config.REDDIT_USER.lower())
    print(text_array)
    try:
        if len(text_set) > 0:
            list_of_posts, list_of_keywords = handle_query(text_array, text_set)
        else:
            target = cmt.parent()
            if isinstance(target, praw.models.Submission):
                try:
                    comment_reply = process_post(target, False, True)
                    list_of_posts = ''
                    list_of_keywords = ''
                except faqhelper.IncorrectPostType:
                    comment_reply = 'Unfortunately, I am not equipped to handle link and sticky posts.'
                    comment_reply += user_signature(True)
                except (faqhelper.IgnoredFlair, faqhelper.IgnoredTitle):
                    comment_reply = 'Unfortunately, I explicitly ignore posts with this flair or title. '\
                                    'If you really want my input on some specific facet of this post, '\
                                    'please tag me again (in a new comment) with a short selection of '\
                                    'keywords or a question.'
                    comment_reply += user_signature(True)
            else:
                ptitle, text_array, text_set = prepare_post_text(target)
                list_of_posts, list_of_keywords = handle_query(text_array, text_set)
    except faqhelper.NoRelations as nr:
        comment_reply = 'I identified the following keywords: %s\n\n' % nr.keyword_list
        comment_reply += 'Unfortunately, I was unable to find any relevant posts in this case.'
        comment_reply += user_signature(True)
    comment_reply = 'Thanks for using the Catholic FAQ Bot!\n\n' + comment_reply
    if len(list_of_keywords) > 0 and len(list_of_posts) > 0:
        comment_reply += 'Our analysis indicates that the keywords are: ' + list_of_keywords
        comment_reply += '\n\nHere are some posts that are related:\n\n'
        array_of_posts = list_of_posts.split(',')
        for pid in array_of_posts:
            post = r.submission(pid)
            plink = post.permalink
            ptitle = post.title
            comment_reply += '*[' + ptitle + '](' + plink + ')\n\n'
        comment_reply += user_signature(True)
    retry = True
    while retry:
        try:
            cmt.reply(comment_reply)
            retry = False
        except praw.exceptions.APIException as e:
            if e.field.lower() == 'ratelimit':
                minutes = get_numbers(e.message)[0]
                sleep((minutes + 1) * 60)
                retry = True
            else:
                raise e
    mark_as_processed(cmt.id)
    return


def handle_query(tarray: list, tset: set, ignore_min_links: bool = False):
    global db, MIN_LINKS, subr
    if tarray is None or tset is None:
        # this hasn't been handled correctly, so raise an error to notify the administrator
        raise SyntaxError
    # now handle query array
    cursor = db.cursor()
    tarray = ['\'{0}\''.format(element) for element in tarray]
    args = (','.join(tarray), None, None)
    ret = cursor.callproc('queryRelated', args)
    related = ret[1]
    if related is not None:
        related = related.split(',')
    important = ret[2]
    cursor.close()
    if related is None or (not ignore_min_links and len(related) < MIN_LINKS):
        related = search_instead(important, related, ignore_min_links)
    return related, important


def retrieve_token_counts(submissions):
    global db, fromCrash
    for post in submissions:
        # "gilded" returns both comments and submissions, so exclude the comments
        if not isinstance(post, praw.models.Submission) or not post.is_self or is_link_only(post.selftext):
            continue
        if post.link_flair_text is not None:
            if post.link_flair_text.lower() in config.FLAIRS_TO_IGNORE:
                continue
        skip = False
        for ignorable in config.TITLE_TEXT_TO_IGNORE:
            if ignorable in post.title.lower():
                skip = True
                break
        if skip:
            continue
        post_id = post.id
        # if in posts SQL table already, do nothing
        cursor = execute_sql('SELECT id FROM posts WHERE id = %(pid)s', {'pid': post_id})
        cursor.fetchall()
        if cursor.rowcount > 0:
            cursor.close()
            if fromCrash:
                # if things are only sorted by new, then getting to something we've already done means nothing
                # else will be new to us, either
                break
            else:
                continue
        cursor.close()
        # otherwise, count the tokens
        post_title, text_array, text_set = prepare_post_text(post)
        token_counting(post, post_title, text_array, text_set)
    return


def token_counting(post, post_title, text_array, text_set):
    global db
    # get post text data
    post_id = post.id
    # add post_id to posts SQL table (have to do this first so foreign keys in other SQL tables don't complain)
    cursor = execute_sql('INSERT IGNORE INTO posts (id) VALUES (%(pid)s)', {'pid': post_id})
    db.commit()
    cursor.close()
    # loop through tokens and add them to the database
    print("Adding tokens for post %s: \"%s\"" % (post_id, post_title))
    for token in text_set:
        # print(' ' + token)
        new_token_id = 0
        count = text_array.count(token)
        # add counts to SQL database (use spelling correction to determine "source" keyword, or add new)
        cursor = execute_sql('SELECT tokens.id FROM tokens WHERE tokens.token LIKE %(wrd)s', {'wrd': token})
        word_row = cursor.fetchone()
        # check for match
        make_new_word = (cursor.rowcount <= 0)
        if make_new_word:  # no token found
            new_word = spell.correction(token)  # is the token an existing word
            if cursor is not None:
                cursor.close()
            cursor = execute_sql('SELECT tokens.id FROM tokens WHERE tokens.token LIKE %(wrd)s', {'wrd': new_word})
            word_row = cursor.fetchone()
            make_new_word = (cursor.rowcount <= 0)
            if make_new_word:
                # the token was not in our database and either was in English or did not match anything closely
                # add to tokens table
                if cursor is not None:
                    cursor.close()
                cursor = execute_sql('INSERT IGNORE INTO tokens (token, document_count) VALUES (%(str)s, 1)',
                                     {'str': token})
                db.commit()
                new_token_id = cursor.lastrowid
                cursor.close()
        if not make_new_word:  # either the token was found initially or with a spelling correction
            new_token_id = word_row[0]
            # update tokens table
            if cursor is not None:
                cursor.close()
            cursor = execute_sql('UPDATE tokens SET document_count = document_count + 1 WHERE id=%(tid)s',
                                 {'tid': new_token_id})
            db.commit()
            cursor.close()
            
        # add to keywords table
        cursor = execute_sql('INSERT IGNORE INTO keywords (tokenId, postId, num_in_post) '
                             'VALUES (%(tid)s, %(pid)s, %(count)s)',
                             {'tid': new_token_id, 'pid': post_id, 'count': count})
        db.commit()
        cursor.close()
    return


def prepare_post_text(post):
    global replacement
    if isinstance(post, praw.models.Message):
        post_title = post.subject
        post_text = post.body
    elif isinstance(post, praw.models.Comment):
        post_title = ''
        post_text = post.body
    else:
        post_title = post.title
        post_text = post.selftext
    # this regex finds "http" followed by an unknown number of letters and not-letters until, looking ahead, we see a
    # closing parenthesis, a horizontal space, or a vertical space
    # we want to replace links with nothing so that they don't mess with our word analysis
    replacement = ''
    replace_pattern = r'http(\w|\W)+?(?=\)| |\t|\v|$)'
    post_text = re.sub(replace_pattern, remove_nonalpha, post_text.lower())
    post_title = re.sub(replace_pattern, remove_nonalpha, post_title.lower())
    # this regex finds cardinal numbers (i.e., not "1st" or "3rd", but "37" or "6")
    # we want to remove these because they're not really words, and they're not relevant regardless
    replace_pattern = r'\b\d+\b'
    post_text = re.sub(replace_pattern, remove_nonalpha, post_text)
    post_title = re.sub(replace_pattern, remove_nonalpha, post_title)
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
    return post_title, text_array, text_set


def search_instead(keywords, current_post_list, ignore_minimum: bool = False):
    global subr, MIN_LINKS
    if current_post_list is None:
        current_post_list = []
    for result in subr.search(keywords, limit=get_setting('numlinks')):
        current_post_list.append(result.id)
    if not ignore_minimum and current_post_list < MIN_LINKS:
        raise faqhelper.NoRelations(keys=keywords)
    return current_post_list
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
            return
        if msg.subject.split()[0].upper() == 'HELP':
            reply_message = help_text()
        else:
            if msg.subject is not None and msg.body is not None:
                reply_message = query_results(msg) + user_signature(False)
            else:
                return
    else:
        cmd = msg.subject.split()
        if cmd[0].upper() == 'QUERY':
            reply_message = query_results(msg)
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
            except (faqhelper.MissingParameter, faqhelper.MismatchedParameter, IndexError):
                reply_message = invalid_params(cmd)
            except (faqhelper.BadParameter, faqhelper.IncorrectState, faqhelper.WrongSubreddit):
                reply_message = improper_params(cmd[0])
            try:
                code_to_exec = 'global reply_message; reply_message = '\
                               + switch(faqhelper.ADMIN_REPLIES, '-1', cmd[0].upper())
                exec(code_to_exec, globals(), locals())
            except IndexError:
                reply_message = invalid_params(cmd)
        reply_message += admin_signature()
    msg.reply(reply_message)
    return


def main_loop():
    global r, db, subr, MIN_LINKS
    try:
        subr = r.subreddit(config.SUBREDDIT)
        initial_data_load(subr)
        MIN_LINKS = get_setting('minlinks', 3)
        print("Initial load done")
        while True:
            callers = get_stream(pause_after=0)
            for caller in callers:
                if caller is None:
                    break
                if isinstance(caller, praw.models.Message):
                    handle_command_message(caller)
                elif isinstance(caller, praw.models.Submission):
                    try:
                        process_post(caller)
                    except faqhelper.IgnoredFlair:
                        print("Ignored by flair")
                    except faqhelper.IgnoredTitle:
                        print("Ignored by title")
                    except faqhelper.IncorrectPostType:
                        print("Ignored as sticky or link")
                    except faqhelper.WrongSubreddit:
                        print("Ignored as on wrong subreddit")
                    except faqhelper.AlreadyProcessed:
                        print("Ignored as already processed")
                else:
                    process_comment(caller)
                if len(VALID_ADMINS) > 1:
                    VALID_ADMINS.clear()
                    VALID_ADMINS.append(config.ADMIN_USER)
                if isinstance(caller, praw.models.Message):
                    caller.delete()
            # review old comments looking for downvotes
            my_old_comments = r.redditor(config.REDDIT_USER).comments.new(limit=1000)
            for old_comment in my_old_comments:
                if old_comment.score < 0:
                    old_comment.delete()
    except mysql.connector.OperationalError:
        err_data = sys.exc_info()
        print(err_data)
        db.close()
        sleep(2)
        db = get_mysql_connection()
    except praw.exceptions.PRAWException:
        err_data = sys.exc_info()
        print(err_data)
        r = None
        r = get_reddit()
    except Exception as e:
        db.close()
        err_data = sys.exc_info()
        err_msg = str(err_data[1]) + '\n\n'  # error message
        traces = traceback.format_list(traceback.extract_tb(err_data[2]))
        for trace in traces:
            err_msg += '    ' + trace + '\n'  # stack trace
        r.redditor(config.ADMIN_USER).message('FAQ CRASH', err_msg)
        raise e
    main_loop()
    return


# main -----------------------------------
r = get_reddit()

# local debug test
strm = get_stream()
# end local debug test


db = get_mysql_connection()

if len(sys.argv) > 1:
    fromCrash = (sys.argv[1] != 'initial')
    fullReset = (sys.argv[1] == 'reset')
else:
    fromCrash = True
    fullReset = False

exists_cursor = execute_sql('SHOW TABLES LIKE %(tbl)s', {'tbl': 'keywords'})
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
    reset_cursor = execute_sql("TRUNCATE keywords; TRUNCATE tokens;", multi=True)
    db.commit()
    reset_cursor.close()
    reset_cursor = execute_sql("SELECT id FROM posts;")
    for row in reset_cursor:
        curpost = r.submission(row[0])
        title, reset_text_array, reset_text_set = prepare_post_text(curpost)
        token_counting(curpost, title, reset_text_array, reset_text_set)
    reset_cursor.close()
    reset_all_settings()

main_loop()
