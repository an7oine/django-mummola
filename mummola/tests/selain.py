''' Apurit selaintesteille (Node + puppeteer-core + Chromium-selain). '''

import json
import os
import shutil
import subprocess
from pathlib import Path

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

JS_HAKEMISTO = Path(__file__).parent / 'js'

# Selaintestit vaativat työkalut, joita ei ole joka koneella; puuttuessa
# testit ohitetaan. Polut voi ylikirjoittaa ympäristömuuttujilla.
SELAIN = os.environ.get(
  'MUMMOLA_SELAIN',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
)
NODE_MODULES = os.environ.get(
  'MUMMOLA_NODE_PATH', '/tmp/mummolaselain/node_modules'
)


def selain_puuttuu():
  ''' Kerro syy, miksi selaintestejä ei voi ajaa – tai tyhjä merkkijono. '''
  if not shutil.which('node'):
    return 'node puuttuu'
  if not Path(SELAIN).exists():
    return f'selainta ei löydy: {SELAIN}'
  if not (Path(NODE_MODULES) / 'puppeteer-core').exists():
    return f'puppeteer-core puuttuu: {NODE_MODULES}'
  return ''
  # def selain_puuttuu


class SelainTesti(StaticLiveServerTestCase):
  '''
  Pohja selaintesteille: luo käyttäjän ja ajaa `js/`-hakemiston ajurin.

  Ajuri tulostaa tuloksensa rivillä `TULOS <json>`.
  '''

  tunnus = 'mummo'
  salasana = 'salasana-123'

  def setUp(self):
    ''' Luo käyttäjä, jolle salasanamodaali ei aukea kirjautuessa. '''
    super().setUp()
    self.kayttaja = get_user_model().objects.create_user(
      username=self.tunnus, password=self.salasana
    )
    LogEntry.objects.log_actions(
      self.kayttaja.pk, [self.kayttaja], CHANGE,
      change_message='salasana', single_object=True,
    )
    # def setUp

  def aja_selain(self, ajuri, aikakatkaisu=300):
    ''' Aja Node-ajuri kalenterisivua vasten ja palauta sen JSON-tulos. '''
    ymparisto = {
      **os.environ,
      'NODE_PATH': NODE_MODULES,
      'MUMMOLA_SELAIN': SELAIN,
    }
    tulos = subprocess.run(
      [
        'node', str(JS_HAKEMISTO / ajuri),
        self.live_server_url, self.tunnus, self.salasana,
      ],
      capture_output=True, text=True,
      timeout=aikakatkaisu, env=ymparisto,
    )
    if tulos.returncode:
      self.fail(f'selainajuri {ajuri} kaatui:\n{tulos.stderr}')
    for rivi in tulos.stdout.splitlines():
      if rivi.startswith('TULOS '):
        return json.loads(rivi[len('TULOS '):])
    self.fail(
      f'selainajuri {ajuri} ei tulostanut tulosta:\n'
      f'{tulos.stdout}\n{tulos.stderr}'
    )
    # def aja_selain

  # class SelainTesti
