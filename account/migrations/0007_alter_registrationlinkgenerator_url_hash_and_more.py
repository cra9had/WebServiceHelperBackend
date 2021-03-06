# Generated by Django 4.0.1 on 2022-02-08 17:48

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0006_alter_registrationlinkgenerator_url_hash_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registrationlinkgenerator',
            name='url_hash',
            field=models.CharField(default='ea6956f36f3448c19b337035f40139f5', editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True, region=None, verbose_name='Номер телефона'),
        ),
    ]
