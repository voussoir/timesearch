import copy
import prawcore
import time
import traceback

from . import common
from . import exceptions
from . import tsdb


def _listify(x):
    '''
    The user may have given us a string containing multiple subreddits / users.
    Try to split that up into a list of names.
    '''
    if not x:
        return []
    if isinstance(x, str):
        return common.split_any(x, ['+', ' ', ','])
    return x

def generator_printer(generator):
    '''
    Given a generator that produces livestream update steps, print them out.
    This yields None because print returns None.
    '''
    prev_message_length = 0
    for step in generator:
        newtext = '%s: +%ds, %dc' % (step['tsdb'].filepath.basename, step['new_submissions'], step['new_comments'])
        totalnew = step['new_submissions'] + step['new_comments']
        status = '{now} {new}'.format(now=common.human(common.get_now()), new=newtext)
        clear_prev = (' ' * prev_message_length) + '\r'
        print(clear_prev + status, end='')
        prev_message_length = len(status)
        if totalnew == 0 and common.log.level != common.logging.DEBUG:
            # Since there were no news, allow the next line to overwrite status
            print('\r', end='', flush=True)
        else:
            print()
        yield None

def cycle_generators(generators, only_once, sleepy):
    '''
    Given multiple generators, yield an item from each one, cycling through
    them in a round-robin fashion.

    This is useful if you want to convert multiple livestream generators into a
    single generator that take turns updating each of them and yields all of
    their items.
    '''
    while True:
        for generator in generators:
            yield next(generator)
        if only_once:
            break
        time.sleep(sleepy)

def livestream(
        subreddit=None,
        username=None,
        as_a_generator=False,
        do_submissions=True,
        do_comments=True,
        limit=100,
        only_once=False,
        sleepy=30,
    ):
    '''
    Continuously get posts from this source and insert them into the database.

    as_a_generator:
        Return a generator where every iteration does a single livestream loop
        and yields the return value of TSDB.insert (A summary of new
        submission & comment count).
        This is useful if you want to manage the generator yourself.
        Otherwise, this function will run the generator forever.
    '''
    subreddits = _listify(subreddit)
    usernames = _listify(username)
    kwargs = {
        'do_submissions': do_submissions,
        'do_comments': do_comments,
        'limit': limit,
        'params': {'show': 'all'},
    }

    subreddit_generators = [
        _livestream_as_a_generator(subreddit=subreddit, username=None, **kwargs) for subreddit in subreddits
    ]
    user_generators = [
        _livestream_as_a_generator(subreddit=None, username=username, **kwargs) for username in usernames
    ]
    generators = subreddit_generators + user_generators

    if as_a_generator:
        if len(generators) == 1:
            return generators[0]
        return generators

    generator = cycle_generators(generators, only_once=only_once, sleepy=sleepy)
    generator = generator_printer(generator)

    try:
        for step in generator:
            pass
    except KeyboardInterrupt:
        print()
        return

hangman = lambda: livestream(
    username='gallowboob',
    do_submissions=True,
    do_comments=True,
    sleepy=60,
)

def _livestream_as_a_generator(
        subreddit,
        username,
        do_submissions,
        do_comments,
        limit,
        params,
    ):

    if not common.is_xor(subreddit, username):
        raise exceptions.NotExclusive(['subreddit', 'username'])

    if not any([do_submissions, do_comments]):
        raise TypeError('Required do_submissions and/or do_comments parameter')
    common.login()

    if subreddit:
        common.log.debug('Getting subreddit %s', subreddit)
        (database, subreddit) = tsdb.TSDB.for_subreddit(subreddit, fix_name=True)
        subreddit = common.r.subreddit(subreddit)
        submission_function = subreddit.new if do_submissions else None
        comment_function = subreddit.comments if do_comments else None
    else:
        common.log.debug('Getting redditor %s', username)
        (database, username) = tsdb.TSDB.for_user(username, fix_name=True)
        user = common.r.redditor(username)
        submission_function = user.submissions.new if do_submissions else None
        comment_function = user.comments.new if do_comments else None

    while True:
        try:
            items = _livestream_helper(
                submission_function=submission_function,
                comment_function=comment_function,
                limit=limit,
                params=params,
            )
            newitems = database.insert(items)
            yield newitems
        except prawcore.exceptions.NotFound:
            print(database.filepath.basename, '404 not found')
            step = {'tsdb': database, 'new_comments': 0, 'new_submissions': 0}
            yield step
        except Exception:
            traceback.print_exc()
            print('Retrying...')
            step = {'tsdb': database, 'new_comments': 0, 'new_submissions': 0}
            yield step

def _livestream_helper(
        submission_function=None,
        comment_function=None,
        *args,
        **kwargs,
    ):
    '''
    Given a submission-retrieving function and/or a comment-retrieving function,
    collect submissions and comments in a list together and return that.

    args and kwargs go into the collecting functions.
    '''
    if not any([submission_function, comment_function]):
        raise TypeError('Required submissions and/or comments parameter')
    results = []

    if submission_function:
        common.log.debug('Getting submissions %s %s', args, kwargs)
        this_kwargs = copy.deepcopy(kwargs)
        submission_batch = submission_function(*args, **this_kwargs)
        results.extend(submission_batch)
    if comment_function:
        common.log.debug('Getting comments %s %s', args, kwargs)
        this_kwargs = copy.deepcopy(kwargs)
        comment_batch = comment_function(*args, **this_kwargs)
        results.extend(comment_batch)
    common.log.debug('Got %d posts', len(results))
    return results

def livestream_argparse(args):
    if args.submissions is args.comments is False:
        args.submissions = True
        args.comments = True
    if args.limit is None:
        limit = 100
    else:
        limit = int(args.limit)

    return livestream(
        subreddit=args.subreddit,
        username=args.username,
        do_comments=args.comments,
        do_submissions=args.submissions,
        limit=limit,
        only_once=args.once,
        sleepy=int(args.sleepy),
    )
