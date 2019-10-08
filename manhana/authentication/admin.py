from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# Register your models here.
class GrupoDocenteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'grupo_pai', 'is_ativo')

class PessoaInline(admin.StackedInline):
    model = Pessoa
    can_delete = False
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (PessoaInline, )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


class TaeProfileAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'siape', 'cargo')

class DocenteProfileAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'siape', 'cargo')

class DiscenteProfileAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'matricula')



admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(GrupoDocente, GrupoDocenteAdmin)
admin.site.register(TaeProfile, TaeProfileAdmin)
admin.site.register(DocenteProfile, DocenteProfileAdmin)
admin.site.register(DiscenteProfile)