"""SQLite primitives for immutable, temporary analysis results (no raw identifiers)."""
from contextlib import contextmanager
import csv
from io import StringIO
import sqlite3
import time


COLUMNS = 'row_number, prediction, probability'


def connect(path, *, readonly=False):
    connection = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rwc'),
                                 uri=True, check_same_thread=False)
    # Each connection has a bounded page cache; sorting must not materialize RAM
    # datasets. Matching indexes below avoid export/probability sort temp files.
    connection.execute('PRAGMA cache_size=-2048')
    connection.execute('PRAGMA mmap_size=0')
    connection.execute('PRAGMA temp_store=FILE')
    return connection


@contextmanager
def reading(path):
    connection = connect(path, readonly=True)
    try:
        yield connection
    finally:
        connection.close()


def initialize(connection, budget):
    page_size = connection.execute('PRAGMA page_size').fetchone()[0]
    # Bound database + rollback journal before any writes. Three times the DB
    # pages plus 64 KiB reserves conservative journal/header overhead. Failed
    # staging files are discarded; batches commit without publishing a session.
    pages = (budget - 65_536) // (3 * page_size)
    if pages < 4:
        raise sqlite3.OperationalError('database or disk is full')
    connection.execute(f'PRAGMA max_page_count={pages}')
    connection.execute('PRAGMA journal_mode=DELETE')
    connection.executescript('''
        CREATE TABLE flows (
            row_number INTEGER PRIMARY KEY,
            prediction INTEGER NOT NULL CHECK(prediction IN (0,1)),
            probability REAL NOT NULL CHECK(probability BETWEEN 0 AND 1),
            features TEXT NOT NULL
        );
        CREATE INDEX probability_asc ON flows(probability ASC, row_number ASC);
        CREATE INDEX probability_desc ON flows(probability DESC, row_number ASC);
        CREATE INDEX prediction_probability ON flows(prediction, probability);
    ''')


def prediction(row):
    return dict(row_number=row[0], prediction='DDoS' if row[1] else 'BENIGN', ddos_probability=row[2])


class ExportLease:
    """An owned read connection; closing releases retained-file quota exactly once."""
    def __init__(self, store, session):
        self.store, self.session = store, session
        self.connection = connect(session.path, readonly=True)
        self.cursor = self.connection.execute(f'SELECT {COLUMNS} FROM flows ORDER BY row_number')
        self.deadline = time.monotonic() + store.export_timeout
        self.closed = False

    def chunks(self):
        yield b'row_number,prediction,ddos_probability\n'
        while True:
            if time.monotonic() >= self.deadline:
                # Propagating an error aborts the HTTP stream; never signal a
                # successful truncated CSV on timeout or SQLite failure.
                raise TimeoutError('Analysis export deadline exceeded')
            rows = self.cursor.fetchmany(1000)
            if not rows:
                break
            output = StringIO(newline='')
            writer = csv.writer(output, lineterminator='\n')
            writer.writerows((row[0], 'DDoS' if row[1] else 'BENIGN', row[2]) for row in rows)
            yield output.getvalue().encode('utf-8')

    def close(self):
        with self.store.lock:
            if not self.closed:
                self.closed = True
                self.cursor.close()
                self.connection.close()
                self.store.exports.remove(self)
                self.store.reap(self.session)
