import sys
import time
import textwrap
import itertools


class TableFormatterWorker(object):

    vertical_separator = '|'
    horizontal_separator = '-'

    def __init__(self, columns, data, output):
        self.columns = columns
        self.data_iterator = iter(data)
        self.output = output
        self._first_rows = ()

    def _compute_widths(self):
        if all(c.get('width') for c in self.columns):
            return

        start_time = time.time()
        rows = []
        for index, row in enumerate(self.data_iterator):
            rows.append(row)
            if index > 3 or time.time() > start_time + 1:
                break

        for index, column in enumerate(self.columns):
            if column.get('width'):
                continue

            if rows:
                column['width'] = max(len(str(row[index]))
                                      for row in rows)
            else:
                column['width'] = 10

        self._first_rows = rows

    def _iter_data_rows(self):
        yield from iter(self._first_rows)
        yield from self.data_iterator

    @property
    def total_width(self):
        return len(self.columns) * 3 + 1 + sum(c['width']
                                               for c in self.columns)

    def write(self, str):
        self.output.write(str)

    def write_line(self):
        self.write(self.total_width * '-')
        self.write('\n')

    def write_row(self, values, header=False):
        wraped_values = []
        for column, value in zip(self.columns, values):
            width = column['width']
            value = str(value)
            if len(value) > width:
                wraped_values.append(textwrap.wrap(value, width=width))
            else:
                wraped_values.append((value,))

        for line in itertools.zip_longest(*wraped_values):
            self.write('|')
            for column, cell in zip(self.columns, line):
                align = column.get('align_header' if header else 'align', '^')
                self.write(' {:{}{}} |'.format(cell or '',
                                               align,
                                               column['width']))
            self.write('\n')

    def write_header(self):
        self.write_line()
        self.write_row((column['label'] for column in self.columns), True)
        self.write_line()

    def run(self):
        self._compute_widths()

        index = None
        for index, data_row in enumerate(self._iter_data_rows()):
            if index % 20 == 0:
                self.write_header()
            self.write_row(data_row)

        if index is not None:
            self.write_line()
        else:
            self.no_data()

    def no_data(self):
        self.write('no data\n')


class TableFormatter(object):

    def __init__(self, columns=(), data=(), output=sys.stdout):
        self._columns = []
        self.data = data
        self.output = output

        for column in columns:
            self.add_column(**column)

    def add_column(self, label=None, **kwargs):

        if label is None:
            label = str(len(self._columns) + 1)

        kwargs['label'] = label

        self._columns.append(kwargs)

    def dumps(self, data=None, output=None):
        TableFormatterWorker(self._columns,
                             data or self.data,
                             output or self.output).run()

    def print(self, data=None):
        self.dumps(data, sys.stdout)

if __name__ == '__main__':
    def gen():
        count = 100000
        while True:
            time.sleep(.4)
            count += 1
            yield (count, 2, 'blah')

    formatter = TableFormatter()

    formatter.add_column('bl')
    formatter.add_column('bli bl', width=4)
    formatter.add_column('blihi bl', width=4)

    formatter.data = gen()

    formatter.print()
