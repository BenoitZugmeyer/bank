from urllib.parse import urljoin
import logging
import re

import click
import requests

from ..transaction import tsv_parser
from ..adaptor import Adaptor, AdaptorError
from ..util import create_date


logger = logging.getLogger(__name__)


class BredAdaptorError(AdaptorError):
    pass


class Session(requests.Session):

    root_url = 'https://www.bred.fr/Andromede/'

    def __init__(self, identifier=None, password=None):
        super().__init__()
        self.identifier = identifier
        self.password = password

    def _authentificate(self):
        if not self.identifier or not self.password:
            raise BredAdaptorError('Can\'t authentificate without identifiers')

        auth_data = {
            'typeDemande': 'ID',
            'id': self.identifier,
            'pass': self.password,
        }

        self.post('MainAuth', data=auth_data)

    def prepare_request(self, request):
        if 'bredplone_cookie' not in self.cookies and \
                not request.url.endswith('MainAuth'):
            self._authentificate()

        request.url = urljoin(self.root_url, request.url)
        return super().prepare_request(request)

    def send(self, request, **kwargs):
        logger.debug('send', request.url)
        return super().send(request, **kwargs)


class BredAdaptor(Adaptor):

    def create_session(self, config):
        identifier = config.identifier or click.prompt('BRED identifier')
        password = config.password or click.prompt('BRED password',
                                                   hide_input=True)
        return Session(identifier, password)

    def fetch_transactions(self, since):
        download_params = {
            'type_demande': 'C',
            'periode': 'true',
            'date1': since.strftime('%Y%m%d'),
            'date2': create_date().strftime('%Y%m%d'),
            'fichier_telechargement': 'excel',
            'date_telechargement': 'JJMMAAAA',
            'separateur_telechargement': 'point',
            'fichier': '11404097.dat',
        }

        self.set_account_data(download_params)

        request = self.session.get('Telechargement',
                                   params=download_params)

        if 'text/html' in request.headers.get('content-type', ''):
            return set()

        return tsv_parser(self.account, request.text.split('\n'))

    def fetch_balance(self):

        params = {
            'nom_application': 'compte_epargne_detail',
            'typeDemande': 'D',
            'from': 'compte_consultation',
        }

        self.set_account_data(params)

        content = self.session.get('Main', params=params).text

        result = re.search(r'Solde après dernière opération enregistrée le '
                           r'(\d\d/\d\d/\d\d\d\d) : '
                           r'[<>a-z ]*(-?[\d\s]+,\d+)\sEUR',
                           content)

        if not result:
            raise Exception('Can\'t parse balance')

        date, amount = result.groups()
        date = create_date(date, dayfirst=True)
        amount = float(amount.translate({
            ord(' '): None,
            0xA0: None,
            ord(','): ord('.')
        }))

        return date, amount

    def set_account_data(self, data):
        data['numero_compte'], _, data['numero_poste'] = self.account.id \
            .partition('-')
