# Generated by Django 2.1.7 on 2019-07-31 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_auto_20190730_1655'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estruturaorganizacional',
            name='tipo_estrutura',
            field=models.IntegerField(choices=[(1, 'Raiz'), (2, 'Campus'), (3, 'Comissão'), (4, 'Setor'), (5, 'Polo'), (6, 'Pró-Reitoria')], default=1, verbose_name='Tipo de estrutura organizacional'),
        ),
    ]
