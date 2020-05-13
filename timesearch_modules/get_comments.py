import traceback

from . import common
from . import exceptions
from . import pushshift; print('Thank you Jason Baumgartner, owner of Pushshift.io!')
from . import tsdb


def get_comments(
        subreddit=None,
        username=None,
        specific_submission=None,
        do_supplement=True,
        lower=None,
        upper=None,
    ):
    if not specific_submission and not common.is_xor(subreddit, username):
        raise exceptions.NotExclusive(['subreddit', 'username'])
    if username and specific_submission:
        raise exceptions.NotExclusive(['username', 'specific_submission'])

    common.login()

    if specific_submission:
        (database, subreddit) = tsdb.TSDB.for_submission(specific_submission, do_create=True, fix_name=True)
        specific_submission = common.t3_prefix(specific_submission)[3:]
        specific_submission = common.r.submission(specific_submission)
        database.insert(specific_submission)

    elif subreddit:
        (database, subreddit) = tsdb.TSDB.for_subreddit(subreddit, do_create=True, fix_name=True)

    else:
        (database, username) = tsdb.TSDB.for_user(username, do_create=True, fix_name=True)

    cur = database.sql.cursor()

    if lower is None:
        lower = 0
    if lower == 'update':
        query_latest = 'SELECT created FROM comments ORDER BY created DESC LIMIT 1'
        if subreddit:
            # Instead of blindly taking the highest timestamp currently in the db,
            # we must consider the case that the user has previously done a
            # specific_submission scan and now wants to do a general scan, which
            # would trick the latest timestamp into missing anything before that
            # specific submission.
            query = '''
            SELECT created FROM comments WHERE NOT EXISTS (
                SELECT 1 FROM submissions
                WHERE submissions.idstr == comments.submission
                AND submissions.augmented_at IS NOT NULL
            )
            ORDER BY created DESC LIMIT 1
            '''
            unaugmented = cur.execute(query).fetchone()
            if unaugmented:
                lower = unaugmented[0] - 1
            else:
                latest = cur.execute(query_latest).fetchone()
                if latest:
                    lower = latest[0] - 1
        if username:
            latest = cur.execute(query_latest).fetchone()
            if latest:
                lower = latest[0] - 1
    if lower == 'update':
        lower = 0

    if specific_submission:
        comments = pushshift.get_comments_from_submission(specific_submission)
    elif subreddit:
        comments = pushshift.get_comments_from_subreddit(subreddit, lower=lower, upper=upper)
    elif username:
        comments = pushshift.get_comments_from_user(username, lower=lower, upper=upper)

    form = '{lower} ({lower_unix}) - {upper} ({upper_unix}) +{gain}'

    if do_supplement:
        comments = pushshift.supplement_reddit_data(comments, chunk_size=100)
    comments = common.generator_chunker(comments, 200)
    for chunk in comments:
        step = database.insert(chunk)
        message = form.format(
            lower=common.human(chunk[0].created_utc),
            upper=common.human(chunk[-1].created_utc),
            lower_unix=int(chunk[0].created_utc),
            upper_unix=int(chunk[-1].created_utc),
            gain=step['new_comments'],
        )
        print(message)
    if specific_submission:
        query = '''
            UPDATE submissions
            set augmented_at = ?
            WHERE idstr == ?
        '''
        bindings = [common.get_now(), specific_submission.fullname]
        cur.execute(query, bindings)
        database.sql.commit()

def get_comments_argparse(args):
    if args.verbose:
        common.log.setLevel(common.logging.DEBUG)

    return get_comments(
        subreddit=args.subreddit,
        username=args.username,
        #limit=common.int_none(args.limit),
        #threshold=common.int_none(args.threshold),
        #num_thresh=common.int_none(args.num_thresh),
        #verbose=args.verbose,
        specific_submission=args.specific_submission,
        do_supplement=args.do_supplement,
        lower=args.lower,
        upper=args.upper,
    )
