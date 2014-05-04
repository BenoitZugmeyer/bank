from io import StringIO
import re
from pypeg2 import maybe_some, attr, List, some, Symbol, omit, parse, optional, separated

__all__ = ['build']


class MetaThing(type):

    def __repr__(cls):
        if hasattr(cls, '__class_repr__'):
            return cls.__class_repr__(cls)
        return cls.__name__


class Thing(metaclass=MetaThing):

    @property
    def fts(self):
        if isinstance(self, list):
            return all(sub.fts for sub in self)

        return False


expressions = []


class MetaExpression(MetaThing):
    def __new__(cls, name, bases, dict):
        result = super().__new__(cls, name, bases, dict)
        if any(isinstance(c, cls) for c in bases):
            expressions.append(result)
        return result


class Expression(Thing, metaclass=MetaExpression):
    pass


def K(*_aliases):

    class KSymbol(Symbol, Thing):
        keyword = _aliases[0]
        pattern = '|'.join(
            r'\b{}\b'.format(''.join(
                '[{}{}]'.format(char, char.upper())
                for char in alias
            ))
            for alias in _aliases
        )
        regex = re.compile(pattern)

        def __new__(cls, value):
            return super().__new__(cls, cls.keyword)

        def __str__(self):
            return self.keyword

        def __repr__(self):
            return self.keyword

        def __class_repr__(cls):
            return cls.keyword

    return KSymbol

symbols = {
    'day': K('day', 'days'),
    'month': K('month', 'months'),
    'year': K('year', 'years'),
    'week': K('week', 'weeks'),
    'and': K('and'),
    'or': K('or'),
    'since': K('since', 'after'),
    'between': K('between'),
    'before': K('before'),
    'more': K('more'),
    'less': K('less'),
    'not': K('not'),
}

del K


number = re.compile('-?\d+(\.\d+)?')


class BooleanOperator(str, Thing):
    grammar = [symbols['or'], symbols['and']]

    def build(self, builder):
        builder.add(self)


class TimeUnit(str, Thing):
    grammar = [
        symbols['day'],
        symbols['week'],
        symbols['month'],
        symbols['year'],
    ]


class Word(str, Thing):
    word_re = r'''
    (?!{keywords_re})           # Ignore keywords
    -?(?:\w+:)?                 # Field
    ( [\w:*\\][\w:*\\-]*        # Simple words
    |
        (?:"
            (?:[^"\n\r\\]       # Double quoted strings
            |  ""
            |  \\x[0-9a-fA-F]+
            |  \\.
            )*
        "
        |  '
            (?:[^'\n\r\\]       # Single quoted strings
            |  ''
            |  \\x[0-9a-fA-F]+
            |  \\.
            )*
        '
        )
    )
    '''.format(keywords_re='|'.join(s.pattern for s in symbols.values()))

    grammar = re.compile(word_re, re.VERBOSE)

    del word_re


class Date(str, Thing):
    grammar = re.compile(r'\d\d\d\d-\d\d-\d\d')


class Query(List, Thing):
    grammar = expressions, maybe_some(optional(BooleanOperator), expressions)

    def build(self, builder):
        previous = None
        for thing in self:
            if previous and \
                    not isinstance(previous, BooleanOperator) and \
                    not isinstance(thing, BooleanOperator):
                builder.add('AND')
            thing.build(builder)
            previous = thing


class AfterDateExpression(Expression, str):
    grammar = omit(symbols['since']), Date

    def build(self, builder):
        builder.add('''date >= ?''', self)


class BeforeDateExpression(Expression, str):
    grammar = omit(symbols['before']), Date

    def build(self, builder):
        builder.add('''date <= ?''', self)


class BetweenDateExpression(Expression):
    grammar = \
        omit(symbols['between']), attr('min', Date), \
        omit(symbols['and']), attr('max', Date)

    def build(self, builder):
        builder.add('''(date >= ? AND date <= ?)''', self.min, self.max)


class RelativeDateExpression(Expression):
    grammar = \
        omit(symbols['since']), \
        attr('length', number), \
        attr('unit', TimeUnit)

    def build(self, builder):
        unit = self.unit
        length = -int(self.length)

        if unit == 'week':
            length *= 7
            unit = 'day'

        builder.add('''date >= DATE('now', '{} {}')'''.format(length, unit))


class AmountExpression(Expression):
    grammar = \
        attr('cmp', [symbols['more'], symbols['less']]), \
        optional('than'), \
        attr('sign', re.compile(r'[+-]?')), \
        attr('value', number)

    def build(self, builder):
        operator = '>=' if self.cmp == 'more' else '<='
        amount = 'amount' if self.sign else 'ABS(amount)'

        value = float(self.value)
        if self.sign == '-':
            value *= -1

        builder.add('{} {} ?'.format(amount, operator), value)


class NotExpression(Expression, List):
    grammar = omit(symbols['not']), expressions

    def build(self, builder):
        builder.add('NOT (')
        self[0].build(builder)
        builder.add(')')


class GroupExpression(Query):
    grammar = '(', Query.grammar, ')'

    def build(self, builder):
        builder.add('(')
        super().build(builder)
        builder.add(')')


class WordsExpression(Expression, List):
    grammar = separated(some(Word))

    def build(self, builder):
        builder.add('''
            hash IN (
                SELECT docid
                FROM transaction_search
                WHERE description
                MATCH ?
            )''', ' '.join(self))


class StatementBuilder(object):
    def __init__(self):
        self._statement = StringIO()
        self._arguments = []

    def add(self, part, *args):
        self._statement.write(part)
        self._statement.write(' ')
        self._arguments.extend(args)

    @property
    def statement(self):
        return self._statement.getvalue()

    @property
    def arguments(self):
        return tuple(self._arguments)


def build(query):
    builder = StatementBuilder()
    parse(query, Query).build(builder)
    return builder.statement, builder.arguments

if __name__ == '__main__':
    import sys
    print(*build(sys.argv[1]))
