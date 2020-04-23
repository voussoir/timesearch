'''
This is the main launch file for Timesearch.

When you run `python timesearch.py get_submissions -r subredditname` or any
other command, your arguments will first go to timesearch_modules\__init__.py,
then into timesearch_modules\get_submissions.py as appropriate for your command.
'''

import logging
handler = logging.StreamHandler()
log_format = '{levelname}:timesearch.{module}.{funcName}: {message}'
handler.setFormatter(logging.Formatter(log_format, style='{'))
logging.getLogger().addHandler(handler)

import sys
import timesearch_modules

status_code = timesearch_modules.main(sys.argv[1:])
raise SystemExit(status_code)
