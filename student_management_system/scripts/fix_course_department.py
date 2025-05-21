import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'studentmanagement.settings')
django.setup()

from student_management_system.models import Course, Department

def fix_course_department():
    courses = Course.objects.all()
    for course in courses:
        # Check if department_name is a string instead of Department instance
        if isinstance(course.department_name, str):
            dept_name = course.department_name
            department_instance, created = Department.objects.get_or_create(name=dept_name)
            course.department_name = department_instance
            course.save()
            print(f"Fixed Course id={course.id} department_name from string '{dept_name}' to Department instance.")
        else:
            # Also check if department_name is None or invalid
            if course.department_name is None:
                print(f"Course id={course.id} has no department_name assigned.")
            else:
                # department_name is already a Department instance
                pass

if __name__ == "__main__":
    fix_course_department()
