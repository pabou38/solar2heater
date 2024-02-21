#!/usr/bin/python3

import logging

#logging.warning('warning')
# Be sure to try the following in a newly started Python interpreter, and don’t just continue from the session described above:

# WARNING: configure log file BEFORE any module which may import logging
logging.basicConfig(filename='test.log', format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8', level=logging.DEBUG)

logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')

logging.shutdown()

print('end')
