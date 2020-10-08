'''
This is the main launch file for Timesearch.

When you run `python timesearch.py get_submissions -r subredditname` or any
other command, your arguments will go to the timesearch_modules file as
appropriate for your command.
'''
import logging
handler = logging.StreamHandler()
log_format = '{levelname}:timesearch.{module}.{funcName}: {message}'
handler.setFormatter(logging.Formatter(log_format, style='{'))
logging.getLogger().addHandler(handler)

import argparse
import sys

from voussoirkit import betterhelp

from timesearch_modules import exceptions

# NOTE: Originally I wanted the docstring for each module to be within their
# file. However, this means that composing the global helptext would require
# importing those modules, which will subsequently import PRAW and a whole lot
# of other things. This made TS very slow to load which is okay when you're
# actually using it but really terrible when you're just viewing the help text.
DOCSTRING = '''
Timesearch
The subreddit archiver

The basics:
1. Collect a subreddit's submissions
    python timesearch.py get_submissions -r subredditname

2. Collect the comments for those submissions
    python timesearch.py get_comments -r subredditname

3. Stay up to date
    python timesearch.py livestream -r subredditname

Commands for collecting:

{get_submissions}

{get_comments}

{livestream}

{get_styles}

{get_wiki}

Commands for processing:

{breakdown}

{index}

{merge_db}

{offline_reading}

TO SEE DETAILS ON EACH COMMAND, RUN
python timesearch.py <command>
'''.lstrip()

SUB_DOCSTRINGS = dict(
breakdown='''
breakdown:
    Give the comment / submission counts for users in a subreddit, or
    the subreddits that a user posts to.

    Automatically dumps into a <database>_breakdown.json file
    in the same directory as the database.

    python timesearch.py breakdown -r subredditname <flags>
    python timesearch.py breakdown -u username <flags>

    flags:
    -r "test" | --subreddit "test":
        The subreddit database to break down.

    -u "test" | --username "test":
        The username database to break down.

    --sort "name" | "submissions" | "comments" | "total_posts"
        Sort the output.
'''.strip(),

get_comments='''
get_comments:
    Collect comments on a subreddit or comments made by a user.

    python timesearch.py get_comments -r subredditname <flags>
    python timesearch.py get_comments -u username <flags>

    flags:
    -s "t3_xxxxxx" | --specific "t3_xxxxxx":
        Given a submission ID, t3_xxxxxx, scan only that submission.

    -l "update" | --lower "update":
        If a number - the unix timestamp to start at.
        If "update" - continue from latest comment in db.
        WARNING: If at some point you collected comments for a particular
        submission which was ahead of the rest of your comments, using "update"
        will start from that later submission, and you will miss the stuff in
        between that specific post and the past.
        Default: update

    -up 1467460221 | --upper 1467460221:
        If a number - the unix timestamp to stop at.
        If not provided - stop at current time.
        Default: current time

    --dont_supplement:
        If provided, trust the pushshift data and do not fetch live copies
        from reddit.

    -v | --verbose:
        If provided, print extra information to the screen.
'''.strip(),

get_styles='''
get_styles:
    Collect the stylesheet, and css images.

    python timesearch.py get_styles -r subredditname
'''.strip(),

get_submissions='''
get_submissions:
    Collect submissions from the subreddit across all of history, or
    Collect submissions by a user (as many as possible).

    python timesearch.py get_submissions -r subredditname <flags>
    python timesearch.py get_submissions -u username <flags>

    -r "test" | --subreddit "test":
        The subreddit to scan. Mutually exclusive with username.

    -u "test" | --username "test":
        The user to scan. Mutually exclusive with subreddit.

    -l "update" | --lower "update":
        If a number - the unix timestamp to start at.
        If "update" - continue from latest submission in db.
        Default: update

    -up 1467460221 | --upper 1467460221:
        If a number - the unix timestamp to stop at.
        If not provided - stop at current time.
        Default: current time

    --dont_supplement:
        If provided, trust the pushshift data and do not fetch live copies
        from reddit.

    -v | --verbose:
        If provided, print extra information to the screen.
'''.strip(),

get_wiki='''
get_wiki:
    Collect all available wiki pages.

    python timesearch.py get_wiki -r subredditname
'''.strip(),

index='''
index:
    Dump submission listings to a plaintext or HTML file.

    python timesearch.py index -r subredditname <flags>
    python timesearch.py index -u username <flags>

    flags:
    -r "test" | --subreddit "test":
        The subreddit database to dump

    -u "test" | --username "test":
        The username database to dump

    --html:
        Write HTML files instead of plain text.

    --offline:
        The links in the index will point to the files generated by
        offline_reading. That is, `../offline_reading/fullname.html` instead
        of `http://redd.it/id`. This will NOT trigger offline_reading to
        generate the files now, so you must run that tool separately.

    -st 50 | --score_threshold 50:
        Only index posts with at least this many points.
        Applies to ALL indexes!

    --all:
        Perform all of the indexes listed below.

    --date:
        Perform a index sorted by date.

    --title:
        Perform a index sorted by title.

    --score:
        Perform a index sorted by score.

    --author:
        For subreddit databases only.
        Perform a index sorted by author.

    --sub:
        For username databases only.
        Perform a index sorted by subreddit.

    --flair:
        Perform a index sorted by flair.

    examples:
        `timesearch index -r botwatch --date`
        does only the date file.

        `timesearch index -r botwatch --score --title`
        does both the score and title files.

        `timesearch index -r botwatch --score --score_threshold 50`
        only shows submissions with >= 50 points.

        `timesearch index -r botwatch --all`
        performs all of the different mashes.
'''.strip(),

livestream='''
livestream:
    Continously collect submissions and/or comments.

    python timesearch.py livestream -r subredditname <flags>
    python timesearch.py livestream -u username <flags>

    flags:
    -r "test" | --subreddit "test":
        The subreddit to collect from.

    -u "test" | --username "test":
        The redditor to collect from.

    -s | --submissions:
        If provided, do collect submissions. Otherwise don't.

    -c | --comments:
        If provided, do collect comments. Otherwise don't.

    If submissions and comments are BOTH left unspecified, then they will
    BOTH be collected.

    -v | --verbose:
        If provided, print extra information to the screen.

    -w 30 | --wait 30:
        The number of seconds to wait between cycles.

    -1 | --once:
        If provided, only do a single loop. Otherwise go forever.
'''.strip(),

merge_db='''
merge_db:
    Copy all new posts from one timesearch database into another.

    python timesearch.py merge_db --from redditdev1.db --to redditdev2.db

    flags:
    --from:
        The database file containing the posts you wish to copy.

    --to:
        The database file to which you will copy the posts.
        The database is modified in-place.
        Existing posts will be ignored and not updated.
'''.strip(),

offline_reading='''
offline_reading:
    Render submissions and comment threads to HTML via Markdown.

    python timesearch.py offline_reading -r subredditname <flags>
    python timesearch.py offline_reading -u username <flags>

    flags:
    -s "t3_xxxxxx" | --specific "t3_xxxxxx":
        Given a submission ID, t3_xxxxxx, render only that submission.
        Otherwise render every submission in the database.
'''.strip(),
)

DOCSTRING = betterhelp.add_previews(DOCSTRING, SUB_DOCSTRINGS)

####################################################################################################
####################################################################################################

def breakdown_gateway(args):
    from timesearch_modules import breakdown
    breakdown.breakdown_argparse(args)

def get_comments_gateway(args):
    from timesearch_modules import get_comments
    get_comments.get_comments_argparse(args)

def get_styles_gateway(args):
    from timesearch_modules import get_styles
    get_styles.get_styles_argparse(args)

def get_wiki_gateway(args):
    from timesearch_modules import get_wiki
    get_wiki.get_wiki_argparse(args)

def livestream_gateway(args):
    from timesearch_modules import livestream
    livestream.livestream_argparse(args)

def merge_db_gateway(args):
    from timesearch_modules import merge_db
    merge_db.merge_db_argparse(args)

def offline_reading_gateway(args):
    from timesearch_modules import offline_reading
    offline_reading.offline_reading_argparse(args)

def index_gateway(args):
    from timesearch_modules import index
    index.index_argparse(args)

def get_submissions_gateway(args):
    from timesearch_modules import get_submissions
    get_submissions.get_submissions_argparse(args)

def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers()

    p_breakdown = subparsers.add_parser('breakdown')
    p_breakdown.add_argument('--sort', dest='sort', default=None)
    p_breakdown.add_argument('-r', '--subreddit', dest='subreddit', default=None)
    p_breakdown.add_argument('-u', '--user', dest='username', default=None)
    p_breakdown.set_defaults(func=breakdown_gateway)

    p_get_comments = subparsers.add_parser('get_comments', aliases=['commentaugment'])
    p_get_comments.add_argument('-r', '--subreddit', dest='subreddit', default=None)
    p_get_comments.add_argument('-s', '--specific', dest='specific_submission', default=None)
    p_get_comments.add_argument('-u', '--user', dest='username', default=None)
    p_get_comments.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    p_get_comments.add_argument('--dont_supplement', '--dont-supplement', dest='do_supplement', action='store_false')
    p_get_comments.add_argument('-l', '--lower', dest='lower', default='update')
    p_get_comments.add_argument('-up', '--upper', dest='upper', default=None)
    p_get_comments.set_defaults(func=get_comments_gateway)

    p_get_styles = subparsers.add_parser('get_styles', aliases=['getstyles'])
    p_get_styles.add_argument('-r', '--subreddit', dest='subreddit')
    p_get_styles.set_defaults(func=get_styles_gateway)

    p_get_wiki = subparsers.add_parser('get_wiki', aliases=['getwiki'])
    p_get_wiki.add_argument('-r', '--subreddit', dest='subreddit')
    p_get_wiki.set_defaults(func=get_wiki_gateway)

    p_livestream = subparsers.add_parser('livestream')
    p_livestream.add_argument('-1', '--once', dest='once', action='store_true')
    p_livestream.add_argument('-c', '--comments', dest='comments', action='store_true')
    p_livestream.add_argument('-l', '--limit', dest='limit', default=None)
    p_livestream.add_argument('-r', '--subreddit', dest='subreddit', default=None)
    p_livestream.add_argument('-s', '--submissions', dest='submissions', action='store_true')
    p_livestream.add_argument('-u', '--user', dest='username', default=None)
    p_livestream.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    p_livestream.add_argument('-w', '--wait', dest='sleepy', default=30)
    p_livestream.set_defaults(func=livestream_gateway)

    p_merge_db = subparsers.add_parser('merge_db', aliases=['mergedb'])
    p_merge_db.add_argument('--from', dest='from_db_path', required=True)
    p_merge_db.add_argument('--to', dest='to_db_path', required=True)
    p_merge_db.set_defaults(func=merge_db_gateway)

    p_offline_reading = subparsers.add_parser('offline_reading')
    p_offline_reading.add_argument('-r', '--subreddit', dest='subreddit', default=None)
    p_offline_reading.add_argument('-s', '--specific', dest='specific_submission', default=None)
    p_offline_reading.add_argument('-u', '--user', dest='username', default=None)
    p_offline_reading.set_defaults(func=offline_reading_gateway)

    p_index = subparsers.add_parser('index', aliases=['redmash'])
    p_index.add_argument('--all', dest='do_all', action='store_true')
    p_index.add_argument('--author', dest='do_author', action='store_true')
    p_index.add_argument('--date', dest='do_date', action='store_true')
    p_index.add_argument('--flair', dest='do_flair', action='store_true')
    p_index.add_argument('--html', dest='html', action='store_true')
    p_index.add_argument('--score', dest='do_score', action='store_true')
    p_index.add_argument('--sub', dest='do_subreddit', action='store_true')
    p_index.add_argument('--title', dest='do_title', action='store_true')
    p_index.add_argument('--offline', dest='offline', action='store_true')
    p_index.add_argument('-r', '--subreddit', dest='subreddit', default=None)
    p_index.add_argument('-st', '--score_threshold', '--score-threshold', dest='score_threshold', default=0)
    p_index.add_argument('-u', '--user', dest='username', default=None)
    p_index.set_defaults(func=index_gateway)

    p_get_submissions = subparsers.add_parser('get_submissions', aliases=['timesearch'])
    p_get_submissions.add_argument('-l', '--lower', dest='lower', default='update')
    p_get_submissions.add_argument('-r', '--subreddit', dest='subreddit', default=None)
    p_get_submissions.add_argument('-u', '--user', dest='username', default=None)
    p_get_submissions.add_argument('-up', '--upper', dest='upper', default=None)
    p_get_submissions.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    p_get_submissions.add_argument('--dont_supplement', '--dont-supplement', dest='do_supplement', action='store_false')
    p_get_submissions.set_defaults(func=get_submissions_gateway)

    try:
        return betterhelp.subparser_main(
            argv,
            parser,
            main_docstring=DOCSTRING,
            sub_docstrings=SUB_DOCSTRINGS,
        )
    except exceptions.DatabaseNotFound as exc:
        message = str(exc)
        message += '\nHave you used any of the other utilities to collect data?'
        print(message)
        return 1

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
