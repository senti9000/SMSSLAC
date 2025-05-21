from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.files.storage import default_storage
import os
import logging
from .models import Student, Subject, Grade

@receiver(post_save, sender=Student)
def assign_subjects_on_course_change(sender, instance, created, **kwargs):
    """
    Automatically assign all subjects of the student's course to the student
    when the student is created or when the course field changes.
    """
    if created:
        # On creation, assign all subjects of the course
        if instance.course:
            subjects = Subject.objects.filter(course_id=instance.course)
            for subject in subjects:
                Grade.objects.get_or_create(
                    student=instance,
                    subject=subject,
                    defaults={
                        'semester': '1st',
                        'academic_year': str(timezone.now().year),
                        'is_active': True
                    }
                )
    else:
        # On update, check if course field changed
        try:
            old_instance = Student.objects.get(pk=instance.pk)
        except Student.DoesNotExist:
            old_instance = None

        if old_instance and old_instance.course != instance.course:
            # Course changed, assign all subjects of the new course
            if instance.course:
                subjects = Subject.objects.filter(course_id=instance.course)
                for subject in subjects:
                    Grade.objects.get_or_create(
                        student=instance,
                        subject=subject,
                        defaults={
                            'semester': '1st',
                            'academic_year': str(timezone.now().year),
                            'is_active': True
                        }
                    )

def delete_file(file_field):
    """Helper function to delete file from storage if it exists."""
    if file_field and default_storage.exists(file_field.name):
        try:
            default_storage.delete(file_field.name)
            logging.info(f"Deleted file: {file_field.name}")
        except Exception as e:
            logging.error(f"Error deleting file {file_field.name}: {str(e)}")
    else:
        logging.info(f"File not found or already deleted: {file_field.name if file_field else 'None'}")

@receiver(pre_delete, sender=Student)
def delete_student_files(sender, instance, **kwargs):
    logging.info(f"Pre-delete signal triggered for Student id={instance.id}")
    """Delete all files associated with the Student instance when it is deleted."""
    delete_file(instance.f137)
    delete_file(instance.psa_photocopy)
    delete_file(instance.shs_diploma_photocopy)
    delete_file(instance.good_moral)
    delete_file(instance.honorable_dismissal)
    delete_file(instance.original_tor)
    delete_file(instance.pictures)
    delete_file(instance.profile_pic)

@receiver(pre_save, sender=Student)
def delete_old_files_on_update(sender, instance, **kwargs):
    logging.info(f"Pre-save signal triggered for Student id={instance.id if instance.id else 'new instance'}")
    """
    Delete old files from storage when a file field is updated with a new file or set to None.
    """
    if not instance.pk:
        # New instance, no old files to delete
        return

    try:
        old_instance = Student.objects.get(pk=instance.pk)
    except Student.DoesNotExist:
        return

    file_fields = [
        'f137',
        'psa_photocopy',
        'shs_diploma_photocopy',
        'good_moral',
        'honorable_dismissal',
        'original_tor',
        'pictures',
        'profile_pic',
    ]

    for field in file_fields:
        old_file = getattr(old_instance, field)
        new_file = getattr(instance, field)
        if old_file and old_file != new_file:
            delete_file(old_file)
