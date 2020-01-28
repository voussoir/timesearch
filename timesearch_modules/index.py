import datetime
import os

from . import common
from . import exceptions
from . import tsdb


LINE_FORMAT_TXT = '''
{timestamp}: [{title}]({link}) - /u/{author} (+{score})
'''.replace('\n', '')

LINE_FORMAT_HTML = '''
<div>{timestamp}: <a href="{link}">[{flairtext}] {title}</a> - <a href="{authorlink}">{author}</a> (+{score})</div>
'''.replace('\n', '')

TIMESTAMP_FORMAT = '%Y %b %d'
# The time format.
# "%Y %b %d" = "2016 August 10"
# See http://strftime.org/

HTML_HEADER = '''
<html>
<head>
<meta charset="UTF-8">
<style>
    *
    {
        font-family: Consolas;
    }
</style>
</head>

<body>
'''

HTML_FOOTER = '''
</body>
</html>
'''


def index(
        subreddit=None,
        username=None,
        do_all=False,
        do_date=False,
        do_title=False,
        do_score=False,
        do_author=False,
        do_subreddit=False,
        do_flair=False,
        html=False,
        offline=False,
        score_threshold=0,
    ):
    if not common.is_xor(subreddit, username):
        raise exceptions.NotExclusive(['subreddit', 'username'])

    if subreddit:
        database = tsdb.TSDB.for_subreddit(subreddit, do_create=False)
    else:
        database = tsdb.TSDB.for_user(username, do_create=False)

    kwargs = {'html': html, 'offline': offline, 'score_threshold': score_threshold}
    wrote = None

    if do_all or do_date:
        print('Writing time file')
        wrote = index_worker(database, suffix='_date', orderby='created ASC', **kwargs)

    if do_all or do_title:
        print('Writing title file')
        wrote = index_worker(database, suffix='_title', orderby='title ASC', **kwargs)

    if do_all or do_score:
        print('Writing score file')
        wrote = index_worker(database, suffix='_score', orderby='score DESC', **kwargs)

    if not username and (do_all or do_author):
        print('Writing author file')
        wrote = index_worker(database, suffix='_author', orderby='author ASC', **kwargs)

    if username and (do_all or do_subreddit):
        print('Writing subreddit file')
        wrote = index_worker(database, suffix='_subreddit', orderby='subreddit ASC', **kwargs)

    if do_all or do_flair:
        print('Writing flair file')
        # Items with flair come before items without. Each group is sorted by time separately.
        orderby = 'flair_text IS NULL ASC, created ASC'
        wrote = index_worker(database, suffix='_flair', orderby=orderby, **kwargs)

    if not wrote:
        raise Exception('No sorts selected! Read the docstring')
    print('Done.')

def index_worker(
        database,
        suffix,
        orderby,
        score_threshold=0,
        html=False,
        offline=False,
    ):
    cur = database.sql.cursor()
    statement = 'SELECT * FROM submissions WHERE score >= {threshold} ORDER BY {order}'
    statement = statement.format(threshold=score_threshold, order=orderby)
    cur.execute(statement)

    os.makedirs(database.index_dir.absolute_path, exist_ok=True)

    extension = '.html' if html else '.txt'
    mash_basename = database.filepath.replace_extension('').basename
    mash_basename += suffix + extension
    mash_filepath = database.index_dir.with_child(mash_basename)

    mash_handle = open(mash_filepath.absolute_path, 'w', encoding='UTF-8')
    if html:
        mash_handle.write(HTML_HEADER)
        line_format = LINE_FORMAT_HTML
    else:
        line_format = LINE_FORMAT_TXT

    do_timestamp = '{timestamp}' in line_format

    for submission in common.fetchgenerator(cur):
        submission = tsdb.DBEntry(submission)

        if do_timestamp:
            timestamp = int(submission.created)
            timestamp = datetime.datetime.utcfromtimestamp(timestamp)
            timestamp = timestamp.strftime(TIMESTAMP_FORMAT)
        else:
            timestamp = ''

        if offline:
            link = f'../offline_reading/{submission.idstr}.html'
        else:
            link = f'https://redd.it/{submission.idstr[3:]}'

        author = submission.author
        if author.lower() == '[deleted]':
            author_link = '#'
        else:
            author_link = 'https://reddit.com/u/%s' % author

        line = line_format.format(
            author=author,
            authorlink=author_link,
            flaircss=submission.flair_css_class or '',
            flairtext=submission.flair_text or '',
            id=submission.idstr,
            numcomments=submission.num_comments,
            score=submission.score,
            link=link,
            subreddit=submission.subreddit,
            timestamp=timestamp,
            title=submission.title.replace('\n', ' '),
            url=submission.url or link,
        )
        line += '\n'
        mash_handle.write(line)

    if html:
        mash_handle.write(HTML_FOOTER)
    mash_handle.close()
    print('Wrote', mash_filepath.relative_path)
    return mash_filepath

def index_argparse(args):
    return index(
        subreddit=args.subreddit,
        username=args.username,
        do_all=args.do_all,
        do_date=args.do_date,
        do_title=args.do_title,
        do_score=args.do_score,
        do_author=args.do_author,
        do_subreddit=args.do_subreddit,
        do_flair=args.do_flair,
        html=args.html,
        offline=args.offline,
        score_threshold=common.int_none(args.score_threshold),
    )
