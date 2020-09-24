import os

from . import common
from . import tsdb


def get_wiki(subreddit):
    (database, subreddit) = tsdb.TSDB.for_subreddit(subreddit, fix_name=True)

    print('Getting wiki pages for /r/%s' % subreddit)
    subreddit = common.r.subreddit(subreddit)

    for wikipage in subreddit.wiki:
        if wikipage.name == 'config/stylesheet':
            continue

        wikipage_path = database.wiki_dir.join(wikipage.name).replace_extension('md')
        wikipage_path.parent.makedirs(exist_ok=True)
        with wikipage_path.open('w', encoding='utf-8') as handle:
            handle.write(wikipage.content_md)
        print('Wrote', wikipage_path.relative_path)

def get_wiki_argparse(args):
    return get_wiki(args.subreddit)
