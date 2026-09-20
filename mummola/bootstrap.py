''' Bootstrap-, FullCalendar- ja sivupohjan mediat ilman django-bootstrap-riippuvuutta. '''

from django_sivumedia import Mediasaate


class Bootstrap(Mediasaate):
  ''' Bootstrap 5 -tyylit ja -skriptit CDN:stä plus paikallinen teema.js. '''

  class Media:
    ''' Bootstrap 5.3.8 CSS/JS ja väriteeman asetus. '''

    versio = '5.3.8'
    css = {'all': [
      f'https://cdn.jsdelivr.net/npm/bootstrap'
      f'@{versio}/dist/css/bootstrap.min.css',
    ]}
    js = [
      f'https://cdn.jsdelivr.net/npm/bootstrap'
      f'@{versio}/dist/js/bootstrap.bundle.min.js',

      # Asettaa `data-bs-theme`-määreen selaimen väriteeman mukaan.
      'mummola/js/teema.js',
    ]

    # class Media

  # class Bootstrap


class BootstrapKuvakkeet(Bootstrap):
  ''' Kuvakefontti mm. FullCalendarin prev/next-painikkeisiin. '''

  class Media:  # pyright: ignore
    ''' Bootstrap Icons -fontti. '''

    versio = '1.11.1'
    css = {'all': [
      f'https://cdn.jsdelivr.net/npm/bootstrap-icons'
      f'@{versio}/font/bootstrap-icons.css',
    ]}

    # class Media

  # class BootstrapKuvakkeet


class SolmuJS(Mediasaate):
  ''' solmu-js: DOM-solmujen esityskytkennät (`data-solmu-esitys`). '''

  class Media:  # pyright: ignore
    ''' solmu-js CDN-paketti. '''

    versio = 'v0.9.x'
    js = [
      f'https://cdn.jsdelivr.net/gh/an7oine/solmu-js'
      f'@{versio}/solmu.min.js',
    ]

    # class Media

  # class SolmuJS


class Kalenteri(BootstrapKuvakkeet):
  ''' FullCalendar 6 Bootstrap 5 -teemalla. '''

  class Media:  # pyright: ignore
    ''' FullCalendarin ydin, kielipaketit, bootstrap5-teema ja kytkentä. '''

    versio = '6.1.10'
    css = {'all': [
      'mummola/css/fullcalendar.css',
    ]}
    js = [
      f'https://cdn.jsdelivr.net/npm/fullcalendar@{versio}/index.global.min.js',
      f'https://cdn.jsdelivr.net/npm/@fullcalendar/core@{versio}/locales-all.global.min.js',
      f'https://cdn.jsdelivr.net/npm/@fullcalendar/bootstrap5@{versio}/index.global.min.js',
      'mummola/js/fullcalendar.js',
    ]

    # class Media

  # class Kalenteri


class Nakyma(Kalenteri, SolmuJS):
  '''
  TemplateView-pohjainen Bootstrap 5 -sivunäkyma.

  `sisaltoaihio` liitetään sivun rungoksi `sivu.html`-pohjassa.
  '''

  sisaltoaihio: str | None = None
  data_alkutilanne: dict | None = None

  @property
  def media_alkutilanne(self):
    ''' Media-tagit JSON-muodossa solmu-js:n dynaamista latausta varten. '''
    media = self.media
    return {
      'css': list(media.render_css()),
      'js': list(media.render_js()),
    }
    # def media_alkutilanne

  def get_context_data(self, **kwargs):
    ''' Lisää Bootstrap-meta, media-alkutilanne ja sisältöaihion polku. '''
    return {
      **super().get_context_data(**kwargs),
      'bootstrap': {
        'viewport': (
          'width=device-width, initial-scale=1, minimum-scale=1'
        ),
        'variteemat': 'light dark',
        'variteema_vaalea': '#EEE',
        'variteema_tumma': '#111',
        'ymparisto': None,
      },
      'data_alkutilanne': self.data_alkutilanne,
      'media_alkutilanne': self.media_alkutilanne,
      'sisaltoaihio': self.sisaltoaihio,
    }
    # def get_context_data

  # class Nakyma
