# Generated by Django 2.2.16 on 2022-08-27 14:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0009_comment'),
    ]

    operations = [
        migrations.RenameField(
            model_name='comment',
            old_name='created',
            new_name='pub_date',
        ),
    ]
