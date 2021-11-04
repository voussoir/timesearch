import os
import markdown

from . import common
from . import exceptions
from . import tsdb


HTML_HEADER = '''
<html>
<head>
<title>{title}</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>

<style>
.submission, .comment
{{
    padding-left: 20px;
    padding-right: 4px;
}}
.comment
{{
    margin-top: 4px;
    margin-bottom: 4px;
    border: 1px solid black;
}}
.submission
{{
    border: 2px solid blue;
}}
.hidden
{{
    display: none;
}}
</style>
</head>
<body>
'''.strip()

HTML_FOOTER = '''
</body>

<script>
function toggle_collapse(comment_div)
{
    var button = comment_div.getElementsByClassName("toggle_hide_button")[0];
    var collapsible = comment_div.getElementsByClassName("collapsible")[0];
    if (collapsible.classList.contains("hidden"))
    {
        collapsible.classList.remove("hidden");
        button.innerText = "[-]";
    }
    else
    {
        collapsible.classList.add("hidden");
        button.innerText = "[+]";
    }
}
</script>
</html>
'''.strip()

HTML_COMMENT = '''
<div class="comment" id="{id}">
    <p class="userinfo">
        <a
        class="toggle_hide_button"
        href="javascript:void(0)"
        onclick="toggle_collapse(this.parentElement.parentElement)">[-]
        </a>
        {usernamelink}
        |
        <span class="score">{score} points</span>
        |
        <a class="timestamp" href="{permalink}">{human}</a>
    </p>
    <div class="collapsible">
        {body}
        {{children}}
    </div>
</div>
'''.strip()

HTML_SUBMISSION = '''
<div class="submission" id="{id}">
    <p class="userinfo">
        {usernamelink}
        |
        <span class="score">{score} points</span>
        |
        <a class="timestamp" href="{permalink}">{human}</a>
    </p>
    <strong>{title}</strong>
    <p>{url_or_text}</p>
</div>
{{children}}
'''.strip()


class TreeNode:
    def __init__(self, identifier, data, parent=None):
        assert isinstance(identifier, str)
        assert '\\' not in identifier
        self.identifier = identifier
        self.data = data
        self.parent = parent
        self.children = {}

    def __getitem__(self, key):
        return self.children[key]

    def __repr__(self):
        return 'TreeNode %s' % self.abspath()

    def abspath(self):
        node = self
        nodes = [node]
        while node.parent is not None:
            node = node.parent
            nodes.append(node)
        nodes.reverse()
        nodes = [node.identifier for node in nodes]
        return '\\'.join(nodes)

    def add_child(self, other_node, overwrite_parent=False):
        self.check_child_availability(other_node.identifier)
        if other_node.parent is not None and not overwrite_parent:
            raise ValueError('That node already has a parent. Try `overwrite_parent=True`')

        other_node.parent = self
        self.children[other_node.identifier] = other_node
        return other_node

    def check_child_availability(self, identifier):
        if ':' in identifier:
            raise Exception('Only roots may have a colon')
        if identifier in self.children:
            raise Exception('Node %s already has child %s' % (self.identifier, identifier))

    def detach(self):
        del self.parent.children[self.identifier]
        self.parent = None

    def listnodes(self, customsort=None):
        items = list(self.children.items())
        if customsort is None:
            items.sort(key=lambda x: x[0].lower())
        else:
            items.sort(key=customsort)
        return [item[1] for item in items]

    def merge_other(self, othertree, otherroot=None):
        newroot = None
        if ':' in othertree.identifier:
            if otherroot is None:
                raise Exception('Must specify a new name for the other tree\'s root')
            else:
                newroot = otherroot
        else:
            newroot = othertree.identifier
        othertree.identifier = newroot
        othertree.parent = self
        self.check_child_availability(newroot)
        self.children[newroot] = othertree

    def printtree(self, customsort=None):
        for node in self.walk(customsort):
            print(node.abspath())

    def walk(self, customsort=None):
        yield self
        for child in self.listnodes(customsort=customsort):
            #print(child)
            #print(child.listnodes())
            yield from child.walk(customsort=customsort)

def html_format_comment(comment):
    text = HTML_COMMENT.format(
        id=comment.idstr,
        body=sanitize_braces(render_markdown(comment.body)),
        usernamelink=html_helper_userlink(comment),
        score=comment.score,
        human=common.human(comment.created),
        permalink=html_helper_permalink(comment),
    )
    return text

def html_format_submission(submission):
    text = HTML_SUBMISSION.format(
        id=submission.idstr,
        title=sanitize_braces(submission.title),
        usernamelink=html_helper_userlink(submission),
        score=submission.score,
        human=common.human(submission.created),
        permalink=html_helper_permalink(submission),
        url_or_text=html_helper_urlortext(submission),
    )
    return text

def html_from_database(database, specific_submission=None):
    '''
    Given a timesearch database, produce html pages for each
    of the submissions it contains (or one particular submission fullname)
    '''
    if markdown is None:
        raise ImportError('Page cannot be rendered without the markdown module')

    submission_trees = trees_from_database(database, specific_submission)
    for submission_tree in submission_trees:
        page = html_from_tree(submission_tree, sort=lambda x: x.data.score * -1)
        database.offline_reading_dir.makedirs(exist_ok=True)

        html = ''

        header = HTML_HEADER.format(title=submission_tree.data.title)
        html += header

        html += page

        html += HTML_FOOTER
        yield (submission_tree.identifier, html)

def html_from_tree(tree, sort=None):
    '''
    Given a tree *whose root is the submission*, return
    HTML-formatted text representing each submission's comment page.
    '''
    if tree.data.object_type == 'submission':
        page = html_format_submission(tree.data)
    elif tree.data.object_type == 'comment':
        page = html_format_comment(tree.data)
    children = tree.listnodes()
    if sort is not None:
        children.sort(key=sort)
    children = [html_from_tree(child, sort) for child in children]
    if len(children) == 0:
        children = ''
    else:
        children = '\n\n'.join(children)
    try:
        page = page.format(children=children)
    except IndexError:
        print(page)
        raise
    return page

def html_helper_permalink(item):
    '''
    Given a submission or a comment, return the URL for its permalink.
    '''
    link = 'https://www.reddit.com/r/%s/comments/' % item.subreddit
    if item.object_type == 'submission':
        link += item.idstr[3:]
    elif item.object_type == 'comment':
        link += '%s/_/%s' % (item.submission[3:], item.idstr[3:])
    return link

def html_helper_urlortext(submission):
    '''
    Given a submission, return either an <a> tag for its url, or its
    markdown-rendered selftext.
    '''
    if submission.url:
        text = '<a href="{url}">{url}</a>'.format(url=submission.url)
    elif submission.selftext:
        text = render_markdown(submission.selftext)
    else:
        text = ''
    text = sanitize_braces(text)
    return text

def html_helper_userlink(item):
    '''
    Given a submission or comment, return an <a> tag for its author, or [deleted].
    '''
    name = item.author
    if name.lower() == '[deleted]':
        return '[deleted]'
    link = 'https://www.reddit.com/u/{name}'
    link = '<a href="%s">{name}</a>' % link
    link = link.format(name=name)
    return link

def render_markdown(text):
    # I was going to use html.escape, but then it turns html entities like
    # &nbsp; into &amp;nbsp; which doesn't work.
    # So I only want to escape the brackets.
    escaped = text.replace('<', '&lt;').replace('>', '&rt;')
    text = markdown.markdown(escaped, output_format='html5')
    return text

def sanitize_braces(text):
    text = text.replace('{', '{{')
    text = text.replace('}', '}}')
    return text

def trees_from_database(database, specific_submission=None):
    '''
    Given a timesearch database, take all of the submission
    ids, take all of the comments for each submission id, and run them
    through `tree_from_submission`.

    Yield each submission's tree as it is generated.
    '''
    cur1 = database.sql.cursor()
    cur2 = database.sql.cursor()

    if specific_submission is None:
        cur1.execute('SELECT idstr FROM submissions ORDER BY created ASC')
        submission_ids = common.fetchgenerator(cur1)
        # sql always returns rows as tuples, even when selecting one column.
        submission_ids = (x[0] for x in submission_ids)
    else:
        specific_submission = common.t3_prefix(specific_submission)
        submission_ids = [specific_submission]

    found_some_posts = False
    for submission_id in submission_ids:
        found_some_posts = True
        cur2.execute('SELECT * FROM submissions WHERE idstr == ?', [submission_id])
        submission = cur2.fetchone()
        cur2.execute('SELECT * FROM comments WHERE submission == ?', [submission_id])
        fetched_comments = cur2.fetchall()
        submission_tree = tree_from_submission(submission, fetched_comments)
        yield submission_tree

    if not found_some_posts:
        raise Exception('Found no submissions!')

def tree_from_submission(submission_dbrow, comments_dbrows):
    '''
    Given the sqlite data for a submission and all of its comments,
    return a tree with the submission id as the root
    '''
    submission = tsdb.DBEntry(submission_dbrow)
    comments = [tsdb.DBEntry(c) for c in comments_dbrows]
    comments.sort(key=lambda x: x.created)

    print('Building tree for %s (%d comments)' % (submission.idstr, len(comments)))
    # Thanks Martin Schmidt for the algorithm
    # http://stackoverflow.com/a/29942118/5430534
    tree = TreeNode(identifier=submission.idstr, data=submission)
    node_map = {}

    for comment in comments:
        # Ensure this comment is in a node of its own
        this_node = node_map.get(comment.idstr, None)
        if this_node:
            # This ID was detected as a parent of a previous iteration
            # Now we're actually filling it in.
            this_node.data = comment
        else:
            this_node = TreeNode(comment.idstr, comment)
            node_map[comment.idstr] = this_node

        # Attach this node to the parent.
        if comment.parent.startswith('t3_'):
            tree.add_child(this_node)
        else:
            parent_node = node_map.get(comment.parent, None)
            if not parent_node:
                parent_node = TreeNode(comment.parent, data=None)
                node_map[comment.parent] = parent_node
            parent_node.add_child(this_node)
            this_node.parent = parent_node
    return tree

def offline_reading(subreddit=None, username=None, specific_submission=None):
    if not specific_submission and not common.is_xor(subreddit, username):
        raise exceptions.NotExclusive(['subreddit', 'username'])

    if specific_submission and not username and not subreddit:
        database = tsdb.TSDB.for_submission(specific_submission, do_create=False)

    elif subreddit:
        database = tsdb.TSDB.for_subreddit(subreddit, do_create=False)

    else:
        database = tsdb.TSDB.for_user(username, do_create=False)

    htmls = html_from_database(database, specific_submission=specific_submission)

    for (id, html) in htmls:
        html_basename = '%s.html' % id
        html_filepath = database.offline_reading_dir.with_child(html_basename)
        html_handle = html_filepath.open('w', encoding='utf-8')
        html_handle.write(html)
        html_handle.close()
        print('Wrote', html_filepath.relative_path)

def offline_reading_argparse(args):
    return offline_reading(
        subreddit=args.subreddit,
        username=args.username,
        specific_submission=args.specific_submission,
    )
