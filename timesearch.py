'''
This is the main launch file for Timesearch.

When you run `python timesearch.py get_submissions -r subredditname` or any
other command, your arguments will go to the timesearch_modules file as
appropriate for your command.
'''
import argparse
import sys

from voussoirkit import betterhelp
from voussoirkit import vlogging

from timesearch_modules import exceptions

# NOTE: Originally I wanted the docstring for each module to be within their
# file. However, this means that composing the global helptext would require
# importing those modules, which will subsequently import PRAW and a whole lot
# of other things. This made TS very slow to load which is okay when you're
# actually using it but really terrible when you're just viewing the help text.

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

@vlogging.main_decorator
def main(argv):
    parser = argparse.ArgumentParser(
        description='''
        The subreddit archiver

        The basics:
        1. Collect a subreddit's submissions
            timesearch get_submissions -r subredditname

        2. Collect the comments for those submissions
            timesearch get_comments -r subredditname

        3. Stay up to date
            timesearch livestream -r subredditname
        ''',
    )
    subparsers = parser.add_subparsers()

    # BREAKDOWN
    p_breakdown = subparsers.add_parser(
        'breakdown',
        description='''
        Generate the comment / submission counts for users in a subreddit, or
        the subreddits that a user posts to.

        Automatically dumps into a <database>_breakdown.json file
        in the same directory as the database.
        ''',
    )
    p_breakdown.add_argument(
        '--sort',
        dest='sort',
        type=str,
        default=None,
        help='''
        Sort the output by one property.
        Should be one of "name", "submissions", "comments", "total_posts".
        ''',
    )
    p_breakdown.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
        default=None,
        help='''
        The subreddit database to break down.
        ''',
    )
    p_breakdown.add_argument(
        '-u',
        '--user',
        dest='username',
        default=None,
        help='''
        The username database to break down.
        ''',
    )
    p_breakdown.set_defaults(func=breakdown_gateway)

    # GET_COMMENTS
    p_get_comments = subparsers.add_parser(
        'get_comments',
        aliases=['get-comments', 'commentaugment'],
        description='''
        Collect comments on a subreddit or comments made by a user.
        ''',
    )
    p_get_comments.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
        default=None,
    )
    p_get_comments.add_argument(
        '-s',
        '--specific',
        dest='specific_submission',
        default=None,
        help='''
        Given a submission ID like t3_xxxxxx, scan only that submission.
        ''',
    )
    p_get_comments.add_argument(
        '-u',
        '--user',
        dest='username',
        default=None,
    )
    p_get_comments.add_argument(
        '--dont_supplement',
        '--dont-supplement',
        dest='do_supplement',
        action='store_false',
        help='''
        If provided, trust the pushshift data and do not fetch live copies
        from reddit.
        ''',
    )
    p_get_comments.add_argument(
        '--lower',
        dest='lower',
        default='update',
        help='''
        If a number - the unix timestamp to start at.
        If "update" - continue from latest comment in db.
        WARNING: If at some point you collected comments for a particular
        submission which was ahead of the rest of your comments, using "update"
        will start from that later submission, and you will miss the stuff in
        between that specific post and the past.
        ''',
    )
    p_get_comments.add_argument(
        '--upper',
        dest='upper',
        default=None,
        help='''
        If a number - the unix timestamp to stop at.
        If not provided - stop at current time.
        ''',
    )
    p_get_comments.set_defaults(func=get_comments_gateway)

    # GET_STYLES
    p_get_styles = subparsers.add_parser(
        'get_styles',
        aliases=['get-styles', 'getstyles'],
        help='''
        Collect the stylesheet, and css images.
        ''',
    )
    p_get_styles.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
    )
    p_get_styles.set_defaults(func=get_styles_gateway)

    # GET_WIKI
    p_get_wiki = subparsers.add_parser(
        'get_wiki',
        aliases=['get-wiki', 'getwiki'],
        description='''
        Collect all available wiki pages.
        ''',
    )
    p_get_wiki.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
    )
    p_get_wiki.set_defaults(func=get_wiki_gateway)

    # LIVESTREAM
    p_livestream = subparsers.add_parser(
        'livestream',
        description='''
        Continously collect submissions and/or comments.
        ''',
    )
    p_livestream.add_argument(
        '--once',
        dest='once',
        action='store_true',
        help='''
        If provided, only do a single loop. Otherwise go forever.
        ''',
    )
    p_livestream.add_argument(
        '-c',
        '--comments',
        dest='comments',
        action='store_true',
        help='''
        If provided, do collect comments. Otherwise don't.

        If submissions and comments are BOTH left unspecified, then they will
        BOTH be collected.
        ''',
    )
    p_livestream.add_argument(
        '--limit',
        dest='limit',
        type=int,
        default=None,
        help='''
        Number of items to fetch per request.
        ''',
    )
    p_livestream.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
        default=None,
        help='''
        The subreddit to collect from.
        ''',
    )
    p_livestream.add_argument(
        '-s',
        '--submissions',
        dest='submissions',
        action='store_true',
        help='''
        If provided, do collect submissions. Otherwise don't.

        If submissions and comments are BOTH left unspecified, then they will
        BOTH be collected.
        ''',
    )
    p_livestream.add_argument(
        '-u',
        '--user',
        dest='username',
        default=None,
        help='''
        The redditor to collect from.
        ''',
    )
    p_livestream.add_argument(
        '-w',
        '--wait',
        dest='sleepy',
        default=30,
        help='''
        The number of seconds to wait between cycles.
        ''',
    )
    p_livestream.set_defaults(func=livestream_gateway)

    # MERGEDB'
    p_merge_db = subparsers.add_parser(
        'merge_db',
        aliases=['merge-db', 'mergedb'],
        description='''
        Copy all new posts from one timesearch database into another.
        ''',
    )
    p_merge_db.examples = [
        '--from redditdev1.db --to redditdev2.db',
    ]
    p_merge_db.add_argument(
        '--from',
        dest='from_db_path',
        required=True,
        help='''
        The database file containing the posts you wish to copy.
        ''',
    )
    p_merge_db.add_argument(
        '--to',
        dest='to_db_path',
        required=True,
        help='''
        The database file to which you will copy the posts.
        The database is modified in-place.
        Existing posts will be ignored and not updated.
        ''',
    )
    p_merge_db.set_defaults(func=merge_db_gateway)

    # OFFLINE_READING
    p_offline_reading = subparsers.add_parser(
        'offline_reading',
        description='''
        Render submissions and comment threads to HTML via Markdown.
        ''',
    )
    p_offline_reading.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
        default=None,
    )
    p_offline_reading.add_argument(
        '-s',
        '--specific',
        dest='specific_submission',
        default=None,
        type=str,
        help='''
        Given a submission ID like t3_xxxxxx, render only that submission.
        Otherwise render every submission in the database.
        ''',
    )
    p_offline_reading.add_argument(
        '-u',
        '--user',
        dest='username',
        default=None,
    )
    p_offline_reading.set_defaults(func=offline_reading_gateway)

    # INDEX
    p_index = subparsers.add_parser(
        'index',
        aliases=['redmash'],
        description='''
        Dump submission listings to a plaintext or HTML file.
        ''',
    )
    p_index.examples = [
        {
            'args': '-r botwatch --date',
            'comment': 'Does only the date file.'
        },
        {
            'args': '-r botwatch --score --title',
            'comment': 'Does both the score and title files.'
        },
        {
            'args': '-r botwatch --score --score_threshold 50',
            'comment': 'Only shows submissions with >= 50 points.'
        },
        {
            'args': '-r botwatch --all',
            'comment': 'Performs all of the different mashes.'
        },
    ]
    p_index.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
        default=None,
        help='''
        The subreddit database to dump.
        ''',
    )
    p_index.add_argument(
        '-u',
        '--user',
        dest='username',
        default=None,
        help='''
        The username database to dump.
        ''',
    )
    p_index.add_argument(
        '--all',
        dest='do_all',
        action='store_true',
        help='''
        Perform all of the indexes listed below.
        ''',
    )
    p_index.add_argument(
        '--author',
        dest='do_author',
        action='store_true',
        help='''
        For subreddit databases only.
        Perform an index sorted by author.
        ''',
    )
    p_index.add_argument(
        '--date',
        dest='do_date',
        action='store_true',
        help='''
        Perform an index sorted by date.
        ''',
    )
    p_index.add_argument(
        '--flair',
        dest='do_flair',
        action='store_true',
        help='''
        Perform an index sorted by flair.
        ''',
    )
    p_index.add_argument(
        '--html',
        dest='html',
        action='store_true',
        help='''
        Write HTML files instead of plain text.
        ''',
    )
    p_index.add_argument(
        '--score',
        dest='do_score',
        action='store_true',
        help='''
        Perform an index sorted by score.
        ''',
    )
    p_index.add_argument(
        '--sub',
        dest='do_subreddit',
        action='store_true',
        help='''
        For username databases only.
        Perform an index sorted by subreddit.
        ''',
    )
    p_index.add_argument(
        '--title',
        dest='do_title',
        action='store_true',
        help='''
        Perform an index sorted by title.
        ''',
    )
    p_index.add_argument(
        '--offline',
        dest='offline',
        action='store_true',
        help='''
        The links in the index will point to the files generated by
        offline_reading. That is, `../offline_reading/fullname.html` instead
        of `http://redd.it/id`. This will NOT trigger offline_reading to
        generate the files now, so you must run that tool separately.
        ''',
    )
    p_index.add_argument(
        '--score_threshold',
        '--score-threshold',
        dest='score_threshold',
        type=int,
        default=0,
        help='''
        Only index posts with at least this many points.
        Applies to ALL indexes!
        ''',
    )
    p_index.set_defaults(func=index_gateway)

    # GET_SUBMISSIONS
    p_get_submissions = subparsers.add_parser(
        'get_submissions',
        aliases=['get-submissions', 'timesearch'],
        description='''
        Collect submissions from the subreddit across all of history, or
        Collect submissions by a user (as many as possible).
        ''',
    )
    p_get_submissions.add_argument(
        '--lower',
        dest='lower',
        default='update',
        help='''
        If a number - the unix timestamp to start at.
        If "update" - continue from latest submission in db.
        ''',
    )
    p_get_submissions.add_argument(
        '-r',
        '--subreddit',
        dest='subreddit',
        type=str,
        default=None,
        help='''
        The subreddit to scan. Mutually exclusive with username.
        ''',
    )
    p_get_submissions.add_argument(
        '-u',
        '--user',
        dest='username',
        type=str,
        default=None,
        help='''
        The user to scan. Mutually exclusive with subreddit.
        ''',
    )
    p_get_submissions.add_argument(
        '--upper',
        dest='upper',
        default=None,
        help='''
        If a number - the unix timestamp to stop at.
        If not provided - stop at current time.
        ''',
    )
    p_get_submissions.add_argument(
        '--dont_supplement',
        '--dont-supplement',
        dest='do_supplement',
        action='store_false',
        help='''
        If provided, trust the pushshift data and do not fetch live copies
        from reddit.
        ''',
    )
    p_get_submissions.set_defaults(func=get_submissions_gateway)

    try:
        return betterhelp.go(parser, argv)
    except exceptions.DatabaseNotFound as exc:
        message = str(exc)
        message += '\nHave you used any of the other utilities to collect data?'
        print(message)
        return 1

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
