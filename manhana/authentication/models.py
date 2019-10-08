from django.db import models
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from manhana.core.models.parametro import AreaContratacao, EstruturaOrganizacional
from .choices import *
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from datetime import date


# Create your models here.
class Pessoa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    cpf = models.CharField('CPF', max_length=15, unique=True, blank=True, null=True)
    data_nascimento = models.DateField('Data de nascimento', blank=True, null=True)
    nome_mae = models.CharField('Nome da mãe', max_length=50, blank=True, null=True)
    nome_pai = models.CharField('Nome do pai', max_length=50, blank=True, null=True)
    sexo = models.CharField('Sexo', max_length=2, choices=TIPO_SEXO, default='F')
    registro_geral = models.CharField('Número do Registro Geral', max_length=15, blank=True, null=True)
    rg_orgao_expedidor = models.CharField('Órgão expedidor do RG', max_length=10, blank=True, null=True)
    rg_data_expedicao = models.DateField('Data de expedição do RG', blank=True, null=True)
    rg_uf = models.IntegerField('UF do RG', choices=TIPO_UF, blank=True, null=True)
    grupo_sanguineo = models.IntegerField('Grupo sanguíneo', choices=TIPO_GRUPO_SANGUINEO, blank=True, null=True)
    id_pessoa_sig = models.IntegerField('ID da pessoa nos SIGs', unique=True, blank=True, null=True)

    def __str__(self):
        return "%s" % self.user

    def idade(self):
        today = date.today()
        diff = today - self.data_nascimento
        days = diff.days
        years, days = days // 365, days % 365
        months, days = days // 30, days % 30
        return "{} anos, {} meses e {} dias".format(years, months, days)


@receiver(post_save, sender=User)
def create_or_update_user_pessoa(sender, instance, created, **kwargs):
    if created:
        Pessoa.objects.create(user=instance)
    instance.pessoa.save()
    

class ServidorProfile(models.Model):
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE)
    siape = models.CharField('Siape', unique=True, max_length=100, blank=True, null=True)
    id_servidor_sig = models.IntegerField('ID do servidor nos SIGs', unique=True, blank=True, null=True)
    unidade_lotacao = models.ForeignKey(EstruturaOrganizacional, related_name='unidade_lotacao_organizacional_fk', on_delete=models.PROTECT, default="INDEFINIDO")
    unidade_exercicio = models.ForeignKey(EstruturaOrganizacional, related_name='unidade_exercicio_organizacional_fk', on_delete=models.PROTECT, default="INDEFINIDO")
    unidade_responsavel = models.ForeignKey(EstruturaOrganizacional, related_name='unidade_responsavel_organizacional_fk', on_delete=models.PROTECT)
    cargo = models.CharField('Cargo', max_length=100)
    tipo_servidor = models.CharField('Tipo de servidor', max_length=200)
    categoria = models.CharField('Categoria', max_length=200)
    regime_trabalho = models.CharField('Regime de trabalho', max_length=100)
    situacao = models.CharField('Situação', max_length=200)
    titulacao = models.CharField('Titulação', max_length=200)
    is_ativo = models.BooleanField('Ativo?', default=True,  help_text='Indica que o perfil será tratado como ativo. Ao invés de excluir perfis, desmarque isso.')

    def __str__(self):
        return f"{self.pessoa.user.get_full_name()} ({self.siape}): {self.cargo}"


class TaeProfile(ServidorProfile):

    class Meta:
        verbose_name = 'Técnico Administrativo'
        verbose_name_plural = 'Técnicos Administrativos'


class GrupoDocente(models.Model):
    nome = models.CharField('Nome', max_length=150)
    descricao = models.CharField('Descrição', blank=True, null=True, max_length=255)
    is_ativo = models.BooleanField('Ativo?', default=True,  help_text='Indica que o grupo será tratado como ativo. Ao invés de excluir grupos, desmarque isso.')
    grupo_pai = models.ForeignKey('self', on_delete=models.PROTECT, related_name='grupos_pai', null=True, blank=True)
    ch_semanal = models.DecimalField('Carga horária semanal', max_digits=10, decimal_places=2, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Grupo do docente'
        verbose_name_plural = 'Grupos dos docentes'
        ordering = ('nome',)

    def __str__(self):
        return self.nome

class DocenteProfile(ServidorProfile):
    lattes = models.URLField('Link do lattes', unique=True, help_text='Ex: http://lattes.cnpq.br/2076449581151181', blank=True, null=True)
    grupo = models.ForeignKey(GrupoDocente, verbose_name='Grupo em função da carga horária', on_delete=models.PROTECT, related_name='docentes_grupo', blank=True, null=True)
    area_contratacao = models.ForeignKey(AreaContratacao, on_delete=models.PROTECT, related_name='docentes_area_contratacao', blank=True, null=True)

    class Meta:
        verbose_name = 'Docente'
        verbose_name_plural = 'Docentes'


class DiscenteProfile(models.Model):
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE)
    matricula = models.CharField('Matrícula', unique=True, max_length=100, blank=True, null=True)
    id_discente_sig = models.IntegerField('ID do discente nos SIGAA', unique=True, blank=True, null=True)
    is_ativo = models.BooleanField('Ativo?', default=True, help_text='Indica que o perfil será tratado como ativo. Ao invés de excluir perfis, desmarque isso.')

    class Meta:
        verbose_name = 'Discente'
        verbose_name_plural = 'Discentes'











