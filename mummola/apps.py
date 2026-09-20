''' Django-sovelluksen AppConfig. '''

from django.apps import AppConfig


class MummolaConfig(AppConfig):
  ''' Sovellusmääritys: paketin nimi `mummola`, julkinen nimi Mummola. '''

  name = 'mummola'
  verbose_name = 'Mummola'
  default_auto_field = 'django.db.models.AutoField'

  # class MummolaConfig
