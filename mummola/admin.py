''' Django-ylläpito Varaus-mallille. '''

from django.contrib import admin

from .models import Varaus


@admin.register(Varaus)
class VarausAdmin(admin.ModelAdmin):
  ''' Varausten listaus, suodatus ja haku Django-ylläpidossa. '''

  list_display = (
    'alku', 'loppu', 'sijainti', 'tarkeys',
    'lapset', 'aikuiset', 'koirat', 'tekija',
  )
  list_filter = ('sijainti', 'tarkeys', 'tekija')
  search_fields = ('kuvaus',)
  date_hierarchy = 'alku'

  # class VarausAdmin
