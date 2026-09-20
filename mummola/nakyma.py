''' Mummolan kalenterinäkymä ja Yhdiste-toiminnot. '''

from datetime import time

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.urls import path
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.utils.translation import gettext as _, override
from django.views import generic

from yhdiste import Yhdiste

from .bootstrap import Nakyma as BootstrapNakyma
from .models import Sijainti, Varaus


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
    ''' Djangon vakio käyttäjänluontilomake Bootstrap-kenttäluokilla. '''
    return self.bootstrap_lomake(UserCreationForm(data=data))
    # def kayttajalomake

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
    except (TypeError, ValueError):
      tarkeys, lapset = None, None

    if alku is None or loppu is None or loppu <= alku:
      return JsonResponse(
        {'virhe': _('Tarkista ajanjakso.')},
        status=400,
      )
    if tarkeys not in range(1, 6) or lapset is None or lapset < 0:
      return JsonResponse(
        {'virhe': _('Tarkista tärkeys ja lasten määrä.')},
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
    varaus.sijainti = sijainti
    if varaus.paallekkaiset().exists():
      return JsonResponse(
        {'virhe': _('Valittu aika on jo varattu.')},
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
    self.kirjaa(varaus, ADDITION)
    return JsonResponse(self.varauksen_tiedot(varaus))
    # def varaa

  @Yhdiste.toiminto(tyyppi='POST')
  def muokkaa(self, request, *, muokkaa, pk, **kwargs):
    ''' Päivitä oma varaus. '''
    # pylint: disable=unused-argument
    try:
      varaus = Varaus.objects.get(pk=pk, tekija=request.user)
    except (Varaus.DoesNotExist, ValueError):
      return JsonResponse(
        {'virhe': _('Varausta ei löytynyt.')},
        status=404,
      )
    varaus = self.varaus_pyynnolta(request, varaus=varaus)
    if isinstance(varaus, JsonResponse):
      return varaus
    varaus.save()
    self.kirjaa(varaus, CHANGE)
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
    self.kirjaa(varaus, DELETION)
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
    # Kentän verbose_name tallennetaan kääntämättömänä, kuten admin tekee.
    with override(None):
      salasana = str(get_user_model()._meta.get_field('password').verbose_name)
    self.kirjaa(
      lomake.user,
      CHANGE,
      [{'changed': {'fields': [salasana]}}],
    )
    return JsonResponse({'ok': True})
    # def vaihda_salasana

  @Yhdiste.toiminto(tyyppi='POST')
  def lisaa_kayttaja(self, request, *, lisaa_kayttaja, **kwargs):
    ''' Luo uusi käyttäjä Djangon UserCreationForm-luokalla. '''
    # pylint: disable=unused-argument
    lomake = self.kayttajalomake(data=request.POST)
    if not lomake.is_valid():
      return JsonResponse(
        {'virheet': lomake.errors.get_json_data()},
        status=400,
      )
    kayttaja = lomake.save()
    self.kirjaa(kayttaja, ADDITION)
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
