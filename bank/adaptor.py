

class AdaptorError(Exception):
    pass


class ActionNotAvailaible(AdaptorError):
    pass


class AdaptorMeta(type):

    def __new__(cls, name, bases, namespace):
        if 'create_session' in namespace:
            namespace['_sessions'] = {}
        return super().__new__(cls, name, bases, namespace)


class Adaptor(metaclass=AdaptorMeta):

    def __init__(self, account):
        self.account = account

    @property
    def session(self):
        name = self._session_name
        sessions = self._sessions

        if name not in sessions:
            sessions[name] = self.create_session(
                self.account.app.config.sessions.get(name))

        return sessions[name]

    @property
    def _session_name(self):
        a = self.account.config
        return a.session or a.type

    def create_session(self, config):
        raise ActionNotAvailaible()

    def fetch_transactions(self, since):
        raise ActionNotAvailaible()

    def fetch_balance(self):
        raise ActionNotAvailaible()


if __name__ == '__main__':
    from bank.config import Config

    class Account():
        app = Config({
            'config': {
                'sessions': {
                    'blah': 'foo'
                }
            }
        })

        config = Config({
            'type': 'blah'
        })

    class SubAdaptorA(Adaptor):

        def create_session(self, config):
            return {}

    class SubAdaptorB(Adaptor):

        def create_session(self, config):
            return {}

    account = Account()
    assert SubAdaptorA._sessions is not SubAdaptorB._sessions
    assert SubAdaptorA(account).session is not SubAdaptorB(account).session
    assert SubAdaptorB(account).session is SubAdaptorB(account).session
