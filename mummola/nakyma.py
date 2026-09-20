''' Mummolan kalenterinäkymä ja Yhdiste-toiminnot. '''

from datetime import time

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.forms import ModelForm
from django.http import JsonResponse
from django.urls import path
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import generic

from yhdiste import Yhdiste

from .bootstrap import Nakyma as BootstrapNakyma
from .models import Sijainti, Varaus


class Kayttajanluontilomake(UserCreationForm):
  '''
  Uuden käyttäjän luonti kalenterin modaalin kautta.

  Ohittaa `AUTH_PASSWORD_VALIDATORS`-tarkistukset (pituus, yleisyys,
  numeerisuus, samankaltaisuus). Käyttäjänimen uniikkius ja
  salasanakenttien vastaavuus tarkistetaan edelleen. Oman salasanan
  vaihto (`PasswordChangeForm`) ja ylläpitopaneeli käyttävät
  Djangon vakio-vaatimuksia.
  '''

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['password1'].help_text = ''
    self.fields['password2'].help_text = ''
    # def __init__

  def _post_clean(self):
    ''' Älä aja `validate_password`-tarkistuksia luonnin yhteydessä. '''
    ModelForm._post_clean(self)
    # def _post_clean

  # class Kayttajanluontilomake


class Nakyma(
  LoginRequiredMixin,
  Yhdiste,
  BootstrapNakyma,
  generic.TemplateView,
):
  '''
  Mummolan kalenterisivu.

  Yhdiste-toiminnot: `?varaukset`, `?varaa`, `?muokkaa`, `?poista`,
  `?vaihda_salasana`, `?lisaa_kayttaja`.
  '''

  template_name = 'mummola/sivu.html'
  sisaltoaihio = 'mummola/kalenteri.html'

  class Media:  # pyright: ignore
    ''' Kalenterin ja käyttäjävalikon paikalliset tyylit ja skriptit. '''

    css = {'all': ['mummola/css/kalenteri.css']}
    js = [
      'mummola/js/esitys.js',
      'mummola/js/kayttaja.js',
    ]

    # class Media

  def bootstrap_lomake(self, lomake):
    ''' Lisää tekstikenttiin Bootstrapin `form-control`-luokka. '''
    for kentta in lomake.fields.values():
      if 'class' not in kentta.widget.attrs:
        kentta.widget.attrs['class'] = 'form-control'
    return lomake
    # def bootstrap_lomake

  def salasanalomake(self, data=None):
    ''' Djangon vakio salasananvaihtolomake Bootstrap-kenttäluokilla. '''
    return self.bootstrap_lomake(
      PasswordChangeForm(user=self.request.user, data=data),
    )
    # def salasanalomake

  def kayttajalomake(self, data=None):
    ''' Käyttäjänluontilomake ilman salasanavaatimuksia, Bootstrap-luokilla. '''
    return self.bootstrap_lomake(Kayttajanluontilomake(data=data))
    # def kayttajalomake

  def on_salasana(self, nimi):
    ''' True, jos kentän nimi viittaa salasanaan. '''
    n = (nimi or '').lower()
    return 'password' in n or 'salasana' in n
    # def on_salasana

  def kentan_otsikko(self, kohde, nimi):
    ''' Palauta kentän verbose_name, tai nimi jos kenttää ei ole. '''
    mallit = []
    if kohde is not None:
      mallit.append(kohde._meta)
    mallit.append(get_user_model()._meta)
    for meta in mallit:
      try:
        return str(meta.get_field(nimi).verbose_name)
      except FieldDoesNotExist:
        continue
    if self.on_salasana(nimi):
      return _('salasana')
    return nimi
    # def kentan_otsikko

  def arvo_tekstiksi(self, nimi, arvo, kentta=None):
    ''' Muotoile kentän arvo lokitekstiin; salasanat ovat `(salasana)`. '''
    if self.on_salasana(nimi):
      return '(salasana)'
    if arvo is None:
      return ''
    if kentta is not None:
      if kentta.choices:
        return str(dict(kentta.flatchoices).get(arvo, arvo))
      if kentta.get_internal_type() == 'DateTimeField':
        try:
          paikallinen = timezone.localtime(arvo)
        except (ValueError, OverflowError, TypeError):
          paikallinen = arvo
        return paikallinen.isoformat(sep=' ', timespec='minutes')
    return str(arvo)
    # def arvo_tekstiksi

  def kooste(self, kohde=None, vanha=None, **lisat):
    '''
    Tekstikooste kentistä muodossa `nimi: arvo; …`.

    Mallista luetaan muut kuin pääavainkentät. Jos `vanha` on sanakirja
    aiemmista arvoista, mukaan otetaan vain muuttuneet kentät. `lisat`
    täydentää tai korvaa (esim. lomakkeen salasanakentät).
    '''
    osat = []
    if kohde is not None:
      for kentta in kohde._meta.concrete_fields:
        if kentta.primary_key:
          continue
        nimi = kentta.name
        arvo = getattr(kohde, nimi)
        if vanha is not None and vanha.get(nimi) == arvo:
          continue
        osat.append(
          f'{self.kentan_otsikko(kohde, nimi)}: '
          f'{self.arvo_tekstiksi(nimi, arvo, kentta)}'
        )
    for nimi, arvo in lisat.items():
      otsikko = self.kentan_otsikko(kohde, nimi)
      kentta = None
      if kohde is not None:
        try:
          kentta = kohde._meta.get_field(nimi)
        except FieldDoesNotExist:
          kentta = None
      osat.append(
        f'{otsikko}: {self.arvo_tekstiksi(nimi, arvo, kentta)}'
      )
    return '; '.join(osat)
    # def kooste

  def mallin_arvot(self, kohde):
    ''' Palauta mallin kenttien nykyiset arvot lokikoosteen vertailuun. '''
    return {
      kentta.name: getattr(kohde, kentta.name)
      for kentta in kohde._meta.concrete_fields
      if not kentta.primary_key
    }
    # def mallin_arvot

  def kirjaa(self, kohde, toiminto, viesti=''):
    ''' Tallenna django.contrib.admin.LogEntry annetusta kohteesta. '''
    return LogEntry.objects.log_actions(
      user_id=self.request.user.pk,
      queryset=[kohde],
      action_flag=toiminto,
      change_message=viesti,
      single_object=True,
    )
    # def kirjaa

  def salasana_vaihdettava(self):
    ''' True, jos käyttäjän muutoslokissa ei ole yhtään CHANGE-merkintää. '''
    kayttaja = self.request.user
    return not LogEntry.objects.filter(
      content_type=ContentType.objects.get_for_model(
        kayttaja,
        for_concrete_model=False,
      ),
      object_id=str(kayttaja.pk),
      action_flag=CHANGE,
    ).exists()
    # def salasana_vaihdettava

  def get_context_data(self, **kwargs):
    ''' Kalenterilomakkeen valinnat, käyttäjälista ja käyttäjävalikon lomakkeet. '''
    return {
      **super().get_context_data(**kwargs),
      'kuvaus': _('Mummolan varauskalenteri'),
      'sivutunnus': _('Mummola'),
      'sijainnit': Sijainti.choices,
      'tarkeysasteet': range(1, 6),
      'kayttajat': get_user_model().objects.order_by('username'),
      'salasanalomake': self.salasanalomake(),
      'kayttajalomake': self.kayttajalomake(),
      'avaa_salasanamodaali': self.salasana_vaihdettava(),
    }
    # def get_context_data

  def varauksen_otsikko(self, varaus):
    ''' Muodosta kalenterissa näytettävä otsikko. '''
    return f'{varaus.get_sijainti_display()} · {varaus.tekija}'
    # def varauksen_otsikko

  def varauksen_tiedot(self, varaus):
    ''' Palauta JSON-aineisto yksittäisestä varauksesta. '''
    alku = timezone.localtime(varaus.alku)
    loppu = timezone.localtime(varaus.loppu)
    koko_paiva = alku.time() == time.min and loppu.time() == time.min
    return {
      'id': varaus.pk,
      'allDay': koko_paiva,
      'title': self.varauksen_otsikko(varaus),
      'start': varaus.alku,
      'end': varaus.loppu,
      'color': varaus.vari,
      'extendedProps': {
        'kuvaus': varaus.kuvaus,
        'tekija': str(varaus.tekija),
        'tekija_id': varaus.tekija_id,
        'oma': varaus.tekija_id == self.request.user.pk,
        'tarkeys': varaus.tarkeys,
        'lapset': varaus.lapset,
        'aikuiset': varaus.aikuiset,
        'koirat': varaus.koirat,
        'sijainti': varaus.sijainti,
        'sijainti_naytto': varaus.get_sijainti_display(),
        'alku': alku.strftime('%Y-%m-%dT%H:%M'),
        'loppu': loppu.strftime('%Y-%m-%dT%H:%M'),
      },
    }
    # def varauksen_tiedot

  def tulkitse_aika(self, arvo):
    ''' Tulkitse aikaleima USE_TZ-asetuksen mukaisesti. '''
    aika = parse_datetime(arvo.replace('T', ' ', 1)) if arvo else None
    if aika is None:
      return None
    if not settings.USE_TZ:
      return aika if timezone.is_naive(aika) else timezone.make_naive(aika)
    if timezone.is_naive(aika):
      return timezone.make_aware(aika)
    return aika
    # def tulkitse_aika

  @Yhdiste.toiminto
  def hae_varaukset(self, request, *, varaukset, start, end, **kwargs):
    ''' Palauta aineisto annetulla välillä näytettävistä varauksista. '''
    # pylint: disable=unused-argument
    alkaen, paattyen = map(self.tulkitse_aika, (start, end))
    return JsonResponse(
      [
        self.varauksen_tiedot(varaus)
        for varaus in Varaus.objects.filter(
          alku__lt=paattyen,
          loppu__gt=alkaen,
        ).select_related('tekija')
      ],
      safe=False,
    )
    # def hae_varaukset

  def varaus_pyynnolta(self, request, varaus=None):
    ''' Lue ja tarkista varauskentät POST-pyynnöstä. '''
    kuvaus = (request.POST.get('kuvaus') or '').strip()
    alku = self.tulkitse_aika(request.POST.get('alku'))
    loppu = self.tulkitse_aika(request.POST.get('loppu'))
    sijainti = request.POST.get('sijainti')

    try:
      tarkeys = int(request.POST.get('tarkeys'))
      lapset = int(request.POST.get('lapset') or 0)
      aikuiset = int(request.POST.get('aikuiset') or 0)
      koirat = int(request.POST.get('koirat') or 0)
    except (TypeError, ValueError):
      tarkeys = lapset = aikuiset = koirat = None

    if alku is None or loppu is None or loppu <= alku:
      return JsonResponse(
        {'virhe': _('Tarkista ajanjakso.')},
        status=400,
      )
    if (
      tarkeys not in range(1, 6)
      or None in (lapset, aikuiset, koirat)
      or min(lapset, aikuiset, koirat) < 0
    ):
      return JsonResponse(
        {'virhe': _('Tarkista tärkeys ja osallistujamäärät.')},
        status=400,
      )
    if sijainti not in Sijainti.values:
      return JsonResponse(
        {'virhe': _('Tarkista sijainti.')},
        status=400,
      )

    if varaus is None:
      varaus = Varaus(tekija=request.user)
    else:
      try:
        tekija = get_user_model().objects.get(
          pk=int(request.POST.get('tekija')),
        )
      except (TypeError, ValueError, get_user_model().DoesNotExist):
        return JsonResponse(
          {'virhe': _('Tarkista tekijä.')},
          status=400,
        )
      varaus.tekija = tekija
    varaus.alku = alku
    varaus.loppu = loppu
    varaus.tarkeys = tarkeys
    varaus.kuvaus = kuvaus
    varaus.lapset = lapset
    varaus.aikuiset = aikuiset
    varaus.koirat = koirat
    varaus.sijainti = sijainti
    if varaus.paallekkaiset().exists():
      return JsonResponse(
        {'virhe': _('Sinulla on jo varaus valitulla aikavälillä.')},
        status=409,
      )
    return varaus
    # def varaus_pyynnolta

  @Yhdiste.toiminto(tyyppi='POST')
  def varaa(self, request, *, varaa, **kwargs):
    ''' Luo uusi varaus jaettuun kalenteriin. '''
    # pylint: disable=unused-argument
    varaus = self.varaus_pyynnolta(request)
    if isinstance(varaus, JsonResponse):
      return varaus
    varaus.save()
    self.kirjaa(varaus, ADDITION, self.kooste(varaus))
    return JsonResponse(self.varauksen_tiedot(varaus))
    # def varaa

  @Yhdiste.toiminto(tyyppi='POST')
  def muokkaa(self, request, *, muokkaa, pk, **kwargs):
    ''' Päivitä oma varaus. '''
    # pylint: disable=unused-argument
    try:
      varaus = Varaus.objects.select_related('tekija').get(
        pk=pk, tekija=request.user,
      )
    except (Varaus.DoesNotExist, ValueError):
      return JsonResponse(
        {'virhe': _('Varausta ei löytynyt.')},
        status=404,
      )
    vanha = self.mallin_arvot(varaus)
    varaus = self.varaus_pyynnolta(request, varaus=varaus)
    if isinstance(varaus, JsonResponse):
      return varaus
    varaus.save()
    self.kirjaa(varaus, CHANGE, self.kooste(varaus, vanha=vanha))
    return JsonResponse(self.varauksen_tiedot(varaus))
    # def muokkaa

  @Yhdiste.toiminto(tyyppi='POST')
  def poista(self, request, *, poista, pk, **kwargs):
    ''' Poista oma varaus. '''
    # pylint: disable=unused-argument
    try:
      varaus = Varaus.objects.get(pk=pk, tekija=request.user)
    except (Varaus.DoesNotExist, ValueError):
      return JsonResponse(
        {'virhe': _('Varausta ei löytynyt.')},
        status=404,
      )
    self.kirjaa(varaus, DELETION, self.kooste(varaus))
    varaus.delete()
    return JsonResponse({'ok': True})
    # def poista

  @Yhdiste.toiminto(tyyppi='POST')
  def vaihda_salasana(self, request, *, vaihda_salasana, **kwargs):
    ''' Vaihda salasana Djangon PasswordChangeForm-luokalla. '''
    # pylint: disable=unused-argument
    lomake = self.salasanalomake(data=request.POST)
    if not lomake.is_valid():
      return JsonResponse(
        {'virheet': lomake.errors.get_json_data()},
        status=400,
      )
    lomake.save()
    update_session_auth_hash(request, lomake.user)
    self.kirjaa(
      lomake.user,
      CHANGE,
      self.kooste(password=lomake.cleaned_data.get('new_password1')),
    )
    return JsonResponse({'ok': True})
    # def vaihda_salasana

  @Yhdiste.toiminto(tyyppi='POST')
  def lisaa_kayttaja(self, request, *, lisaa_kayttaja, **kwargs):
    ''' Luo uusi käyttäjä ilman salasanan monimutkaisuusvaatimuksia. '''
    # pylint: disable=unused-argument
    lomake = self.kayttajalomake(data=request.POST)
    if not lomake.is_valid():
      return JsonResponse(
        {'virheet': lomake.errors.get_json_data()},
        status=400,
      )
    kayttaja = lomake.save()
    self.kirjaa(
      kayttaja,
      ADDITION,
      self.kooste(
        username=kayttaja.username,
        password=lomake.cleaned_data.get('password1'),
      ),
    )
    return JsonResponse({
      'ok': True,
      'pk': kayttaja.pk,
      'nimi': str(kayttaja),
    })
    # def lisaa_kayttaja

  # class Nakyma


# Protonin `django.osoitteisto`-entry point liittää tämän `/mummola/`-polkuun.
urlpatterns = [
  path('', Nakyma.as_view(), name='index'),
]
