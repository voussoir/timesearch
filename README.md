timesearch
==========

# NEWS (2018 04 09):

[Reddit has removed the timestamp search feature which timesearch was built off of](https://voussoir.github.io/t3_7tus5f.html#t1_dtfcdn0) ([original](https://www.reddit.com/r/changelog/comments/7tus5f/update_to_search_api/dtfcdn0/)). Please message the admins by [sending a PM to /r/reddit.com](https://www.reddit.com/message/compose?to=%2Fr%2Freddit.com&subject=Timestamp+search). Let them know that this feature is important to you, and you would like them to restore it on the new search stack.

Thankfully, Jason Baumgartner aka [/u/Stuck_in_the_Matrix](https://reddit.com/u/Stuck_in_the_Matrix/overview), owner of [Pushshift.io](https://github.com/pushshift/api), has made it easy to interact with his dataset. Timesearch now queries his API to get post data, and then uses reddit's /api/info to get up-to-date information about those posts (scores, edited text bodies, ...). While we're at it, this also gives us the ability to speed up `get_comments`. In addition, we can get all of a user's comments which was not possible through reddit alone.

NOTE: Because Pushshift is an independent dataset run by a regular person, it does not contain posts from private subreddits. Without the timestamp search parameter, scanning private subreddits is now impossible. I urge once again that you contact ~~your senator~~ the admins to have this feature restored.

---

I don't have a test suite. You're my test suite! Messages go to [/u/GoldenSights](https://reddit.com/u/GoldenSights).

Timesearch is a collection of utilities for archiving subreddits.

### Make sure you have:
- Installed [Python](https://www.python.org/download). I use Python 3.7.
- Installed PRAW >= 4, as well as the other modules in `requirements.txt`. Try `pip install -r requirements.txt` to get them all.
- Created an OAuth app at https://reddit.com/prefs/apps. Make it `script` type, and set the redirect URI to `http://localhost:8080`. The title and description can be anything you want, and the about URL is not required.
- Used [this PRAW script](https://praw.readthedocs.io/en/latest/tutorials/refresh_token.html) to generate a refresh token. Just save it as a .py file somewhere and run it through your terminal / command line. For simplicity's sake, I just choose `all` for the scopes.
- Downloaded a copy of [this file](https://github.com/voussoir/reddit/blob/master/bot4.py) and saved it as `bot.py`. Fill out the variables using your OAuth information, and read the instructions to see where to put it. The Useragent is a description of your API usage. Typically "/u/username's praw client" is sufficient.
- Downloaded this project using the green "Clone or Download" button in the upper right.

### This package consists of:

- **get_submissions**: If you try to page through `/new` on a subreddit, you'll hit a limit at or before 1,000 posts. Timesearch uses the pushshift.io dataset to get information about very old posts, and then queries the reddit api to update their information. Previously, we used the `timestamp` cloudsearch query parameter on reddit's own API, but reddit has removed that feature and pushshift is now the only viable source for initial data.  
    `python timesearch.py get_submissions -r subredditname <flags>`  
    `python timesearch.py get_submissions -u username <flags>`

- **get_comments**: Similar to `get_submissions`, this tool queries pushshift for comment data and updates it from reddit.  
    `python timesearch.py get_comments -r subredditname <flags>`  
    `python timesearch.py get_comments -u username <flags>`

- **livestream**: get_submissions+get_comments is great for starting your database and getting the historical posts, but it's not the best for staying up-to-date. Instead, livestream monitors `/new` and `/comments` to continuously ingest data.  
    `python timesearch.py livestream -r subredditname <flags>`  
    `python timesearch.py livestream -u username <flags>`

- **get_styles**: Downloads the stylesheet and CSS images.  
    `python timesearch.py get_styles -r subredditname`

- **get_wiki**: Downloads the wiki pages, sidebar, etc. from /wiki/pages.  
    `python timesearch.py get_wiki -r subredditname`

- **offline_reading**: Renders comment threads into HTML via markdown.  
    Note: I'm currently using the [markdown library from pypi](https://pypi.python.org/pypi/Markdown), and it doesn't do reddit's custom markdown like `/r/` or `/u/`, obviously. So far I don't think anybody really uses o_r so I haven't invested much time into improving it.  
    `python timesearch.py offline_reading -r subredditname <flags>`  
    `python timesearch.py offline_reading -u username <flags>`

- **index**: Generates plaintext or HTML lists of submissions, sorted by a property of your choosing. You can order by date, author, flair, etc. With the `--offline` parameter, you can make all the links point to the files you generated with `offline_reading`.  
    `python timesearch.py index -r subredditname <flags>`  
    `python timesearch.py index -u username <flags>`

- **breakdown**: Produces a JSON file indicating which users make the most posts in a subreddit, or which subreddits a user posts in.  
    `python timesearch.py breakdown -r subredditname` <flags>  
    `python timesearch.py breakdown -u username` <flags>

- **merge_db**: Copy all new data from one timesearch database into another. Useful for syncing or merging two scans of the same subreddit.  
    `python timesearch.py merge_db --from filepath/database1.db --to filepath/database2.db`

### To use it

When you download this project, the main file that you will execute is `timesearch.py` here in the root directory. It will load the appropriate module to run your command from the modules folder.

You can view a summarized version of all the help text by running `timesearch.py`, and you can view a specific help text by running a command with no arguments, like `timesearch.py livestream`, etc.

I recommend [sqlitebrowser](https://github.com/sqlitebrowser/sqlitebrowser/releases) if you want to inspect the database yourself.

### Changelog
- 2020 01 27
    - When I first created Timesearch, it was simply a collection of all the random scripts I had written to archive various things. And they tended to have wacky names like `commentaugment` and `redmash`. Well, since the timesearch toolkit is meant to be a singular cohesive package now I decided to finally rename everything. I believe I have aliased everything properly so the old names still work for backwards compat, except for the fact the modules folder is now called `timesearch_modules` which may break your import statements if you ever imported that on your own.

- 2018 04 09
    - Integrated with Pushshift to restore timesearch functionality, speed up commentaugment, and get user comments.

- 2017 11 13
    - Gave timesearch its own Github repository so that (1) it will be easier for people to download it and (2) it has a cleaner, more independent URL. [voussoir/timesearch](https://github.com/voussoir/timesearch)

- 2017 11 05
    - Added a try-except inside livestream helper to prevent generator from terminating.

- 2017 11 04
    - For timesearch, I switched from using my custom cloudsearch iterator to the one that comes with PRAW4+.

- 2017 10 12
    - Added the `mergedb` utility for combining databases.

- 2017 06 02
    - You can use `commentaugment -s abcdef` to get a particular thread even if you haven't scraped anything else from that subreddit. Previously `-s` only worked if the database already existed and you specified it via `-r`. Now it is inferred from the submission itself.

- 2017 04 28
    - Complete restructure into package, started using PRAW4.

- 2016 08 10
    - Started merging redmash and wrote its argparser

- 2016 07 03
    - Improved docstring clarity.

- 2016 07 02
    - Added `livestream` argparse

- 2016 06 07
    - Offline_reading has been merged with the main timesearch file
    - `get_all_posts` renamed to `timesearch`
    - Timesearch parameter `usermode` renamed to `username`; `maxupper` renamed to `upper`.
    - Everything now accessible via commandline arguments. Read the docstring at the top of the file.

- 2016 06 05
    - NEW DATABASE SCHEME. Submissions and comments now live in different tables like they should have all along. Submission table has two new columns for a little bit of commentaugment metadata. This allows commentaugment to only scan threads that are new.
    - You can use the `migrate_20160605.py` script to convert old databases into new ones.

- 2015 11 11
    - created `offline_reading.py` which converts a timesearch database into a comment tree that can be rendered into HTML

- 2015 09 07
    - fixed bug which allowed `livestream` to crash because `bot.refresh()` was outside of the try-catch.

- 2015 08 19
    - fixed bug in which updatescores stopped iterating early if you had more than 100 comments in a row in the db
    - commentaugment has been completely merged into the timesearch.py file. you can use commentaugment_prompt() to input the parameters, or use the commentaugment() function directly.


____


I want to live in a future where everyone uses UTC and agrees on daylight savings.

<p align="center">
    <img height=256 src="https://github.com/voussoir/timesearch/blob/master/timesearch_logo.svg?raw=true&sanitize=true" alt="Timesearch"/>
</p>

https://github.com/voussoir/timesearch

https://gitlab.com/voussoir/timesearch

https://codeberg.org/voussoir/timesearch
