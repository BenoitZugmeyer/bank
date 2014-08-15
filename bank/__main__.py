import yaml
import json
import sys
import logging
import datetime

import click

from . import config
from . import util
from . import project_name
from .db import DB
from .account import Account
from .tableformatter import TableFormatter

logger = logging.getLogger(__name__)


class App(object):
    def __init__(self, config):
        self.sessions = {}
        self.config = config
        self.db = DB(config.getpath('database', project_name + '.db'))

    @property
    def accounts(self):
        return tuple(Account(self, id) for id, infos in self.config.accounts)

pass_app = click.make_pass_decorator(App)


def print_version(ctx, value):
    if value and not ctx.resilient_parsing:
        import pkg_resources
        version = pkg_resources.require(project_name)[0].version
        click.echo(version)
        ctx.exit()


@click.group()
@click.option('--verbose', '-v', count=True)
@click.option('--version', '-V',
              help='Print version and exit',
              is_flag=True,
              callback=print_version,
              expose_value=False,
              is_eager=True)
@click.option('--config', 'config_path',
              type=click.Path(dir_okay=False,
                              readable=True,
                              resolve_path=True),
              default=project_name + '.yml',
              show_default=True)
@click.pass_context
def main(ctx, verbose, config_path):
    log_levels = {
        0: logging.ERROR,
        1: logging.INFO,
        2: logging.DEBUG
    }

    logging.basicConfig(level=log_levels.get(verbose, log_levels[2]))
    ctx.obj = App(config.from_yaml(config_path, default={}))
    if not ctx.obj.accounts:
        click.echo('No account configured')
        sys.exit(1)


@main.command(
    short_help='Chart the absolute balance of accounts over time',
    help='''
        Outputs a SVG chart representing all accounts balances over time.
    ''')
@click.option('--delta',
              help='Time between points',
              metavar='DELTA',
              show_default=True,
              type=util.create_delta,
              default='1 month')
@click.option('--since',
              help='Date to beging the chart',
              metavar='DATE',
              show_default=True,
              type=util.create_date,
              default='2014-01-10')
@click.option('--output', '-o',
              help='Where to output. The default is a mixup of accounts names',
              type=click.Path())
@pass_app
def chart(app, delta, since, output=None):
    try:
        import pygal
    except ImportError:
        click.echo('You have to install pygal to generate charts')
        sys.exit(1)

    accounts = app.accounts

    line_chart = pygal.StackedLine(x_label_rotation=45, fill=True)

    line_chart.title = 'Balance since {}'.format(since)

    for account in accounts:
        labels, values = util.format_serie(account, since, delta=delta)
        line_chart.add(account.name, values)
        line_chart.x_labels = labels

    filename = output or '_'.join(a.name for a in accounts) + '.svg'
    line_chart.render_to_file(filename)

    click.echo('Rendered to {}'.format(filename))


@main.command(
    help='Update the database with latest transactions',
)
@pass_app
def update(app):

    for account in app.accounts:
        click.echo('Udpating account {}'.format(account.name))

        balance_before = account.get_balance()
        account.update_balance()

        transactions_before = account.transaction_count()
        account.update_transactions()
        transactions_after = account.transaction_count()

        balance_after = account.get_balance()

        click.echo('Balance diff: {:.2}'
                   .format(balance_after - balance_before))

        click.echo('{} new transactions'
                   .format(transactions_after - transactions_before))


@main.command(
    help='Display current account balances',
)
@pass_app
def balances(app):

    f = TableFormatter()
    f.max_width, f.height = click.get_terminal_size()
    f.add_column('Account')
    f.add_column('Balance', align='>')
    f.print(
        (account.name, account.get_balance(datetime.date.today()))
        for account in app.accounts
    )


@main.command(
    help='Display the last transactions',
)
@click.option('-n',
              metavar='K',
              help='outputs the last K transactions',
              type=int,
              default=10)
@pass_app
def tail(app, n):

    f = TableFormatter()
    f.max_width, f.height = click.get_terminal_size()
    f.add_column('Date')
    f.add_column('Account')
    f.add_column('Type')
    f.add_column('Amount', align='>')
    f.add_column('Description')

    data = app.db.cursor().execute('''
    SELECT * FROM (
        SELECT date, account, type, amount, description
        FROM "transaction" ORDER BY date DESC
        LIMIT ?
    ) ORDER BY date
    ''', (n,))

    f.print(data)


@main.command(
    help='Search for transactions'
)
@click.argument('query')
@pass_app
def search(app, query):

    from . import ql

    statement, arguments = ql.build(query)

    f = TableFormatter()
    f.max_width, f.height = click.get_terminal_size()
    f.add_column('Date')
    f.add_column('Account')
    f.add_column('Type')
    f.add_column('Amount', align='>')
    f.add_column('Description')

    query = '''
    SELECT * FROM (
        SELECT date, account, type, amount, description
        FROM "transaction"
        WHERE {}
        ORDER BY date DESC
    ) ORDER BY date
    '''.format(statement)

    logger.debug(query)
    logger.debug(repr(arguments))

    f.print(app.db.cursor().execute(query, arguments))


@main.command(
    short_help='Reindex all transactions from the database',
    help='''
        Reindex all transactions from the database. You should not need to use
        this.
    ''')
@pass_app
def reindex(app):
    app.db.cursor().executescript('''
    DELETE FROM "transaction_search";
    INSERT INTO "transaction_search" (docid, account, type, description)
        SELECT hash, account, type, description
        FROM "transaction"
    ''')


@main.command(
    'config',
    help='''
        Print parsed configuration file
    ''')
@click.option('--type', '-t',
              type=click.Choice(('json', 'yaml')),
              default='yaml')
@pass_app
def config_command(app, type):

    if type == 'json':
        click.echo(json.dumps(app.config,
                              default=util.json_default,
                              indent=2))

    elif type == 'yaml':
        click.echo(yaml.dump(app.config, Dumper=util.YamlDumper))

if __name__ == '__main__':
    main()
