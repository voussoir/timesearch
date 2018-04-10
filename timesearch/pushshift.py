'''
On January 29, 2018, reddit announced the death of the ?timestamp cloudsearch
parameter for submissions. RIP.
https://www.reddit.com/r/changelog/comments/7tus5f/update_to_search_api/dtfcdn0

This module interfaces with api.pushshift.io to restore this functionality.
It also provides new features previously impossible through reddit alone, such
as scanning all of a user's comments.
'''
import html
import requests
import time

from . import common

from voussoirkit import ratelimiter


USERAGENT = 'Timesearch ({version}) ({contact})'
API_URL = 'https://api.pushshift.io/reddit/'

DEFAULT_PARAMS = {
    'size': 1000,
    'sort': 'asc',
    'sort_type': 'created_utc',
}

# Pushshift does not supply attributes that are null. So we fill them back in.
FALLBACK_ATTRIBUTES = {
    'distinguished': None,
    'edited': False,
    'link_flair_css_class': None,
    'link_flair_text': None,
    'score': 0,
    'selftext': '',
}

contact_info_message = '''
Please add a CONTACT_INFO string variable to your bot.py file.
This will be added to your pushshift useragent.
'''.strip()
if not getattr(common.bot, 'CONTACT_INFO', ''):
    raise ValueError(contact_info_message)

useragent = USERAGENT.format(version=common.VERSION, contact=common.bot.CONTACT_INFO)
ratelimit = ratelimiter.Ratelimiter(allowance=60, period=60)
session = requests.Session()
session.headers.update({'User-Agent': useragent})


class DummyObject:
    '''
    These classes are used to convert the JSON data we get from pushshift into
    objects so that the rest of timesearch can operate transparently.
    This requires a bit of whack-a-mole including:
    - Fleshing out the attributes which PS did not include because they were
        null (we use FALLBACK_ATTRIBUTES to replace them).
    - Providing the convenience methods and @properties that PRAW provides.
    - Mimicking the rich attributes like author and subreddit.
    '''
    def __init__(self, **attributes):
        for (key, val) in attributes.items():
            if key == 'author':
                val = DummyObject(name=val)
            elif key == 'subreddit':
                val = DummyObject(display_name=val)
            elif key in ['body', 'selftext']:
                val = html.unescape(val)

            setattr(self, key, val)

        for (key, val) in FALLBACK_ATTRIBUTES.items():
            if not hasattr(self, key):
                setattr(self, key, val)
# This seems to occur in rare cases such as promo posts.
FALLBACK_ATTRIBUTES['subreddit'] = DummyObject(display_name=None)

class DummySubmission(DummyObject):
    @property
    def fullname(self):
        return 't3_' + self.id

class DummyComment(DummyObject):
    @property
    def fullname(self):
        return 't1_' + self.id


def _normalize_subreddit(subreddit):
    if isinstance(subreddit, str):
        return subreddit
    else:
        return subreddit.display_name

def _normalize_user(user):
    if isinstance(user, str):
        return user
    else:
        return user.name

def _pagination_core(url, params, dummy_type, lower=None, upper=None):
    if upper is not None:
        params['before'] = upper
    if lower is not None:
        params['after'] = lower

    setify = lambda items: set(item['id'] for item in items)
    prev_batch_ids = set()
    while True:
        batch = get(url, params)
        batch_ids = setify(batch)
        if len(batch_ids) == 0 or batch_ids.issubset(prev_batch_ids):
            break
        submissions = [dummy_type(**x) for x in batch if x['id'] not in prev_batch_ids]
        submissions.sort(key=lambda x: x.created_utc)
        # Take the latest-1 to avoid the lightning strike chance that two posts
        # have the same timestamp and this occurs at a page boundary.
        # Since ?after=latest would cause us to miss that second one.
        params['after'] = submissions[-1].created_utc - 1
        yield from submissions

        prev_batch_ids = batch_ids
        ratelimit.limit()

def get(url, params=None):
    if not url.startswith('https://'):
        url = API_URL + url.lstrip('/')

    if params is None:
        params = {}

    for (key, val) in DEFAULT_PARAMS.items():
        params.setdefault(key, val)

    common.log.debug('Requesting %s with %s', url, params)
    response = session.get(url, params=params)
    response.raise_for_status()
    response = response.json()
    data = response['data']
    return data

def get_comments_from_submission(submission):
    if isinstance(submission, str):
        submission_id = common.t3_prefix(submission)[3:]
    else:
        submission_id = submission.id

    params = {'link_id': submission_id}
    comments = _pagination_core(
        url='comment/search/',
        params=params,
        dummy_type=DummyComment,
    )
    yield from comments

def get_comments_from_subreddit(subreddit, **kwargs):
    subreddit = _normalize_subreddit(subreddit)
    params = {'subreddit': subreddit}
    comments = _pagination_core(
        url='comment/search/',
        params=params,
        dummy_type=DummyComment,
        **kwargs
    )
    yield from comments

def get_comments_from_user(user, **kwargs):
    user = _normalize_user(user)
    params = {'author': user}
    comments = _pagination_core(
        url='comment/search/',
        params=params,
        dummy_type=DummyComment,
        **kwargs
    )
    yield from comments

def get_submissions_from_subreddit(subreddit, **kwargs):
    subreddit = _normalize_subreddit(subreddit)
    params = {'subreddit': subreddit}
    submissions = _pagination_core(
        url='submission/search/',
        params=params,
        dummy_type=DummySubmission,
        **kwargs
    )
    yield from submissions

def get_submissions_from_user(user, **kwargs):
    user = _normalize_user(user)
    params = {'author': user}
    submissions = _pagination_core(
        url='submission/search/',
        params=params,
        dummy_type=DummySubmission,
        **kwargs
    )
    yield from submissions

def supplement_reddit_data(dummies, chunk_size=100):
    '''
    Given an iterable of the Dummy Pushshift objects, yield them back and also
    yield the live Reddit objects they refer to according to reddit's /api/info.
    The live object will always come after the corresponding dummy object.
    By doing this, we enjoy the strengths of both data sources: Pushshift
    will give us deleted or removed objects that reddit would not, and reddit
    gives us up-to-date scores and text bodies.
    '''
    chunks = common.generator_chunker(dummies, chunk_size)
    for chunk in chunks:
        ids = [item.fullname for item in chunk]
        live_copies = list(common.r.info(ids))
        live_copies = {item.fullname: item for item in live_copies}
        for item in chunk:
            yield item
            live_item = live_copies.get(item.fullname, None)
            if live_item:
                yield live_item
