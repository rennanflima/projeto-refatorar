from django.db import models
from django.db.models import Q


class GrupoDocenteQuerySet(models.QuerySet):
    def filtra_hierarquia(self, grupo):
        return self.filter((Q(grupo_pai=grupo) | Q(pk=grupo.pk)) & Q(is_ativo=True))


class ServidorQuerySet(models.QuerySet):
    def encontra_pela_pessoa(self, pessoa):
        return self.filter(pessoa=pessoa, is_ativo=True)


class DiscenteQuerySet(models.QuerySet):
    def encontra_pela_pessoa(self, pessoa):
        return self.filter(pessoa=pessoa, is_ativo=True)
