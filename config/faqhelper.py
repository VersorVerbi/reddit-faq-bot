# region enums
ADMIN_COMMANDS = {
    'DATA': 'command_ok()',
    'HELP': 'command_ok()',
    'MODFAVE': 'add_favorite(cmd[1])',
    'MODUNFAVE': 'remove_favorite(cmd[1])',
    'NUMKEYS': 'update_numkeys(cmd[1])',
    'NUMLINKS': 'update_numlinks(cmd[1])',
    'QUERY': 'command_ok()',
    'REDUCEUNIQUENESS': 'ignore_token(cmd[1])',
    'TEST': 'command_ok()',
    'CURATE': 'add_curated(\'\'.join(cmd[1:]), msg.body)',
    'RECURATE': 'edit_curated(cmd[1:], msg.body)',
    'TRASH': 'remove_curated(cmd[1])'
}

ADMIN_REPLIES = {
    'DATA': 'quick_analytics()',
    'HELP': 'help_text()',
    'MODFAVE': 'favorite_added(cmd[1])',
    'MODUNFAVE': 'favorite_removed(cmd[1])',
    'NUMKEYS': 'new_numkeys(cmd[1])',
    'NUMLINKS': 'new_numlinks(cmd[1])',
    'QUERY': 'query_results(msg)',
    'REDUCEUNIQUENESS': 'token_ignored(cmd[1])',
    'TEST': 'test_results(cmd[1])',
    'CURATE': 'curated_added(cmd[1])',
    'RECURATE': 'curated_edited(cmd[1])',
    'TRASH': 'curated_removed(cmd[1])'
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
                             'BE REVERSED. PROCEED WITH CAUTION.**',
    'TEST id': 'Where `id` is the string immediately after `/comments/` in the URL of a thread, e.g., `cdgbpv`. '
               'Use this command to see (1) evaluated keywords and (2) related posts as determined by the bot. This '
               'can be helpful for determining false positives, figuring out mod favorites, adding specific posts '
               'to the database that may have ended up outside our initial queries, and improving the responses of '
               'the bot in general.',
    'CURATE keywords': 'Where `keywords` is the comma-delimited list of keywords for which this curated response is '
                       'relevant, sorted from most relevant to least relevant. (This weighted priority will be '
                       'used to determine when to show this response, and when this response is more relevant than '
                       'some other response on a similar topic.) The body of your message should be the exact content '
                       'you want displayed for this curated comment.',
    'RECURATE id newkeywords': 'Where `id` is the database ID of the curated response you want (send a `DATA` message '
                               'to the bot to get a list of those) and `newkeywords` is the (optional) new comma-'
                               'delimited list of keywords for the curated response. The body of your message should '
                               'be an (optional) updated content for the curated response. Either `newkeywords` or the '
                               'new content must be included, or else your update request will fail.',
    'TRASH id': 'Where `id` is the database ID of the curated response to want to get rid of (send a `DATA` message '
                'to the bot to get a list of those). The curated response will be permanently deleted. You will not be '
                'asked again. You will not be able to retrieve it after doing so. Use with caution.'
}


# endregion


# region custom exceptions
class Error(Exception):
    """base class for our custom exceptions"""
    pass


class IgnoredFlair(Error):
    """this error is raised when a post with an ignored flair text is processed"""
    pass


class IgnoredTitle(Error):
    """this error is raised when a post with ignored text in the title is processed"""
    pass


class IncorrectPostType(Error):
    """this error is raised when a mod/sticky post or link post is processed"""
    pass


class AlreadyProcessed(Error):
    """this error is raised when a post that has already been processed is processed again"""
    pass


class MissingParameter(Error):
    """this error is raised when a command is sent without the right parameters"""
    pass


class MismatchedParameter(Error):
    """this error is raised when a command is sent with the wrong type of parameter"""
    pass


class BadParameter(Error):
    """this error is raised when a command is sent with a parameter of the correct type,
    but the parameter value is dumb"""
    pass


class WrongSubreddit(Error):
    """this error is raised when the bot is commanded to deal with a post in a different subreddit"""
    pass


class IncorrectState(Error):
    """this error is raised when the bot is commanded to do something that doesn't make sense,
    e.g., favorite a favorited post, or unfavorite one that isn't a favorite"""
    pass


class NoRelations(Error):
    """no related posts could be found"""
    keyword_list: str = ""

    def __init__(self, **kwargs):
        self.keyword_list = kwargs['keys']

    pass


class NoKeywords(Error):
    """no keywords could be found in the source material"""
    pass
# endregion
