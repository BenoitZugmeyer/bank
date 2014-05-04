import importlib
import datetime

from .adaptor import Adaptor
from .util import format_date, generate_dates, create_date
from .transaction import Transaction


class AdaptorNotFound(Exception):
    pass


def try_import_adaptor(name):
    try:
        return importlib.import_module(name)
    except ImportError as e:
        if e.msg != "No module named '{}'".format(name):
            raise


def find_adaptor_class(module):
    try:
        return next(cls
                    for cls in module.__dict__.values()
                    if isinstance(cls, type)
                    and cls is not Adaptor
                    and issubclass(cls, Adaptor))
    except StopIteration:
        pass


class Account(object):

    def __init__(self, app, id):
        assert isinstance(id, str), '`id` should be a string'

        self.id = id
        self.app = app
        self.adaptor = self.create_adaptor()

    @property
    def config(self):
        return self.app.config.accounts.get(self.id)

    @property
    def db(self):
        return self.app.db

    def create_adaptor(self):
        name = self.config.type
        if not name:
            raise AdaptorNotFound('no adaptor given for account {}'
                                  .format(self.id))

        main_package = __name__.partition('.')[0]

        name = name.lower()

        module = try_import_adaptor(name) or \
            try_import_adaptor(main_package + '.adaptors.' + name)

        if not module:
            raise AdaptorNotFound('module not found for adaptor {}'
                                  .format(name))

        cls = find_adaptor_class(module)

        if not cls:
            raise AdaptorNotFound('Adaptor class not found '
                                  'for adaptor {} in {}'
                                  .format(name, module))

        return cls(self)

    def __repr__(self):
        return 'Account(..., {id!r})'.format(**self.__dict__)

    @property
    def name(self):
        return self.config.name or self.id

    def get_balance(self, since=None):
        row = self.db.cursor().execute('''
            SELECT balance_amount - (
                SELECT TOTAL(amount)
                FROM "transaction"
                WHERE "transaction".account == "account".id
                  AND "transaction".date >= ?
            ) AS balance
            FROM "account"
            WHERE "account".id = ?
            ''', (format_date(since) if since else 0, self.id)).fetchone()

        if not row:
            return 0

        return row['balance']

    def iter_transactions_by_dates(self, since=None, delta=None, until=None):
        transactions = self.iter_transactions(since=since)
        next_transaction = next(transactions)
        for date in generate_dates(since or next_transaction.date,
                                   delta or datetime.timedelta(days=1)):

            if (until is None and next_transaction is None) or \
                    (until is not None and date >= until):
                break

            date_transactions = []

            if next_transaction:
                try:
                    while next_transaction.date <= date:
                        date_transactions.append(next_transaction)
                        next_transaction = next(transactions)
                except StopIteration:
                    next_transaction = None

            yield date, date_transactions

    def iter_transactions(self, since=None):
        query = '''
            SELECT date, id, type, amount, description
            FROM "transaction"
            WHERE account = ?
              AND date >= ?
            ORDER BY date
            '''

        for row in self.db.cursor().execute(
                query,
                (self.id, format_date(since) if since else 0)):
            yield Transaction(account=self, **row)

    def transaction_count(self):
        return self.db.cursor().execute('''
            SELECT COUNT(*)
            FROM "transaction"
            WHERE account = ?
        ''', (self.id,)).fetchone()[0]

    def update_balance(self):
        date, amount = self.adaptor.fetch_balance()
        self.db.cursor().execute('''
            INSERT OR REPLACE INTO "account"
              (id, balance_date, balance_amount)
            VALUES (?, ?, ?)
            ''', (self.id, format_date(date), amount))
        self.db.commit()

    def update_transactions(self):
        cursor = self.db.cursor()
        date_row = cursor.execute('SELECT "date" '
                                  'FROM "transaction" '
                                  'WHERE account = ? '
                                  'ORDER BY "date" DESC',
                                  (self.id,)).fetchone()

        date = create_date(date_row['date']) - datetime.timedelta(days=10) \
            if date_row else create_date('01-01-2013')

        cursor.executemany(
            'INSERT OR REPLACE INTO "transaction" '
            '  (hash, account, date, id, type, amount, description) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                (
                    transaction.hash,
                    transaction.account.id,
                    format_date(transaction.date),
                    transaction.id,
                    transaction.type,
                    transaction.amount,
                    transaction.description
                ) for transaction in self.adaptor.fetch_transactions(date)
            )
        )

        self.db.commit()
