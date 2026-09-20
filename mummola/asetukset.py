''' Protonin asetuslaajennos (`django.asetukset`-entry point). '''

# Kirjautunut käyttäjä juuriosoitteesta (`/`) kalenteriin.
LOGIN_REDIRECT_URL = '/mummola/'

# Istunnot tietokantaan. Protoni valitsee oletuksen sen mukaan, onko
# `DATABASES` määritetty, mutta tekee sen ennen laajennosten latausta,
# jolloin pelkkä `DATABASE_URL` ei vielä näy ja oletukseksi jäisi eväste.
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# Staattiset tiedostot suoraan Gunicornilta (Railway; ei erillistä proxya).
# Protonin oma whitenoise-laajennos lisää ohjaimen vain
# `WHITENOISE_RUNSERVER`-lipulla ja asettaa poistetun
# `STATICFILES_STORAGE`-asetuksen, joten kytketään ohjain tässä.
try:
  import whitenoise
except ImportError:
  pass
else:
  del whitenoise
  whitenoise_ohjain = 'whitenoise.middleware.WhiteNoiseMiddleware'
  if whitenoise_ohjain not in MIDDLEWARE:  # noqa: F821
    # Heti SecurityMiddlewaren jälkeen, ks. WhiteNoise-dokumentaatio.
    MIDDLEWARE.insert(1, whitenoise_ohjain)  # noqa: F821
  del whitenoise_ohjain

# Yksikkötestit käyttävät muistissa olevaa SQLitea, jotta ne eivät
# vaadi Railwayn Postgresia eivätkä peri paikallisen MySQL-kannan
# `OPTIONS`-arvoja (`sql_mode`) väärän moottorin päälle.
import sys
if 'test' in sys.argv:
  DATABASES = {  # noqa: F821
    'default': {
      'ENGINE': 'django.db.backends.sqlite3',
      'NAME': ':memory:',
    }
  }
# else:
#   DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'  # noqa: F821

