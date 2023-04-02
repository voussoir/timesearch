import os
import markdown

from . import common
from . import tsdb


def get_wiki(subreddit):
    (database, subreddit) = tsdb.TSDB.for_subreddit(subreddit, fix_name=True)

    print('Getting wiki pages for /r/%s' % subreddit)
    subreddit = common.r.subreddit(subreddit)

    for wikipage in subreddit.wiki:
        if wikipage.name == 'config/stylesheet':
            continue

        wikipage_path = database.wiki_dir.join(wikipage.name).add_extension('md')
        wikipage_path.parent.makedirs(exist_ok=True)
        wikipage_path.write('w', wikipage.content_md, encoding='utf-8')
        print('Wrote', wikipage_path.relative_path)

        html_path = wikipage_path.replace_extension('html')
        escaped = wikipage.content_md.replace('<', '&lt;').replace('>', '&rt;')
        html_path.write('w', markdown.markdown(escaped, output_format='html5'), encoding='utf-8')
        print('Wrote', html_path.relative_path)

def get_wiki_argparse(args):
    return get_wiki(args.subreddit)
