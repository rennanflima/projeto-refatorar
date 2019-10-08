#MODELS QUE SÃO DE USO PÚBLICO

#IMPORTES
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


#MODEL ABSTRATO DE MANUTENÇÃO DE DATAS E HORAS DE CRIAÇÃO E ULTIMA ATUALIZACAO
class DataHoraModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    ultima_modificacao_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Auditavel(DataHoraModel):
    criado_por = models.ForeignKey(User, related_name='%(class)s_requests_created', on_delete=models.PROTECT)
    modificado_por  = models.ForeignKey(User, related_name='%(class)s_requests_modified', on_delete=models.PROTECT)

    class Meta:
        abstract = True