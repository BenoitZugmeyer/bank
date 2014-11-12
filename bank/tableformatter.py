import re
import sys
import time
import textwrap
import itertools
import io


def rindex(list, needle):
    return next(index
                for index, value in reversed(tuple(enumerate(list)))
                if value == needle)


class Column(object):

    def __init__(self,
                 label,
                 align='<',
                 align_header='^',
                 left_margin=1,
                 right_margin=1):

        self.label = str(label)
        self.align = align
        self.left_margin = left_margin
        self.right_margin = right_margin
        self.align_header = align_header

    def format(self, data):
        return str(data)


class TableFormatterWorker(object):

    def __init__(self, formatter, data, output):
        self.formatter = formatter
        self.columns = formatter._columns
        self.data_iterator = iter(data)
        self.output = output
        self._lines_written = 0
        self._first_rows = ()
        self._column_widths = ()

    def _compute_widths(self):
        rows = self._collect_rows_for_width()

        def iter_values(column_index):
            column = self.columns[column_index]
            yield column.label
            yield from (column.format(row[column_index]) for row in rows)

        largest_widths, acceptable_widths = \
            zip(*(self._compute_width(iter_values(index))
                  for index in range(len(self.columns))))

        width_bound = self.formatter.width or self.formatter.max_width
        if width_bound:

            expected_width = width_bound - self._compute_extra_width()

            if self.formatter.max_width and \
                    sum(largest_widths) <= expected_width:
                widths = largest_widths
            else:
                widths = self._adjust_widths(expected_width,
                                             acceptable_widths, largest_widths)

        else:
            widths = largest_widths

        self._column_widths = widths
        self._first_rows = rows

    def _adjust_widths(self, expected_width, acceptable_widths,
                       largest_widths):

        largest_width_total = sum(largest_widths)
        acceptable_width_total = sum(acceptable_widths)

        if acceptable_width_total < expected_width < largest_width_total:
            ratio = (expected_width - acceptable_width_total) / \
                (largest_width_total - acceptable_width_total)
            widths = (
                aw + (lw - aw) * ratio
                for aw, lw in zip(acceptable_widths, largest_widths))
        elif expected_width <= acceptable_width_total:
            ratio = expected_width / acceptable_width_total
            widths = (w * ratio for w in acceptable_widths)
        else:
            ratio = expected_width / largest_width_total
            widths = (w * ratio for w in largest_widths)

        widths = [max(int(w), 1) for w in widths]
        min_width_index = rindex(widths, min(widths))
        widths[min_width_index] = max(
            widths[min_width_index] + expected_width - sum(widths),
            1)

        return widths

    def _compute_width(self, strings):
        max_width = 0
        max_acceptable_width = 0
        word_re = re.compile(r'\s+')
        for s in strings:
            width = len(s)
            if width > max_width:
                max_width = width

            words = word_re.split(s)
            acceptable_width = min(
                max(len(word) for word in words) + len(words) - 1,
                width)
            if acceptable_width > max_acceptable_width:
                max_acceptable_width = acceptable_width

        return max_width, max_acceptable_width

    def _collect_rows_for_width(self):
        time_limit = time.time() + self.formatter.width_computation_time_limit
        count = self.formatter.width_computation_count

        rows = []
        for index, row in enumerate(self.data_iterator):
            rows.append(row)
            if index > count or time.time() > time_limit:
                break

        return rows

    def _iter_data_rows(self):
        yield from iter(self._first_rows)
        yield from self.data_iterator

    def _compute_extra_width(self):
        return sum(c.left_margin + c.right_margin for c in self.columns) +\
            len(self.formatter.vertical_separator) * (len(self.columns) - 1) +\
            len(self.formatter.external_vertical_separator) * 2

    def write(self, str):
        self._lines_written += str.count('\n')
        self.output.write(str)

    def write_line(self):
        width = self._compute_extra_width() + sum(self._column_widths)
        self.write(width * '-')
        self.write('\n')

    def write_row(self, values, header=False):
        wraped_values = []
        for (index, column), value in zip(enumerate(self.columns), values):
            width = self._column_widths[index]
            value = str(value)
            if len(value) > width:
                wraped_values.append(textwrap.wrap(value, width=width))
            else:
                wraped_values.append((value,))

        for line in itertools.zip_longest(*wraped_values):
            first = True
            for (index, column), cell in zip(enumerate(self.columns), line):
                if first:
                    first = False
                    self.write(self.formatter.external_vertical_separator)
                else:
                    self.write(self.formatter.vertical_separator)

                align = column.align_header if header else column.align

                self.write('{}{:{}{}}{}'.format(
                    column.left_margin * ' ',
                    cell or '',
                    align,
                    self._column_widths[index],
                    column.right_margin * ' '))

            self.write(self.formatter.external_vertical_separator)
            self.write('\n')

    def write_header(self):
        self.write_line()
        self.write_row((column.label for column in self.columns), True)
        self.write_line()

    def run(self):
        self._compute_widths()
        height = self.formatter.height
        last_header_index = 0

        index = None
        for index, data_row in enumerate(self._iter_data_rows()):
            if (height and self._lines_written > last_header_index + height) or \
                    self._lines_written == 0:
                last_header_index = self._lines_written
                self.write_header()

            self.write_row(data_row)

        if index is not None:
            self.write_line()
        else:
            self.no_data()

    def no_data(self):
        self.write('no data\n')


class TableFormatter(object):

    vertical_separator = '|'
    external_vertical_separator = '|'
    horizontal_separator = '-'
    width = None
    max_width = None
    height = None
    width_computation_count = 100
    width_computation_time_limit = .2

    def __init__(self):
        self._columns = []

    def add_column(self, label=None, **kwargs):

        if label is None:
            label = str(len(self._columns) + 1)

        kwargs['label'] = label

        self._columns.append(Column(**kwargs))

    def write(self, data=None, output=sys.stdout):
        TableFormatterWorker(self, data, output).run()

    def dumps(self, data=None):
        output = io.StringIO()
        self.write(data, output)
        return output.getvalue()

    def print(self, data=None):
        self.write(data, sys.stdout)

if __name__ == '__main__':
    def gen(max=None, sleep=0, additional_columns=()):
        count = 0
        while True:
            time.sleep(sleep)
            count += 1
            yield (count,) + additional_columns
            if count == max:
                break

    def test(a, b):
        a = a.strip()
        b = textwrap.dedent(b).strip()
        if a != b:
            raise AssertionError('\n{}\n!=\n{}'.format(a, b))

    formatter = TableFormatter()
    formatter.add_column('bl')
    test(formatter.dumps((('foo',),)), '''
    -------
    | bl  |
    -------
    | foo |
    -------
    ''')

    formatter = TableFormatter()
    formatter.add_column('foo')
    test(formatter.dumps((('fo',),)), '''
    -------
    | foo |
    -------
    | fo  |
    -------
    ''')

    formatter = TableFormatter()
    formatter.add_column('foo')
    formatter.width = 10
    test(formatter.dumps((('fo',),)), '''
    ----------
    |  foo   |
    ----------
    | fo     |
    ----------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.add_column('c')
    formatter.width = 20
    test(formatter.dumps(((10, 11, 12),)), '''
    --------------------
    |  a  |  b  |  c   |
    --------------------
    | 10  | 11  | 12   |
    --------------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.width = 15
    test(formatter.dumps(((1, 100),)), '''
    ---------------
    | a  |   b    |
    ---------------
    | 1  | 100    |
    ---------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.width = 15
    test(formatter.dumps(((1000, 100000000),)), '''
    ---------------
    |  a  |   b   |
    ---------------
    | 100 | 10000 |
    | 0   | 0000  |
    ---------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.width = 15
    test(formatter.dumps((('foo_bar_baz', 'foo bar baz'),)), '''
    ---------------
    |   a   |  b  |
    ---------------
    | foo_b | foo |
    | ar_ba | bar |
    | z     | baz |
    ---------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.width = 17
    test(formatter.dumps((('foo', 'foo bar baz'),)), '''
    -----------------
    |  a  |    b    |
    -----------------
    | foo | foo bar |
    |     | baz     |
    -----------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.max_width = 15
    test(formatter.dumps(((1000, 100000000),)), '''
    ---------------
    |  a  |   b   |
    ---------------
    | 100 | 10000 |
    | 0   | 0000  |
    ---------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.add_column('b')
    formatter.max_width = 1000
    test(formatter.dumps(((1000, 100000000),)), '''
    --------------------
    |  a   |     b     |
    --------------------
    | 1000 | 100000000 |
    --------------------
    ''')

    formatter = TableFormatter()
    formatter.add_column('a')
    formatter.height = 5
    test(formatter.dumps(gen(4)), '''
    -----
    | a |
    -----
    | 1 |
    | 2 |
    -----
    | a |
    -----
    | 3 |
    | 4 |
    -----
    ''')
