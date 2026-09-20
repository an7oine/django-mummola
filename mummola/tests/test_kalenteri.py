''' Kalenterisivun näkyvyys sekä varausten luonti, päivitys ja poisto. '''

from datetime import timedelta

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from mummola.models import Sijainti, Varaus

from .pohja import MummolaTesti


class KalenterisivuTesti(MummolaTesti):
  ''' Kirjautuneen kalenterisivun rakenne. '''

  def test_sivu_sisaltaa_kalenterin_ja_lomakkeet(self):
    ''' Kalenterielementti, varauslomake ja käyttäjävalikko renderöityvät. '''
    self.kirjaudu()
    vastaus = self.client.get(self.KALENTERI)
    self.assertEqual(vastaus.status_code, 200)
    self.assertContains(vastaus, '<title', html=False)
    self.assertContains(vastaus, 'Mummola')
    self.assertContains(vastaus, 'Mummolan varauskalenteri')
    self.assertContains(vastaus, 'id="mummola"')
    self.assertContains(vastaus, 'data-solmu-esitys="mummola, kalenteri"')
    self.assertContains(vastaus, 'id="varaus-lomake"')
    self.assertContains(vastaus, 'name="alku"')
    self.assertContains(vastaus, 'name="loppu"')
    self.assertContains(vastaus, 'name="sijainti"')
    self.assertContains(vastaus, 'name="tarkeys"')
    self.assertContains(vastaus, 'name="lapset"')
    self.assertContains(vastaus, 'name="aikuiset"')
    self.assertContains(vastaus, 'name="koirat"')
    self.assertContains(vastaus, 'name="kuvaus"')
    self.assertContains(vastaus, 'Mummolassa')
    self.assertContains(vastaus, 'muualla')
    self.assertContains(vastaus, 'Käyttäjävalikko')
    self.assertContains(vastaus, 'Kirjaudu ulos')
    self.assertContains(vastaus, 'action="/kirjaudu/ulos/"')
    self.assertNotContains(vastaus, 'Kanta')
    # def test_sivu_sisaltaa_kalenterin_ja_lomakkeet

  def test_tekijavalikko_sisaltaa_kayttajat(self):
    ''' Muokkauslomakkeen tekijä-valikko listaa käyttäjät. '''
    self.kirjaudu()
    vastaus = self.client.get(self.KALENTERI)
    self.assertContains(vastaus, 'id="id_tekija"')
    self.assertContains(vastaus, self.kayttaja.username)
    self.assertContains(vastaus, self.toinen.username)
    # def test_tekijavalikko_sisaltaa_kayttajat

  # class KalenterisivuTesti


class VarausTesti(MummolaTesti):
  ''' Varauksen CRUD Yhdiste-toimintojen kautta. '''

  def hae_varaukset(self, alku=None, loppu=None):
    ''' GET `?varaukset` annetulta (tai laajalta) aikaväliltä. '''
    if alku is None:
      alku = timezone.now() - timedelta(days=1)
    if loppu is None:
      loppu = timezone.now() + timedelta(days=14)
    return self.client.get(self.KALENTERI, {
      'varaukset': '',
      'start': alku.isoformat(),
      'end': loppu.isoformat(),
    })
    # def hae_varaukset

  def test_tyhja_kalenteri_palauttaa_listan(self):
    ''' Ilman varauksia JSON-aineisto on tyhjä lista. '''
    self.kirjaudu()
    vastaus = self.hae_varaukset()
    self.assertEqual(vastaus.status_code, 200)
    self.assertEqual(vastaus.json(), [])
    # def test_tyhja_kalenteri_palauttaa_listan

  def test_luonti_tallentaa_kentat_ja_lokittaa(self):
    ''' POST `?varaa` luo varauksen kaikilla osallistujakentillä. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(),
    )
    self.assertEqual(vastaus.status_code, 200)
    data = vastaus.json()
    varaus = Varaus.objects.get(pk=data['id'])
    self.assertEqual(varaus.tekija, self.kayttaja)
    self.assertEqual(varaus.sijainti, Sijainti.MUMMOLA)
    self.assertEqual(varaus.tarkeys, 3)
    self.assertEqual(varaus.lapset, 2)
    self.assertEqual(varaus.aikuiset, 1)
    self.assertEqual(varaus.koirat, 1)
    self.assertEqual(varaus.kuvaus, 'Viikonloppu mummolassa')
    self.assertEqual(data['title'], f'Mummolassa · {self.kayttaja}')
    self.assertEqual(data['color'], varaus.vari)
    self.assertEqual(data['extendedProps']['oma'], True)
    self.assertEqual(data['extendedProps']['aikuiset'], 1)
    self.assertEqual(data['extendedProps']['koirat'], 1)
    self.assertTrue(
      LogEntry.objects.filter(
        user=self.kayttaja,
        content_type=ContentType.objects.get_for_model(Varaus),
        object_id=str(varaus.pk),
        action_flag=ADDITION,
      ).exists()
    )
    viesti = LogEntry.objects.get(
      object_id=str(varaus.pk),
      action_flag=ADDITION,
    ).change_message
    self.assertIn('tärkeys: 3', viesti)
    self.assertIn('lasten määrä: 2', viesti)
    self.assertIn('aikuisten määrä: 1', viesti)
    self.assertIn('koirien määrä: 1', viesti)
    self.assertIn('sijainti: Mummolassa', viesti)
    self.assertIn('kuvaus: Viikonloppu mummolassa', viesti)
    self.assertIn(self.kayttaja.username, viesti)
    # def test_luonti_tallentaa_kentat_ja_lokittaa

  def test_luotu_varaus_nakyy_aineistossa(self):
    ''' GET `?varaukset` sisältää juuri luodun varauksen. '''
    self.kirjaudu()
    luotu = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(),
    ).json()
    aineisto = self.hae_varaukset().json()
    tunnisteet = [rivi['id'] for rivi in aineisto]
    self.assertIn(luotu['id'], tunnisteet)
    # def test_luotu_varaus_nakyy_aineistossa

  def test_paivitys_muuttaa_kentat(self):
    ''' POST `?muokkaa&pk=` päivittää oman varauksen. '''
    self.kirjaudu()
    varaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(),
    ).json()
    uusi_alku = timezone.now().replace(microsecond=0) + timedelta(days=3)
    uusi_loppu = uusi_alku + timedelta(hours=4)
    vastaus = self.client.post(
      f'{self.KALENTERI}?muokkaa&pk={varaus["id"]}',
      self.varaus_data(
        alku=uusi_alku.strftime('%Y-%m-%dT%H:%M'),
        loppu=uusi_loppu.strftime('%Y-%m-%dT%H:%M'),
        sijainti=Sijainti.MUUALLA,
        tarkeys='5',
        lapset='0',
        aikuiset='4',
        koirat='2',
        kuvaus='Siirretty',
        tekija=str(self.kayttaja.pk),
      ),
    )
    self.assertEqual(vastaus.status_code, 200)
    paivitetty = Varaus.objects.get(pk=varaus['id'])
    self.assertEqual(paivitetty.sijainti, Sijainti.MUUALLA)
    self.assertEqual(paivitetty.tarkeys, 5)
    self.assertEqual(paivitetty.lapset, 0)
    self.assertEqual(paivitetty.aikuiset, 4)
    self.assertEqual(paivitetty.koirat, 2)
    self.assertEqual(paivitetty.kuvaus, 'Siirretty')
    self.assertEqual(vastaus.json()['title'], f'muualla · {self.kayttaja}')
    self.assertTrue(
      LogEntry.objects.filter(
        object_id=str(paivitetty.pk),
        action_flag=CHANGE,
      ).exists()
    )
    viesti = LogEntry.objects.get(
      object_id=str(paivitetty.pk),
      action_flag=CHANGE,
    ).change_message
    self.assertIn('sijainti: muualla', viesti)
    self.assertIn('tärkeys: 5', viesti)
    self.assertIn('kuvaus: Siirretty', viesti)
    self.assertIn('lasten määrä: 0', viesti)
    self.assertIn('aikuisten määrä: 4', viesti)
    self.assertIn('koirien määrä: 2', viesti)
    self.assertNotIn('Mummolassa', viesti)
    # def test_paivitys_muuttaa_kentat

  def test_paivitys_voi_vaihtaa_tekijaa(self):
    ''' Muokkauslomakkeen tekijä-kenttä tallentuu. '''
    self.kirjaudu()
    varaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(),
    ).json()
    vastaus = self.client.post(
      f'{self.KALENTERI}?muokkaa&pk={varaus["id"]}',
      self.varaus_data(tekija=str(self.toinen.pk)),
    )
    self.assertEqual(vastaus.status_code, 200)
    self.assertEqual(
      Varaus.objects.get(pk=varaus['id']).tekija,
      self.toinen,
    )
    # def test_paivitys_voi_vaihtaa_tekijaa

  def test_poisto_poistaa_varauksen(self):
    ''' POST `?poista&pk=` poistaa oman varauksen ja kirjoittaa lokin. '''
    self.kirjaudu()
    varaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(),
    ).json()
    pk = varaus['id']
    vastaus = self.client.post(f'{self.KALENTERI}?poista&pk={pk}')
    self.assertEqual(vastaus.status_code, 200)
    self.assertEqual(vastaus.json(), {'ok': True})
    self.assertFalse(Varaus.objects.filter(pk=pk).exists())
    self.assertTrue(
      LogEntry.objects.filter(
        object_id=str(pk),
        action_flag=DELETION,
      ).exists()
    )
    viesti = LogEntry.objects.get(
      object_id=str(pk),
      action_flag=DELETION,
    ).change_message
    self.assertIn('kuvaus: Viikonloppu mummolassa', viesti)
    self.assertIn('sijainti: Mummolassa', viesti)
    self.assertEqual(self.hae_varaukset().json(), [])
    # def test_poisto_poistaa_varauksen

  def test_toisen_varausta_ei_muokata_eika_poisteta(self):
    ''' Muokkaus ja poisto on rajattu tekijään. '''
    toisen = Varaus.objects.create(
      tekija=self.toinen,
      alku=timezone.now() + timedelta(days=5),
      loppu=timezone.now() + timedelta(days=5, hours=2),
      tarkeys=2,
      sijainti=Sijainti.MUUALLA,
    )
    self.kirjaudu()
    muokkaus = self.client.post(
      f'{self.KALENTERI}?muokkaa&pk={toisen.pk}',
      self.varaus_data(tekija=str(self.kayttaja.pk)),
    )
    poisto = self.client.post(f'{self.KALENTERI}?poista&pk={toisen.pk}')
    self.assertEqual(muokkaus.status_code, 404)
    self.assertEqual(poisto.status_code, 404)
    toisen.refresh_from_db()
    self.assertEqual(toisen.tekija, self.toinen)
    # def test_toisen_varausta_ei_muokata_eika_poisteta

  def test_paallekkainen_aika_hylataan(self):
    ''' Päällekkäinen varaus palauttaa 409. '''
    self.kirjaudu()
    data = self.varaus_data()
    self.assertEqual(
      self.client.post(self.KALENTERI + '?varaa', data).status_code,
      200,
    )
    vastaus = self.client.post(self.KALENTERI + '?varaa', data)
    self.assertEqual(vastaus.status_code, 409)
    self.assertEqual(Varaus.objects.count(), 1)
    # def test_paallekkainen_aika_hylataan

  def test_virheellinen_ajanjakso_hylataan(self):
    ''' Loppu ennen alkua palauttaa 400. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(
        alku='2026-09-21T18:00',
        loppu='2026-09-21T10:00',
      ),
    )
    self.assertEqual(vastaus.status_code, 400)
    self.assertFalse(Varaus.objects.exists())
    # def test_virheellinen_ajanjakso_hylataan

  def test_virheellinen_tarkeys_hylataan(self):
    ''' Tärkeys rajataan välille 1–5. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(tarkeys='9'),
    )
    self.assertEqual(vastaus.status_code, 400)
    # def test_virheellinen_tarkeys_hylataan

  def test_luonti_vaatii_kirjautumisen(self):
    ''' Anonyymi ei voi luoda varausta. '''
    vastaus = self.client.post(
      self.KALENTERI + '?varaa',
      self.varaus_data(),
    )
    self.assertEqual(vastaus.status_code, 302)
    self.assertFalse(Varaus.objects.exists())
    # def test_luonti_vaatii_kirjautumisen

  # class VarausTesti
