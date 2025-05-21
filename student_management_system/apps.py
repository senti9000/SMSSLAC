from django.apps import AppConfig

class StudentManagementSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'student_management_system'

    def ready(self):
        import student_management_system.signals
