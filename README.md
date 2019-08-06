# Reddit FAQ Bot
FAQ bot for the r/Catholicism subreddit

## How to Use
### On Reddit

### As an Administrator
Run the program with `python faqbot.py` to create the tables in the database and do the first major download of historical posts on the subreddit. If the bot crashes during that initial load, run it again with `python faqbot.py initial` to get it to finish that first big chunk of data. All data loaded during the initial load is processed, but ignored (i.e., the bot will not reply to any posts until after the initial load).

If the script crashes after that initial load is complete, you can restart it with just `python faqbot.py`. Any posts made in the intervening time will be addressed as if they were brand-new (i.e., the bot will process them and respond to them as normal).

## How to Make Your Own for Another Subreddit
Using config/constants.py.example, create your own constants.py file.

Put the repository in an appropriate folder on your server, where Python is installed. Make sure to include the SQL files.

Use Python to run faqbot.py per instructions above. It will create the SQL tables for you.

## FAQ
### What version of Python is this compatible with?
I used Python 3.7 to program it originally. I haven't done backwards compatibility testing (or forwards, depending on how long from now someone is reading this).
