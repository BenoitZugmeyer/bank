
====
bank
====

A command line banking utility.

Disclaimer
==========

This project is at its early stages, things will break. Please backup your database regularly.

Installation
============

Install it via :code:`pip` (python 3+)::

    $ pip install --allow-external pyPEG2 --allow-unverified pyPEG2 https://github.com/BenoitZugmeyer/bank/archive/master.zip

Those two pyPEG2 related flags are unfortunate but it would be resolved by `this issue`_.

Usage
=====

::

    $ bank --help
    Usage: bank [OPTIONS] COMMAND [ARGS]...

    Options:
      -v, --verbose
      -V, --version  Print version and exit
      --config PATH  [default: bank.yml]
      --help         Show this message and exit.

    Commands:
      balances  Display current account balances
      chart     Chart the absolute balance of accounts over time
      config    Print parsed configuration file
      reindex   Reindex all transactions from the database
      search    Search for transactions
      tail      Display the last transactions
      update    Update the database with latest transactions


Adaptors
========

An adaptor is a python module to download account transactions from any service. For now, only one adaptor is included.


bred
----

Interfaces with the `bred`_ french bank. :code:`bank` will prompt for an identifier and a password if you don't provide one in the configuration file.


Search query language
=====================

:code:`bank` provides a query language to quickly find transactions. For now, this is only accessible via the :code:`bank search` command.

Full text search
----------------

:code:`bank` uses the `sqlite3 fts extension`_ to search inside various fields of each transaction. By default, it searches into the description field.

:code:`gittip`
    transactions with the word 'gittip' in the description

:code:`paypal or amazon`
    transactions containing the word 'paypal' or 'amazon'

:code:`sncf or "capitaine train"`
    transactions containing the word 'sncf' or 'capitaine train' (but not 'train capitaine')

:code:`volt*`
    transactions containing a word starting with 'volt'

:code:`type:loan`
    transactions with the word 'loan' in the type field

Time search
-----------

Operators to filter transactions based on some dates.

:code:`since 2014-02-03`
    transactions since february 3rd, 2014

:code:`since 10 days`
    transactions since 10 days from now

:code:`before 2014-02-03`
    transactions before february 3rd, 2014

:code:`between 2014-01-01 and 2014-01-31`
    transactions from january 2014

Amount search
-------------

Operators to filter transactions based on the amount of the transaction.

:code:`more than 1000`
    transactions with the absolute amount being more than 1000

:code:`more than +1000`
    transactions with the amount being more than 1000

:code:`less than -1000`
    transactions with the amount being less than -1000

Combining everything
--------------------

All those predicates can be combined in a single query. The default operator is a :code:`and`.

:code:`gittip since 10 days`
    transactions containing 'gittip' within the 10 last days

:code:`amazon more than +0`
    all amazon refounds

:code:`not account:xxx or since 10 days`
    all transactions excluding those from the account id xxx if they are more than 10 days


Configuration
=============

The configuration file should be in `yaml`_ format. By default, :code:`bank` will use the file :code:`bank.yml` located in the local directory, but you can specify another path with the :code:`--config` option. All paths are relative to the configuration file

The configuration file is structured as follow:

.. code:: yaml

    # The database path. Defaults to bank.db.
    database: path_to_sqlite_database.db

    # Accounts listing.
    accounts:

        # Each account is reprensented by an ID. This ID should never change.
        XXXXXX-XXX:

            # Name of the account. You can rename it at any time.
            name: Checking account

            # Name of the adaptor to use. For now, only 'bred' is supported
            type: bred

            # Optional, the name of the session to use. Defaults to the 'type'
            # attribute
            session: my other session


        # Another account...
        YYYYYY-YYY:
            name: Hop
            type: bred

    # Optional, this lists information to send to the adaptor to authenticate
    # you. By default, all accounts of the same type will use the same session,
    # but you can specify any number of sessions you want
    sessions:

        # Default session informations to use with the 'bred' adaptor
        bred:

            # Optional, you identifier. bank will prompt it if you don't
            # provide one.
            identifier: fred

            # Optional, you password. bank will prompt it if you don't provide
            # one.
            password: xxx

        my other session:
            identifier: toto


License
=======

Copyright (C) 2014 Benoît Zugmeyer <benoit@zugmeyer.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


.. _yaml: http://yaml.org/
.. _bred: http://bred.fr/
.. _sqlite3 fts extension: http://www.sqlite.org/fts3.html
.. _this issue: https://bitbucket.org/fdik/pypeg/issue/23/host-pypeg-on-pypi
