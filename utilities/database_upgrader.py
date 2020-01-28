import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from timesearch_modules import tsdb


def upgrade_1_to_2(db):
    '''
    In this version, many of the timesearch modules were renamed, including
    redmash -> index. This update will rename the existing `redmash` folder
    to `index`.
    '''
    cur = db.sql.cursor()
    redmash_dir = db.index_dir.parent.with_child('redmash')
    if redmash_dir.exists:
        if not redmash_dir.is_dir:
            raise Exception(f'{redmash_dir.absolute_path} is not a directory!')
        print('Renaming redmash folder to index.')
        os.rename(redmash_dir.absolute_path, db.index_dir.absolute_path)

def upgrade_all(database_filename):
    '''
    Given the filename of a database, apply all of the needed
    upgrade_x_to_y functions in order.
    '''
    db = tsdb.TSDB(database_filename, do_create=False, skip_version_check=True)

    cur = db.sql.cursor()

    cur.execute('PRAGMA user_version')
    current_version = cur.fetchone()[0]
    needed_version = tsdb.DATABASE_VERSION

    if current_version == needed_version:
        print('Already up to date with version %d.' % needed_version)
        return

    for version_number in range(current_version + 1, needed_version + 1):
        print('Upgrading from %d to %d' % (current_version, version_number))
        upgrade_function = 'upgrade_%d_to_%d' % (current_version, version_number)
        upgrade_function = eval(upgrade_function)
        upgrade_function(db)
        db.sql.cursor().execute('PRAGMA user_version = %d' % version_number)
        db.sql.commit()
        current_version = version_number
    print('Upgrades finished.')


def upgrade_all_argparse(args):
    return upgrade_all(database_filename=args.database_filename)

def main(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument('database_filename')
    parser.set_defaults(func=upgrade_all_argparse)

    args = parser.parse_args(argv)
    args.func(args)

if __name__ == '__main__':
    main(sys.argv[1:])
