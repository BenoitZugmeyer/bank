import hashlib
import re
import logging

from .util import create_date, format_date

logger = logging.getLogger(__name__)


class Transaction():

    def __init__(self, account, date, id, type, amount, description):
        self.account = account
        self.id = int(id)
        self.type = type.strip().lower()
        self.amount = float(amount)
        self.date = create_date(date)
        self.description = re.sub(r'\s+', ' ', description.strip()) \
            .capitalize()

    @property
    def hash(self):
        chunk = b'-'.join(
            bytes(str(i), encoding='utf-8') for i in (
                self.account.id,
                self.id,
                self.type,
                self.amount,
                format_date(self.date),
                self.description
            )
        )
        sha1 = hashlib.sha1(chunk).hexdigest()
        # sqlite indexes are on signed 8-bytes integer
        return int(sha1, 16) % 2 ** 63

    def __repr__(self):
        return 'Transaction({account!r}, {date!r}, {id!r}, {type!r}, {amount!r}, '\
            '{description!r})'.format(**self.__dict__)


def tsv_parser(account, lines):
    for line in lines:
        if not line.strip():
            continue
        args = line.split('\t')
        if len(args) != 5:
            logger.warning('Bad line:', line)
            continue
        yield Transaction(account, *args)
