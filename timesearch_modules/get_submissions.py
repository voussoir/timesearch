import time
import traceback

from . import common
from . import exceptions
from . import pushshift
from . import tsdb

def _normalize_subreddit(subreddit):
    if subreddit is None:
        pass
    elif isinstance(subreddit, str):
        subreddit = common.r.subreddit(subreddit)
    elif not isinstance(subreddit, common.praw.models.Subreddit):
        raise TypeError(type(subreddit))
    return subreddit

def _normalize_user(user):
    if user is None:
        pass
    elif isinstance(user, str):
        user = common.r.redditor(user)
    elif not isinstance(user, common.praw.models.Redditor):
        raise TypeError(type(user))
    return user

def get_submissions(
        subreddit=None,
        username=None,
        lower=None,
        upper=None,
        do_supplement=True,
    ):
    '''
    Collect submissions across time.
    Please see the global DOCSTRING variable.
    '''
    if not common.is_xor(subreddit, username):
        raise exceptions.NotExclusive(['subreddit', 'username'])

    common.login()

    if subreddit:
        (database, subreddit) = tsdb.TSDB.for_subreddit(subreddit, fix_name=True)
    elif username:
        (database, username) = tsdb.TSDB.for_user(username, fix_name=True)
    cur = database.sql.cursor()

    subreddit = _normalize_subreddit(subreddit)
    user = _normalize_user(username)

    if lower == 'update':
        # Start from the latest submission
        cur.execute('SELECT created FROM submissions ORDER BY created DESC LIMIT 1')
        fetch = cur.fetchone()
        if fetch is not None:
            lower = fetch[0]
        else:
            lower = None
    if lower is None:
        lower = 0

    if username:
        submissions = pushshift.get_submissions_from_user(username, lower=lower, upper=upper)
    else:
        submissions = pushshift.get_submissions_from_subreddit(subreddit, lower=lower, upper=upper)

    if do_supplement:
        submissions = pushshift.supplement_reddit_data(submissions, chunk_size=100)
    submissions = common.generator_chunker(submissions, 200)

    form = '{lower} ({lower_unix}) - {upper} ({upper_unix}) +{gain}'
    for chunk in submissions:
        chunk.sort(key=lambda x: x.created_utc)
        step = database.insert(chunk)
        message = form.format(
            lower=common.human(chunk[0].created_utc),
            upper=common.human(chunk[-1].created_utc),
            lower_unix=int(chunk[0].created_utc),
            upper_unix=int(chunk[-1].created_utc),
            gain=step['new_submissions'],
        )
        print(message)

    cur.execute('SELECT COUNT(idint) FROM submissions')
    itemcount = cur.fetchone()[0]

    print('Ended with %d items in %s' % (itemcount, database.filepath.basename))

def get_submissions_argparse(args):
    if args.lower == 'update':
        lower = 'update'
    else:
        lower = common.int_none(args.lower)

    return get_submissions(
        subreddit=args.subreddit,
        username=args.username,
        lower=lower,
        upper=common.int_none(args.upper),
        do_supplement=args.do_supplement,
    )
