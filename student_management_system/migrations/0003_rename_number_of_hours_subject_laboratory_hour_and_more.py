# Generated by Django 5.1.7 on 2025-05-02 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_management_system', '0002_alter_subject_department_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subject',
            old_name='number_of_hours',
            new_name='laboratory_hour',
        ),
        migrations.AddField(
            model_name='subject',
            name='lecture_hour',
            field=models.IntegerField(default=0),
        ),
    ]
