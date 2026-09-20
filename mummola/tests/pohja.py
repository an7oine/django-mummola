''' Yhteiset apurit kirjautumis-, käyttäjä- ja kalenteritesteille. '''

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mummola.models import Sijainti


class MummolaTesti(TestCase):
  ''' Luo oletuskäyttäjän ja tarjoaa kalenteri- ja kirjautumisosoitteet. '''

  SALASANA = 'Alkusalasana-9'
  KALENTERI = '/mummola/'
  SISÄÄN = '/kirjaudu/sisaan/'
  ULOS = '/kirjaudu/ulos/'

  @classmethod
  def setUpTestData(cls):
    ''' Luo vakio- ja toinen käyttäjä kerran testiluokkaa kohden. '''
    User = get_user_model()
    cls.kayttaja = User.objects.create_user(
      'aada',
      password=cls.SALASANA,
    )
    cls.toinen = User.objects.create_user(
      'bertta',
      password=cls.SALASANA,
    )
    # def setUpTestData

  def kirjaudu(self, kayttaja=None, salasana=None):
    ''' Kirjaudu testiasiakkaalla (ohittaa lomakkeen). '''
    self.client.force_login(kayttaja or self.kayttaja)
    # def kirjaudu

  def varaus_data(self, **extra):
    ''' Palauta kelvollinen POST-aineisto uutta varausta varten. '''
    alku = timezone.now().replace(microsecond=0) + timedelta(days=1)
    loppu = alku + timedelta(hours=2)
    data = {
      'alku': alku.strftime('%Y-%m-%dT%H:%M'),
      'loppu': loppu.strftime('%Y-%m-%dT%H:%M'),
      'sijainti': Sijainti.MUMMOLA,
      'tarkeys': '3',
      'lapset': '2',
      'aikuiset': '1',
      'koirat': '1',
      'kuvaus': 'Viikonloppu mummolassa',
    }
    data.update(extra)
    return data
    # def varaus_data

  # class MummolaTesti
