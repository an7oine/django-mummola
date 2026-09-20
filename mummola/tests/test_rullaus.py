'''
Selaintesti jaksonvaihdolle: liukuanimaatiot ja rullauksen kynnysarvot.

Erityisesti tilanne, jossa käyttäjä siirtyy nopeasti edelliseen ja heti
perään seuraavaan viikkoon (tai toisin päin).

Koe ajetaan yhtenä selainistuntona (`js/rullaus.js`), ja kunkin vaiheen
tulos tarkistetaan omana alitestinään.
'''

import unittest
from datetime import timedelta

from django.utils import timezone

from mummola.mallit import Sijainti, Varaus
from mummola.tests.selain import SelainTesti, selain_puuttuu

# Kuinka monta pikseliä rullain saa levätä lähtökohdastaan sivussa.
SALLITTU_POIKKEAMA = 2


@unittest.skipIf(selain_puuttuu(), selain_puuttuu())
class RullausTesti(SelainTesti):
  ''' Kosketuseleet kalenterisivulla puhelimen kokoisella ruudulla. '''

  def setUp(self):
    ''' Varauksia usealle viikolle, jotta jaksot eroavat toisistaan. '''
    super().setUp()
    keskiyo = timezone.localtime().replace(
      hour=0, minute=0, second=0, microsecond=0
    )
    for siirto in (-9, -2, 0, 3, 8):
      Varaus.objects.create(
        tekija=self.kayttaja,
        alku=keskiyo + timedelta(days=siirto, hours=9),
        loppu=keskiyo + timedelta(days=siirto, hours=15),
        tarkeys=3, lapset=2, aikuiset=1, koirat=1,
        sijainti=Sijainti.MUMMOLA,
      )
    # def setUp

  def tiedot(self, tila):
    ''' Rullaimen mitat virheilmoitukseen. '''
    return (
      f'kohta {tila["kohta"]}, lähtökohta {tila["lahtokohta"]},'
      f' sisältö {tila["ylaraja"]}–{tila["alaraja"]},'
      f' ruudukko {tila["ruudukonKohta"]}/{tila["ruudukonVara"]}'
    )
    # def tiedot

  def tarkista_lopputila(self, tila):
    ''' Liuku on päättynyt, jäljennös siivottu ja rullain lähtökohdassa. '''
    self.assertFalse(tila['liukuKesken'], 'liuku jäi kesken (data-vaihtuu)')
    self.assertEqual(
      tila['jaljennoksia'], 0, 'vanhan jakson jäljennös jäi näkyviin'
    )
    self.assertEqual(
      tila['paikka'], 'sisalto',
      f'rullain jäi pehmusteeseen: kohta {tila["kohta"]},'
      f' sisältö {tila["ylaraja"]}–{tila["alaraja"]}'
    )
    self.assertLessEqual(
      abs(tila['poikkeama']), SALLITTU_POIKKEAMA,
      f'rullain ei ole lähtökohdassa: kohta {tila["kohta"]},'
      f' lähtökohta {tila["lahtokohta"]}'
    )
    # def tarkista_lopputila

  def test_jaksonvaihto(self):
    ''' Eleiden sarja ei saa vaihtaa jaksoa itsestään eikä jäädä jumiin. '''
    tulos = self.aja_selain('rullaus.js')
    self.assertEqual(tulos['virheet'], [], 'sivu heitti JS-poikkeuksen')

    with self.subTest('lepo'):
      # Koskematon sivu pysyy paikallaan.
      tila = tulos['lepo']
      self.assertEqual(
        tila['muutoksia'], 0,
        f'jakso vaihtui itsestään: {tila["nimikkeet"]}'
      )
      self.assertEqual(tila['liukuja'], 0)
      self.tarkista_lopputila(tila)

    with self.subTest('pieni ele'):
      # Kynnystä pienempi pyyhkäisy palautuu eikä vaihda jaksoa.
      tila = tulos['pieni']
      self.assertEqual(
        tila['muutoksia'], 0,
        f'pieni ele vaihtoi jakson: {tila["nimikkeet"]}'
        f' (ele vei {tila["heti"]} px lähtökohdasta,'
        f' pehmuste {tila["ylapehmuste"]} px)'
      )
      self.assertEqual(tila['liukuja'], 0, 'pieni ele käynnisti liu\'un')
      self.tarkista_lopputila(tila)

    with self.subTest('kynnyksen yli'):
      # Kynnyksen ylittävä veto vaihtaa jakson tasan kerran.
      tila = tulos['kynnyksenYli']
      self.assertEqual(
        tila['muutoksia'], 1,
        f'jakso ei vaihtunut kertaalleen: {tila["nimikkeet"]}'
      )
      self.assertEqual(tila['liukuja'], 1)
      self.tarkista_lopputila(tila)

    for vaihe, otsikko in (
      ('seuraavaEdellinen', 'seuraava ja edellinen'),
      ('edellinenSeuraava', 'edellinen ja seuraava'),
    ):
      with self.subTest(otsikko):
        # Kaksi vastakkaista elettä vie takaisin lähtöjaksoon.
        tila = tulos[vaihe]
        self.assertNotEqual(
          tila['valinimike'], tila['nimikkeet'][0],
          'ensimmäinen pyyhkäisy ei vaihtanut jaksoa'
        )
        self.assertEqual(
          tila['muutoksia'], 2,
          f'jakso vaihtui väärän monta kertaa: {tila["nimikkeet"]}'
        )
        self.assertEqual(
          tila['liukuja'], 2,
          f'liukuanimaatioita {tila["liukuja"]}, odotettiin kahta'
        )
        self.assertEqual(
          tila['nimike'], tila['nimikkeet'][0],
          f'ei palattu lähtöjaksoon: {tila["nimikkeet"]}'
        )
        self.tarkista_lopputila(tila)

    for vaihe, otsikko in (
      ('nopea', 'nopea sarja eteen ja taakse'),
      ('nopeaToisinpain', 'nopea sarja taakse ja eteen'),
    ):
      with self.subTest(otsikko):
        # Toinen ele alkaa kesken liu'un: kalenteri ei saa jäädä sekaisin.
        tila = tulos[vaihe]
        self.assertLessEqual(
          tila['muutoksia'], 2,
          f'nopea sarja vaihtoi jaksoa liikaa: {tila["nimikkeet"]}'
        )
        self.assertEqual(
          tila['nimike'], tila['nimikkeet'][0],
          f'nopea sarja jätti väärään jaksoon: {tila["nimikkeet"]}'
        )
        self.tarkista_lopputila(tila)

    # def test_jaksonvaihto

  def test_hiirirullaus(self):
    '''
    Työpöydällä jokainen rullaus vaihtaa jakson, myös ensimmäisen jälkeen.

    Rullaus jumitti aiemmin niin, että ensimmäinen ylösrullaus siirsi
    edelliseen viikkoon, minkä jälkeen seuraavat rullaukset vain
    keskittivät näkymän.
    '''
    tulos = self.aja_selain('hiirirullaus.js')
    self.assertEqual(tulos['virheet'], [], 'sivu heitti JS-poikkeuksen')

    for tila in tulos['vaiheet']:
      with self.subTest(tila['nimi']):
        suunta = 'edelliseen' if tila['suunta'] < 0 else 'seuraavaan'
        self.assertGreaterEqual(
          tila['muutoksia'], 1,
          f'rullaus {suunta} ei vaihtanut jaksoa: {self.tiedot(tila)}'
        )
        self.tarkista_lopputila(tila)

    with self.subTest('yhtäjaksoinen rullaus'):
      # Tauoton rullaus jatkuu ensimmäisen vaihdon jälkeenkin.
      tila = tulos['yhtajaksoinen']
      self.assertGreaterEqual(
        tila['muutoksia'], 2,
        'tauoton rullaus vaihtoi jakson vain kerran ja jäi sen jälkeen'
        f' keskittämään näkymää: {tila["nimikkeet"]}, {self.tiedot(tila)}'
      )
      self.tarkista_lopputila(tila)

    # def test_hiirirullaus

  # class RullausTesti
