# Generated by Django 2.2.4 on 2019-08-27 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_auto_20190827_1434'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='vinculoservidorunidade',
            constraint=models.UniqueConstraint(condition=models.Q(is_ativo=True), fields=('unidade', 'servidor'), name='unique_active_vinculo_servidor'),
        ),
    ]
