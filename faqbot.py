import praw
import mysql.connector
import re
import sys
from config import constants

def remove_nonalpha(matchobj):
    return ''

def post_is_processed(postID, db):
    cursor = db.cursor()
    query = "SELECT isKwProcessed FROM faq_posts WHERE id=%s"
    cursor.execute(query, postID)
    return cursor.fetchone().isKwProcessed > 0

def process_post(post, db, initialLoad):
    postID = post.id
    
    # if already processed, quit
    if post_is_processed(postID, db):
        return
    
    if not post.is_self and not initialLoad:
        postLink = post.url
        # TODO: get posts with the same links
        searchString = "url:" + postLink

        # TODO: if none exist, do the normal thing with just the title as a query-weighted string
    postText = post.title + chr(7) + post.selftext
    postKeywords = find_keywords(postText)
    if initialLoad:
        # TODO: just put the scores in the SQL database
        # TODO: mark the post as processed
        return
    releventPosts = relevant_posts(postKeywords)
    # TODO: do other stuff, like add a comment with links and a quote
    # TODO: mark the post as processed
    return

def relevant_posts(keywords): # TODO
    # with all keywords do SQL:
    #SELECT postId,COUNT(*) as sameKeywords
    #FROM `tfIdfTable`
    #WHERE tokenId in (keywords)
    #AND tfIdfScore > KEYWORD_THRESHOLD
    #GROUP BY postId
    #ORDER BY sameKeywords DESC
    # return list where sameKeywords > 25%? of number of keywords
    return

def find_keywords(postText): # TODO
    # split by chr(7); if nothing after, use query calculation; otherwise, just remove chr(7) and pretend all are together
    # split text, reduce to lower-case alpha-numeric only
    # count instances (get tf)
    # loop through unique
    #get idf
    #calculate_tfidf
    #sort by score
    # top scorers = keywords (top 5 or all >keyword threshold, whichever is more, along with scores)
    return
    
def retrieve_token_counts(submissions, db):
    i = 0
    for post in submissions:
        postID = post.id
        # if in posts SQL table already, do nothing
        cursor = db.cursor()
        query = "SELECT id FROM posts WHERE id = %(pid)s"
        cursor.execute(query, { 'pid': postID })
        cursor.fetchall()
        if cursor.rowcount > 0:
            cursor.close()
            continue
        #print(postID)
        cursor.close()
        i = i + 1
        # get post text data
        postTitle = post.title
        postText = post.selftext
        # split strings, reduce to alpha-numeric only, get counts
        replacePattern = r'[^a-zà-öø-ÿ ]' # get rid of non-alpha, non-space characters
        postText = re.sub(replacePattern,remove_nonalpha,postText.lower())
        postTitle = re.sub(replacePattern,remove_nonalpha,postTitle.lower())
        # note to self: potential bug with special-char-concatenated words (don't, super-heated, etc.)
        textArray = postTitle.split() + postText.split()
        textSet = set(textArray)
        # add postID to posts SQL table (have to do this first so foreign keys in other SQL tables don't complain)
        cursor = db.cursor()
        add_to_posts = "INSERT INTO posts (id) VALUES (%(pid)s)"
        cursor.execute(add_to_posts, { 'pid': postID })
        db.commit()
        cursor.close()
        # loop through tokens and add them to the database
        for token in textSet:
            #print(' ' + token)
            new_token_id = 0
            count = textArray.count(token)
            # add counts to SQL database (use Jaccard scoring to determine "source" keyword, or add new ?)
            cursor = db.cursor()
            get_token = "SELECT tokens.id FROM tokens WHERE tokens.token LIKE %(wrd)s"
            cursor.execute(get_token, { 'wrd': token })
            row = cursor.fetchone()
            # check for match
            #print ('  ',cursor.rowcount)
            if cursor.rowcount <= 0:
                # if no match, get closestMatch()
                matched_token_set = cursor.callproc('closestMatch', (token, (0, 'CHAR'), 0, 0) )
                matched_token = matched_token_set[1]
                matched_id = matched_token_set[2]
                matched_proximity = matched_token_set[3]
                # if match is insufficient, add it to the token table
                token_length = len(token)
                # if length <= 3, only 100% is sufficient (won't this still cause bugs -- e.g., fig vs gif?)
                # as length increases, required match decreases (+1/-5?)
                required_match = max(1 - (0.05 * (token_length - 3)), 0.6)
                #print(matched_token_set)
                if False: #matched_proximity > required_match:
                    new_token_id = matched_id
                    # update tokens table
                    add_to_tokens = "UPDATE tokens SET document_count = document_count + 1 WHERE id=%(tid)s"
                    cursor.execute(add_to_tokens, { 'tid': matched_id })
                    db.commit()
                else:
                    #print('new token!')
                    # add to tokens table
                    add_to_tokens = "INSERT INTO tokens (token, document_count) VALUES (%(str)s, 1)"
                    cursor.execute(add_to_tokens, { 'str': token })
                    db.commit()
                    new_token_id = cursor.lastrowid
            else:
                new_token_id = row[0]
                # update tokens table
                add_to_tokens = "UPDATE tokens SET document_count = document_count + 1 WHERE id=%(tid)s"
                cursor.execute(add_to_tokens, { 'tid': new_token_id })
                db.commit()
            # add to keywords table
            add_to_keywords = "INSERT INTO keywords (tokenId, postId, num_in_post) VALUES (%(tid)s, %(pid)s, %(count)s)"
            cursor.execute(add_to_keywords, { 'tid': new_token_id, 'pid': postID, 'count': count })
            db.commit()
            cursor.close()
        if i >= 5:
            raise Exception('finished five document')
    return

def initial_data_load(subreddit, db, fromCrash):
    # Reddit limits the results of each of these calls to 1000 posts; there will undoubtedly be some overlap between these,
    # but by using all of them, we're likely to get a larger number of total posts for analysis (although, unfortunately, only
    # a very small number of the total submissions on the subreddit)
    submissions = []
    if not fromCrash:
        #top
        submissions.append(subreddit.top())
        #hot
        submissions.append(subreddit.hot())
        #gilded
        submissions.append(subreddit.gilded())
        #controversial
        submissions.append(subreddit.controversial())
        #search1
        submissions.append(subreddit.search("title:? self:1",'relevance'))
        submissions.append(subreddit.search("title:? self:1",'hot'))
        submissions.append(subreddit.search("title:? self:1",'top'))
        submissions.append(subreddit.search("title:? self:1",'new'))
        #search2
        submissions.append(subreddit.search("title:question self:1",'relevance'))
        submissions.append(subreddit.search("title:question self:1",'hot'))
        submissions.append(subreddit.search("title:question self:1",'top'))
        submissions.append(subreddit.search("title:question self:1",'new'))
    #new
    submissions.append(subreddit.new())
    for postList in submissions:
        retrieve_token_counts(postList, db)
    return


#main -----------------------------------
r = praw.Reddit(user_agent=constants.USER_AGENT, client_id=constants.CLIENT_ID, client_secret=constants.CLIENT_SECRET, username=constants.REDDIT_USER, password=constants.REDDIT_PW)
db = mysql.connector.connect(user=constants.SQL_USER, password=constants.SQL_PW, host='localhost', database=constants.SQL_DATABASE)
if len(sys.argv) > 1:
	fromCrash = (sys.argv[1] == 'initial')
else:
	fromCrash = True

try:
    subr = r.subreddit(constants.SUBREDDIT_NAME)
    initial_data_load(subr, db, False)
    raise Exception('quit before "constant" loop')
    while True:
        callers = subr.stream.submissions()
        for caller in callers:
            process_post(caller, db, fromCrash)
except Exception as e:
    db.close()
    print(e)
    # other closing stuff? log the error?
