''' Sisäänkirjautumissivun näkyvyys, onnistunut kirjautuminen ja uloskirjaus. '''

from django.contrib.auth import get_user_model

from .pohja import MummolaTesti


class KirjautumissivuTesti(MummolaTesti):
  ''' Kirjautumissivun HTML-rakenne ja uudelleenohjaukset. '''

  def test_sivu_nakyy_anonyymille(self):
    ''' Kirjautumaton käyttäjä saa kirjautumissivun. '''
    vastaus = self.client.get(self.SISÄÄN)
    self.assertEqual(vastaus.status_code, 200)
    self.assertContains(vastaus, 'Mummola')
    self.assertContains(vastaus, 'mummola-kirjautumissivu')
    self.assertContains(vastaus, 'name="username"')
    self.assertContains(vastaus, 'name="password"')
    self.assertContains(vastaus, 'Kirjaudu')
    self.assertNotContains(vastaus, 'tallenna_istunto')
    self.assertNotContains(vastaus, 'Tallenna istunto')
    # def test_sivu_nakyy_anonyymille

  def test_juuri_ohjaa_kirjautumiseen(self):
    ''' Anonyymin `/` ohjautuu sisäänkirjautumiseen. '''
    vastaus = self.client.get('/', follow=False)
    self.assertEqual(vastaus.status_code, 302)
    self.assertEqual(vastaus.url, self.SISÄÄN)
    # def test_juuri_ohjaa_kirjautumiseen

  def test_kalenteri_vaatii_kirjautumisen(self):
    ''' Kalenteri ohjaa kirjautumiseen `next`-parametrilla. '''
    vastaus = self.client.get(self.KALENTERI, follow=False)
    self.assertEqual(vastaus.status_code, 302)
    self.assertIn(self.SISÄÄN.rstrip('/'), vastaus.url)
    self.assertIn('next=', vastaus.url)
    # def test_kalenteri_vaatii_kirjautumisen

  # class KirjautumissivuTesti


class SisaankirjautuminenTesti(MummolaTesti):
  ''' Onnistunut ja epäonnistunut sisäänkirjautuminen lomakkeelta. '''

  def test_vaarat_tunnukset_jattavat_sivulle(self):
    ''' Väärä salasana ei kirjaa sisään. '''
    vastaus = self.client.post(self.SISÄÄN, {
      'username': self.kayttaja.username,
      'password': 'vaara',
    })
    self.assertEqual(vastaus.status_code, 200)
    self.assertFalse(vastaus.wsgi_request.user.is_authenticated)
    self.assertContains(vastaus, 'alert-danger')
    # def test_vaarat_tunnukset_jattavat_sivulle

  def test_onnistunut_kirjautuminen_vie_kalenteriin(self):
    ''' Oikeat tunnukset ohjaavat `/mummola/`-sivulle. '''
    vastaus = self.client.post(self.SISÄÄN, {
      'username': self.kayttaja.username,
      'password': self.SALASANA,
    }, follow=True)
    self.assertTrue(vastaus.wsgi_request.user.is_authenticated)
    self.assertEqual(vastaus.wsgi_request.user, self.kayttaja)
    self.assertEqual(vastaus.request['PATH_INFO'], self.KALENTERI)
    self.assertContains(vastaus, 'id="mummola"')
    # def test_onnistunut_kirjautuminen_vie_kalenteriin

  def test_kirjautunut_juuri_vie_kalenteriin(self):
    ''' Kirjautuneen `/` ohjautuu kalenteriin. '''
    self.kirjaudu()
    vastaus = self.client.get('/', follow=True)
    self.assertEqual(vastaus.request['PATH_INFO'], self.KALENTERI)
    self.assertContains(vastaus, 'id="mummola"')
    # def test_kirjautunut_juuri_vie_kalenteriin

  # class SisaankirjautuminenTesti


class UloskirjautuminenTesti(MummolaTesti):
  ''' Uloskirjautuminen POST-pyyntönä `/kirjaudu/ulos/`. '''

  def test_get_ei_kirjaa_ulos(self):
    ''' Pelkkä GET ei päätä istuntoa (Djangon LogoutView vaatii POST). '''
    self.kirjaudu()
    self.client.get(self.ULOS)
    vastaus = self.client.get(self.KALENTERI)
    self.assertEqual(vastaus.status_code, 200)
    self.assertTrue(vastaus.wsgi_request.user.is_authenticated)
    # def test_get_ei_kirjaa_ulos

  def test_post_kirjaa_ulos(self):
    ''' POST `/kirjaudu/ulos/` päättää istunnon. '''
    self.kirjaudu()
    vastaus = self.client.post(self.ULOS, follow=True)
    self.assertFalse(vastaus.wsgi_request.user.is_authenticated)
    kalenteri = self.client.get(self.KALENTERI, follow=False)
    self.assertEqual(kalenteri.status_code, 302)
    self.assertIn(self.SISÄÄN.rstrip('/'), kalenteri.url)
    # def test_post_kirjaa_ulos

  def test_uloskirjautumisen_jalkeen_voi_kirjautua_uudelleen(self):
    ''' Sama käyttäjä voi kirjautua heti uudelleen. '''
    self.kirjaudu()
    self.client.post(self.ULOS)
    vastaus = self.client.post(self.SISÄÄN, {
      'username': self.kayttaja.username,
      'password': self.SALASANA,
    }, follow=True)
    self.assertTrue(vastaus.wsgi_request.user.is_authenticated)
    self.assertEqual(
      vastaus.wsgi_request.user.username,
      self.kayttaja.username,
    )
    # def test_uloskirjautumisen_jalkeen_voi_kirjautua_uudelleen

  def test_tuntematon_kayttaja_ei_jaa_kantaan_uloskirjauksessa(self):
    ''' Uloskirjaus ei poista käyttäjätietuetta. '''
    self.kirjaudu()
    self.client.post(self.ULOS)
    self.assertTrue(
      get_user_model().objects.filter(pk=self.kayttaja.pk).exists()
    )
    # def test_tuntematon_kayttaja_ei_jaa_kantaan_uloskirjauksessa

  # class UloskirjautuminenTesti
