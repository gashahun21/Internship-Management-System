# Generated by Django 5.1.7 on 2025-04-12 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=25, null=True, verbose_name='Phone Number'),
        ),
    ]
