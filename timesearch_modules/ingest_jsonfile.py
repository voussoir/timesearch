import json
import time
import traceback

from voussoirkit import pathclass

from . import common
from . import exceptions
from . import pushshift
from . import tsdb

def is_submission(obj):
    return (
        obj.get('name', '').startswith('t3_')
        or obj.get('over_18') is not None
    )

def is_comment(obj):
    return (
        obj.get('name', '').startswith('t1_')
        or obj.get('parent_id', '').startswith('t3_')
        or obj.get('link_id', '').startswith('t3_')
    )

def jsonfile_to_objects(filepath):
    filepath = pathclass.Path(filepath)
    filepath.assert_is_file()

    with filepath.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                break
            obj = json.loads(line)
            if is_submission(obj):
                yield pushshift.DummySubmission(**obj)
            elif is_comment(obj):
                yield pushshift.DummyComment(**obj)
            else:
                raise ValueError(f'Could not recognize object type {obj}.')

def ingest_jsonfile(
        filepath,
        subreddit=None,
        username=None,
    ):
    if not common.is_xor(subreddit, username):
        raise exceptions.NotExclusive(['subreddit', 'username'])

    if subreddit:
        (database, subreddit) = tsdb.TSDB.for_subreddit(subreddit, fix_name=True)
    elif username:
        (database, username) = tsdb.TSDB.for_user(username, fix_name=True)
    cur = database.sql.cursor()

    objects = jsonfile_to_objects(filepath)
    database.insert(objects)

    cur.execute('SELECT COUNT(idint) FROM submissions')
    submissioncount = cur.fetchone()[0]
    cur.execute('SELECT COUNT(idint) FROM comments')
    commentcount = cur.fetchone()[0]

    print('Ended with %d submissions and %d comments in %s' % (submissioncount, commentcount, database.filepath.basename))

def ingest_jsonfile_argparse(args):
    return ingest_jsonfile(
        subreddit=args.subreddit,
        username=args.username,
        filepath=args.json_file,
    )
