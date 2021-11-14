import datetime
import logging
import os
import time
import traceback

from voussoirkit import vlogging

VERSION = '2020.09.06.0'

try:
    import praw
except ImportError:
    praw = None
if praw is None or praw.__version__.startswith('3.'):
    import praw4
    praw = praw4

try:
    import bot
except ImportError:
    bot = None
if bot is None or bot.praw != praw:
    try:
        import bot4
        bot = bot4
    except ImportError:
        message = '\n'.join([
        'Could not find your PRAW4 bot file as either `bot.py` or `bot4.py`.',
        'Please see the README.md file for instructions on how to prepare it.'
        ])
        raise ImportError(message)


log = vlogging.get_logger(__name__)

r = bot.anonymous()

def assert_file_exists(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

def b36(i):
    if isinstance(i, int):
        return base36encode(i)
    return base36decode(i)

def base36decode(number):
    return int(number, 36)

def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int)):
        raise TypeError('number must be an integer')
    base36 = ''
    sign = ''
    if number < 0:
        sign = '-'
        number = -number
    if 0 <= number < len(alphabet):
        return sign + alphabet[number]
    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36
    return sign + base36

def fetchgenerator(cursor):
    while True:
        item = cursor.fetchone()
        if item is None:
            break
        yield item

def generator_chunker(generator, chunk_size):
    '''
    Given an item generator, yield lists of length chunk_size, except maybe
    the last one.
    '''
    chunk = []
    for item in generator:
        chunk.append(item)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    if len(chunk) != 0:
        yield chunk

def get_now(stamp=True):
    now = datetime.datetime.now(datetime.timezone.utc)
    if stamp:
        return int(now.timestamp())
    return now

def human(timestamp):
    x = datetime.datetime.utcfromtimestamp(timestamp)
    x = datetime.datetime.strftime(x, "%b %d %Y %H:%M:%S")
    return x

def int_none(x):
    if x is None:
        return None
    return int(x)

def is_xor(*args):
    '''
    Return True if and only if one arg is truthy.
    '''
    return [bool(a) for a in args].count(True) == 1

def login():
    global r
    log.debug('Logging in to reddit.')
    r = bot.login(r)

def nofailrequest(function):
    '''
    Creates a function that will retry until it succeeds.
    This function accepts 1 parameter, a function, and returns a modified
    version of that function that will try-catch, sleep, and loop until it
    finally returns.
    '''
    def a(*args, **kwargs):
        while True:
            try:
                result = function(*args, **kwargs)
                return result
            except KeyboardInterrupt:
                raise
            except Exception:
                traceback.print_exc()
                print('Retrying in 2...')
                time.sleep(2)
    return a

def split_any(text, delimiters):
    delimiters = list(delimiters)
    (splitter, replacers) = (delimiters[0], delimiters[1:])
    for replacer in replacers:
        text = text.replace(replacer, splitter)
    return text.split(splitter)

def subreddit_for_submission(submission_id):
    submission_id = t3_prefix(submission_id)[3:]
    submission = r.submission(submission_id)
    return submission.subreddit

def t3_prefix(submission_id):
    if not submission_id.startswith('t3_'):
        submission_id = 't3_' + submission_id
    return submission_id
