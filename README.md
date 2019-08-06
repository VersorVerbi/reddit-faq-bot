# Reddit FAQ Bot
FAQ bot for the r/Catholicism subreddit

## How to Use
### On Reddit

### As an Administrator
Run the program with `python faqbot.py` to create the tables in the database and do the first major download of historical posts on the subreddit. If the bot crashes during that initial load, run it again with `python faqbot.py initial` to get it to finish that first big chunk of data. All data loaded during the initial load is processed, but ignored (i.e., the bot will not reply to any posts until after the initial load).

If the script crashes after that initial load is complete, you can restart it with just `python faqbot.py`. Any posts made in the intervening time will be addressed as if they were brand-new (i.e., the bot will process them and respond to them as normal).

If at some point you significantly change the way things are processed (you exclude or include more flairs, for example) or the functionality of the bot changes significantly, you will likely want to reinterpret data without losing it. This would be critically important, for example, if you've been using the bot a long time and have many more posts than Reddit would give you with its hard-coded 1000 limit. In that case, kill the bot's process and run it again with `python faqbot.py reset`. All tokens and keywords will be erased, but post data will not, and every post that has ever been analyzed by the bot will be analyzed again.

## How to Make Your Own for Another Subreddit
Using config/constants.py.example, create your own constants.py file.

Put the repository in an appropriate folder on your server, where Python is installed. Make sure to include the SQL files.

Use Python to run faqbot.py per instructions above. It will create the SQL tables for you.

## FAQ
### What version of Python is this compatible with?
I used Python 3.7 to program it originally. I haven't done backwards compatibility testing (or forwards, depending on how long from now someone is reading this).
