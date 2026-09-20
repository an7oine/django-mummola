''' Varaus-mallin kentät ja tärkeysväri. '''

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Sijainti(models.TextChoices):
  ''' Varauksen paikka: mummola tai muualla. '''

  MUMMOLA = 'mummola', _('Mummolassa')
  MUUALLA = 'muualla', _('muualla')

  # class Sijainti


class Varaus(models.Model):
  ''' Yksittäinen ajanjakso jaetussa mummolakalenterissa. '''

  alku = models.DateTimeField(_('alku'))
  loppu = models.DateTimeField(_('loppu'))
  tarkeys = models.PositiveSmallIntegerField(
    _('tärkeys'),
    choices=[(n, str(n)) for n in range(1, 6)],
  )
  tekija = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='mummolan_varaukset',
    verbose_name=_('tekijä'),
  )
  kuvaus = models.TextField(_('kuvaus'), blank=True)
  lapset = models.PositiveSmallIntegerField(_('lasten määrä'), default=0)
  sijainti = models.CharField(
    _('sijainti'),
    max_length=16,
    choices=Sijainti.choices,
  )

  class Meta:
    ''' Järjestys alkamisajan mukaan; suomenkieliset verbose-nimet. '''

    verbose_name = _('varaus')
    verbose_name_plural = _('varaukset')
    ordering = ['alku']

    # class Meta

  def __str__(self):
    ''' Näytä sijainti, aikaväli ja tekijä ylläpidossa ja lokissa. '''
    return (
      f'{self.get_sijainti_display()} ({self.alku}–{self.loppu})'
      f' · {self.tekija}'
    )
    # def __str__

  @property
  def vari(self):
    ''' HTML-värikoodi tärkeyden mukaan: 1 vaalea keltainen … 5 punainen. '''
    vaalea_keltainen = (255, 243, 163)
    punainen = (220, 53, 69)
    osuus = (min(max(int(self.tarkeys), 1), 5) - 1) / 4
    rgb = (
      round(vaalea_keltainen[i] + (punainen[i] - vaalea_keltainen[i]) * osuus)
      for i in range(3)
    )
    return '#{:02x}{:02x}{:02x}'.format(*rgb)
    # def vari

  def paallekkaiset(self):
    ''' Palauta muut varaukset, joiden aikaväli leikkaa tätä varausta. '''
    return Varaus.objects.filter(
      alku__lt=self.loppu,
      loppu__gt=self.alku,
    ).exclude(pk=self.pk)
    # def paallekkaiset

  # class Varaus
