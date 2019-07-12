# Reddit FAQ Bot
FAQ bot for the r/Catholicism subreddit

## How to Use
### On Reddit

### As an Administrator
Run the program initially with `python faqbot.py initial` to do the first major download of historical posts on the subreddit.

If the script crashes after that initial load is complete, you can restart it with just `python faqbot.py`.

## How to Make Your Own for Another Subreddit
Using config/constants.py.example, create your own constants.py file.

Import functions.sql and procedures.sql into your SQL database.

Put the repository in an appropriate folder on your server, where Python is installed.

Use Python to run faqbot.py per instructions above.

## FAQ
### What version of Python is this compatible with?
I used Python 3.7 to program it originally. I haven't done backwards compatibility testing (or forwards, depending on how long from now someone is reading this).
