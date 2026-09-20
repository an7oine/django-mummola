''' Salasanan vaihto ja uuden käyttäjän luonti modaalin kautta. '''

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from mummola.nakyma import Kayttajanluontilomake

from .pohja import MummolaTesti

VAATIMUKSET = [
  {
    'NAME': (
      'django.contrib.auth.password_validation.MinimumLengthValidator'
    ),
  },
  {
    'NAME': (
      'django.contrib.auth.password_validation.NumericPasswordValidator'
    ),
  },
]


class SalasananvaihtoTesti(MummolaTesti):
  ''' POST `?vaihda_salasana` ja ensimmäisen kirjautumisen modaali. '''

  def test_ensimmainen_kirjautuminen_avaa_salasanamodaalin(self):
    ''' Ilman CHANGE-lokia kalenterisivulla on `data-avaa-salasana`. '''
    self.kirjaudu()
    vastaus = self.client.get(self.KALENTERI)
    self.assertContains(vastaus, 'id="salasana-modaali"')
    self.assertContains(vastaus, 'data-avaa-salasana')
    self.assertContains(vastaus, 'name="old_password"')
    self.assertContains(vastaus, 'name="new_password1"')
    self.assertContains(vastaus, 'name="new_password2"')
    # def test_ensimmainen_kirjautuminen_avaa_salasanamodaalin

  def test_vaara_vanha_salasana_hylataan(self):
    ''' Vanha salasana tarkistetaan. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?vaihda_salasana',
      {
        'old_password': 'vaara',
        'new_password1': 'Uusi-salasana-9',
        'new_password2': 'Uusi-salasana-9',
      },
    )
    self.assertEqual(vastaus.status_code, 400)
    self.assertIn('virheet', vastaus.json())
    self.kayttaja.refresh_from_db()
    self.assertTrue(self.kayttaja.check_password(self.SALASANA))
    # def test_vaara_vanha_salasana_hylataan

  def test_erilaiset_uudet_salasanat_hylataan(self):
    ''' Uusi salasana on annettava kahdesti samoin. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?vaihda_salasana',
      {
        'old_password': self.SALASANA,
        'new_password1': 'Uusi-salasana-9',
        'new_password2': 'Toinen-salasana-9',
      },
    )
    self.assertEqual(vastaus.status_code, 400)
    self.assertIn('virheet', vastaus.json())
    # def test_erilaiset_uudet_salasanat_hylataan

  @override_settings(AUTH_PASSWORD_VALIDATORS=VAATIMUKSET)
  def test_lyhyt_salasana_hylataan_vaihdossa(self):
    ''' Oman salasanan vaihto noudattaa AUTH_PASSWORD_VALIDATORS-listaa. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?vaihda_salasana',
      {
        'old_password': self.SALASANA,
        'new_password1': '1',
        'new_password2': '1',
      },
    )
    self.assertEqual(vastaus.status_code, 400)
    self.assertIn('virheet', vastaus.json())
    self.kayttaja.refresh_from_db()
    self.assertTrue(self.kayttaja.check_password(self.SALASANA))
    # def test_lyhyt_salasana_hylataan_vaihdossa

  def test_onnistunut_vaihto_paivittaa_salasanan_ja_lokittaa(self):
    ''' Vaihto onnistuu, istunto säilyy ja CHANGE-lokimerkintä syntyy. '''
    self.kirjaudu()
    uusi = 'Uusi-salasana-9'
    vastaus = self.client.post(
      self.KALENTERI + '?vaihda_salasana',
      {
        'old_password': self.SALASANA,
        'new_password1': uusi,
        'new_password2': uusi,
      },
    )
    self.assertEqual(vastaus.status_code, 200)
    self.assertEqual(vastaus.json(), {'ok': True})
    self.kayttaja.refresh_from_db()
    self.assertTrue(self.kayttaja.check_password(uusi))
    self.assertFalse(self.kayttaja.check_password(self.SALASANA))
    sivu = self.client.get(self.KALENTERI)
    self.assertEqual(sivu.status_code, 200)
    self.assertNotContains(sivu, 'data-avaa-salasana')
    self.assertTrue(
      LogEntry.objects.filter(
        user=self.kayttaja,
        content_type=ContentType.objects.get_for_model(self.kayttaja),
        object_id=str(self.kayttaja.pk),
        action_flag=CHANGE,
      ).exists()
    )
    viesti = LogEntry.objects.get(
      object_id=str(self.kayttaja.pk),
      action_flag=CHANGE,
    ).change_message
    self.assertIn('(salasana)', viesti)
    self.assertNotIn(uusi, viesti)
    self.assertNotIn(self.SALASANA, viesti)
    self.client.post(self.ULOS)
    uudelleen = self.client.post(self.SISÄÄN, {
      'username': self.kayttaja.username,
      'password': uusi,
    }, follow=True)
    self.assertTrue(uudelleen.wsgi_request.user.is_authenticated)
    # def test_onnistunut_vaihto_paivittaa_salasanan_ja_lokittaa

  def test_vaihto_vaatii_kirjautumisen(self):
    ''' Anonyymi POST ohjataan kirjautumiseen. '''
    vastaus = self.client.post(
      self.KALENTERI + '?vaihda_salasana',
      {
        'old_password': self.SALASANA,
        'new_password1': 'Uusi-salasana-9',
        'new_password2': 'Uusi-salasana-9',
      },
    )
    self.assertEqual(vastaus.status_code, 302)
    self.assertIn(self.SISÄÄN.rstrip('/'), vastaus.url)
    # def test_vaihto_vaatii_kirjautumisen

  # class SalasananvaihtoTesti


class KayttajanlisaysTesti(MummolaTesti):
  ''' POST `?lisaa_kayttaja` ja Kayttajanluontilomake. '''

  def test_lomake_nakyy_kalenterisivulla(self):
    ''' Lisää käyttäjä -modaali on kalenterisivulla. '''
    self.kirjaudu()
    vastaus = self.client.get(self.KALENTERI)
    self.assertContains(vastaus, 'id="kayttaja-modaali"')
    self.assertContains(vastaus, 'Lisää käyttäjä')
    self.assertContains(vastaus, 'name="username"')
    self.assertContains(vastaus, 'name="password1"')
    self.assertContains(vastaus, 'name="password2"')
    # def test_lomake_nakyy_kalenterisivulla

  def test_henkilokunta_nakee_kanta_linkin(self):
    ''' `is_staff` näkee Kanta-linkin, tavallinen käyttäjä ei. '''
    self.kayttaja.is_staff = True
    self.kayttaja.save(update_fields=['is_staff'])
    self.kirjaudu()
    self.assertContains(self.client.get(self.KALENTERI), 'Kanta')
    self.client.logout()
    self.kirjaudu(self.toinen)
    self.assertNotContains(self.client.get(self.KALENTERI), 'Kanta')
    # def test_henkilokunta_nakee_kanta_linkin

  @override_settings(AUTH_PASSWORD_VALIDATORS=VAATIMUKSET)
  def test_lyhyt_salasana_kelpaa_lisayksessa(self):
    ''' Modaalin kautta lyhyt salasana hyväksytään. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?lisaa_kayttaja',
      {
        'username': 'cecilia',
        'password1': 'x',
        'password2': 'x',
      },
    )
    self.assertEqual(vastaus.status_code, 200)
    data = vastaus.json()
    self.assertTrue(data['ok'])
    uusi = get_user_model().objects.get(username='cecilia')
    self.assertEqual(data['pk'], uusi.pk)
    self.assertTrue(check_password('x', uusi.password))
    self.assertTrue(
      LogEntry.objects.filter(
        user=self.kayttaja,
        content_type=ContentType.objects.get_for_model(uusi),
        object_id=str(uusi.pk),
        action_flag=ADDITION,
      ).exists()
    )
    viesti = LogEntry.objects.get(
      object_id=str(uusi.pk),
      action_flag=ADDITION,
    ).change_message
    self.assertIn('cecilia', viesti)
    self.assertIn('(salasana)', viesti)
    self.assertNotIn(': x', viesti)
    self.client.logout()
    sisaan = self.client.post(self.SISÄÄN, {
      'username': 'cecilia',
      'password': 'x',
    }, follow=True)
    self.assertTrue(sisaan.wsgi_request.user.is_authenticated)
    # def test_lyhyt_salasana_kelpaa_lisayksessa

  def test_erilaiset_salasanat_hylataan(self):
    ''' Salasanakenttien on täsmättävä. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?lisaa_kayttaja',
      {
        'username': 'cecilia',
        'password1': 'sama',
        'password2': 'eri',
      },
    )
    self.assertEqual(vastaus.status_code, 400)
    self.assertFalse(
      get_user_model().objects.filter(username='cecilia').exists()
    )
    # def test_erilaiset_salasanat_hylataan

  def test_varattu_kayttajanimi_hylataan(self):
    ''' Olemassa olevaa käyttäjänimeä ei voi luoda uudelleen. '''
    self.kirjaudu()
    vastaus = self.client.post(
      self.KALENTERI + '?lisaa_kayttaja',
      {
        'username': self.toinen.username,
        'password1': 'x',
        'password2': 'x',
      },
    )
    self.assertEqual(vastaus.status_code, 400)
    self.assertEqual(
      get_user_model().objects.filter(username=self.toinen.username).count(),
      1,
    )
    # def test_varattu_kayttajanimi_hylataan

  def test_lomake_ohittaa_vaatimukset_suoraan(self):
    ''' Kayttajanluontilomake ei aja validate_password-tarkistuksia. '''
    with override_settings(AUTH_PASSWORD_VALIDATORS=VAATIMUKSET):
      lomake = Kayttajanluontilomake(data={
        'username': 'lyhyt',
        'password1': '1',
        'password2': '1',
      })
      self.assertTrue(lomake.is_valid(), lomake.errors)
    # def test_lomake_ohittaa_vaatimukset_suoraan

  def test_lisays_vaatii_kirjautumisen(self):
    ''' Anonyymi ei voi luoda käyttäjiä. '''
    vastaus = self.client.post(
      self.KALENTERI + '?lisaa_kayttaja',
      {
        'username': 'tunkeutuja',
        'password1': 'x',
        'password2': 'x',
      },
    )
    self.assertEqual(vastaus.status_code, 302)
    self.assertFalse(
      get_user_model().objects.filter(username='tunkeutuja').exists()
    )
    # def test_lisays_vaatii_kirjautumisen

  # class KayttajanlisaysTesti
