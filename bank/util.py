import re
import datetime
import collections
import json

import yaml
import dateutil.parser


def json_default(o):
    if hasattr(o, '__json__'):
        return o.__json__()
    return json.JSONEncoder.default(o)


class YamlDumper(yaml.SafeDumper):
    pass


YamlDumper.add_representer(
    collections.OrderedDict,
    lambda r, d: YamlDumper.represent_dict(r, d.items()))


class YamlLoader(yaml.SafeLoader):
    pass

YamlLoader.add_constructor(
    YamlLoader.DEFAULT_MAPPING_TAG,
    lambda loader, node: collections.OrderedDict(loader.construct_pairs(node)))


def generate_dates(start, delta):
    date = start

    while True:
        yield date
        date += delta


def create_date(date=None, **parser_options):

    if date is None:
        date = datetime.date.today()

    elif isinstance(date, str):
        date = dateutil.parser.parse(date, **parser_options).date()

    elif not isinstance(date, datetime.date):
        raise Exception('not a date {!r}'.format(date))

    return date


def format_date(date):
    return date.strftime('%Y-%m-%d')


def format_serie(account, since, delta):
    labels = []
    values = []

    balance = account.get_balance(since=since)
    for date, transactions in account.iter_transactions_by_dates(
            since=since,
            delta=delta,
            until=create_date()):
        balance += sum(t.amount for t in transactions)
        label = '{} ({})'.format(date.strftime('%d-%m-%y'), len(transactions))
        value = round(balance, 2)
        values.append(value)
        labels.append(label)

    return labels, values


delta_re = re.compile(r'''
(-?\d+)?                 # length
\s*                      # some space
(month|year|week|day)s?  # unit
''', re.VERBOSE)


def create_delta(delta):
    if isinstance(delta, str):

        args = {}
        for r in delta_re.finditer(delta):
            args[r.group(2) + 's'] = int(r.group(1) or 1)

        if not args:
            raise ValueError('not a valid delta format {!r}'.format(delta))

        delta = dateutil.relativedelta.relativedelta(**args)

    elif not isinstance(delta, (
            dateutil.relativedelta.relativedelta,
            datetime.timedelta)):
        raise ValueError('not a delta {!r}'.format(delta))

    return delta
