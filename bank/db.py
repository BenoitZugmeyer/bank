import sqlite3


class DB(object):

    _connection = None

    def __init__(self, path):
        self.path = path

    def __del__(self):
        if self._connection:
            self._connection.close()

    def _create_db(self):

        self.cursor().executescript(r'''
            CREATE TABLE "transaction" (
                hash TEXT PRIMARY KEY,
                account TEXT,
                date TEXT,
                id INTEGER,
                type TEXT,
                amount REAL,
                description TEXT
            );

            CREATE TABLE "account" (
                id TEXT PRIMARY KEY,
                balance_date TEXT,
                balance_amount REAL
            );

            CREATE VIRTUAL TABLE "transaction_search" USING fts4(
                account,
                type,
                description
            );

            CREATE TRIGGER IF NOT EXISTS insert_transaction_trigger
            AFTER INSERT ON "transaction"
            BEGIN
                INSERT OR IGNORE INTO "transaction_search" (
                    docid,
                    account,
                    type,
                    description
                )
                VALUES (
                    NEW.hash,
                    NEW.account,
                    NEW.type,
                    NEW.description
                );
            END;
        ''')

    @property
    def connection(self):
        if self._connection:
            return self._connection

        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        self._connection = connection

        count = self.cursor().execute('''
            SELECT count(*) AS count
            FROM sqlite_master WHERE type='table'
        ''').fetchone()['count']

        if not count:
            self._create_db()

        return connection

    def cursor(self):
        return self.connection.cursor()

    def commit(self):
        return self.connection.commit()
