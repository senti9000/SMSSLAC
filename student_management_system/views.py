import logging
import os
import random
import json
from collections import defaultdict
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Student, Course, Subject, Grade, Department
from .forms import (
    AddStudentSubjectForm,
    ChangeStudentSubjectForm,
    StudentProfileForm,
    UserRegistrationForm,
    CourseForm,
    SubjectForm,
    StaffRegistrationForm,
    SubjectSelectForm,
    GradeForm,
    AccountEditForm,
)
from .tokens import account_activation_token

User = get_user_model()

@login_required
@require_POST
def update_subject_status_ajax(request):
    student_id = request.POST.get('student_id')
    subject_id = request.POST.get('subject_id')
    new_status = request.POST.get('new_subject_status')

    if not student_id or not subject_id or not new_status:
        return JsonResponse({'success': False, 'error': 'Missing required parameters.'})

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found.'})

    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subject not found.'})

    # Update the subject status for this student-subject grade
    try:
        grade = student.grades.get(subject=subject, is_active=True)
        grade.status = new_status
        grade.save()
    except Grade.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Grade record not found for this student and subject.'})

    return JsonResponse({'success': True, 'new_status': new_status, 'subject_id': subject_id})

# Create your views here.

# Added decorators for user role checks
def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a superuser (admin),
    redirects to login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def student_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a student (not staff or superuser),
    redirects to login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or getattr(request.user, 'is_staff_member', False):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def staff_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff member (not superuser),
    redirects to login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or not getattr(request.user, 'is_staff_member', False):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@csrf_exempt
def drop_student_subject_ajax(request):
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')

        if not student_id or not subject_id:
            return JsonResponse({'success': False, 'error': 'Missing student_id or subject_id'})

        # Do not update subject.status here to avoid affecting other students

        # Mark related grades as inactive and update their status to 'Drop'
        grades = Grade.objects.filter(student_id=student_id, subject_id=subject_id, is_active=True)
        for grade in grades:
            grade.is_active = False
            grade.status = 'Drop'
            grade.save()

        return JsonResponse({'success': True, 'message': 'Grades marked inactive and status updated to Drop for the student.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def login_user(request):
    if request.user.is_authenticated:
        messages.error(request, "You are already logged in.")
        user = request.user
        if user.is_superuser:
            return redirect('admin_dashboard')
        elif hasattr(user, 'is_staff_member') and user.is_staff_member:
            return redirect('staff_dashboard')
        else:
            return redirect('student_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            # If authentication fails with username, try with email
            if user is None:
                try:
                    student = Student.objects.get(email=username)
                    if student.user:  # Check if student has a related user
                        user = authenticate(request, username=student.user.username, password=password)
                    else:
                        messages.error(request, 'No user account associated with this email')
                        logging.warning(f"Login failed: No user account associated with email {username}")
                except Student.DoesNotExist:
                    messages.error(request, 'Invalid email or password')
                    logging.warning(f"Login failed: Invalid email {username}")
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome, {username}!')
                if user.is_superuser:
                    return redirect('admin_dashboard')  # Redirect to admin dashboard
                elif hasattr(user, 'is_staff_member') and user.is_staff_member:
                    return redirect('staff_dashboard')  # Redirect to staff dashboard
                else:
                    return redirect('student_dashboard')  # Redirect to student dashboard
            else:
                messages.error(request, 'Invalid username or password.')
                logging.warning(f"Login failed: Invalid username {username}")
        else:
            # Explicitly return the form with errors if form is invalid
            return render(request, 'SMS(logon).html', {'form': form})
    else:
        form = AuthenticationForm()
    return render(request, 'SMS(logon).html', {'form': form})

@login_required
@staff_required
def staff_dashboard(request):
    return render(request, 'SMS(staffdash).html')

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')  # Redirect to the login URL name

@admin_required
@login_required  # Ensure only admin users can access this view
def admin_dashboard(request):
    return render(request, 'SMS(course).html', {'user': request.user})

@student_required
@login_required  # Ensure only student users can access this view
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    departments = Department.objects.all()
    domain = request.get_host()
    return render(request, 'SMS.html', {'user': request.user, 'student': student, 'departments': departments, 'domain': domain})

@admin_required
@login_required(login_url='login')
def SMScourse(request):
    return render(request, "SMS(course).html")

@login_required
@admin_required
def SMScourse_save(request):
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        course_name = request.POST.get("course_name")
        credits = request.POST.get("credits")
        department_name = request.POST.get("department_name")

        if course_id and course_name and credits and department_name:  # Check if all fields are provided
            try:
                from .models import Department
                department_instance, created = Department.objects.get_or_create(name=department_name)
                course_model = Course(
                    course_id=course_id,
                    name=course_name,
                    credits=credits,
                    department_name=department_instance
                )
                course_model.save()
                messages.success(request, "Course Added Successfully")
                return redirect('SMScourse')  # Redirect to show the new course
            except Exception as e:
                messages.error(request, "Failed to Add Course: " + str(e))
                return redirect('SMScourse')  # Redirect to the form page
        else:
            messages.error(request, "All fields are required")
            return redirect('SMScourse')  # Redirect to the form page

    # If the request is GET, retrieve all courses
    courses = Course.objects.all()  # Retrieve all courses from the database
    return render(request, 'SMS(Vcourse).html', {'courses': courses})

@login_required
@admin_required
def delete_course(request, course_id):
    try:
        # Fetch the course instance using the course_id
        course = get_object_or_404(Course, id=course_id)
        course.delete()
        messages.success(request, "Course deleted successfully.")
    except Exception as e:
        messages.error(request, "Failed to delete course: " + str(e))
    return redirect('SMScourse')  # Redirect to the course management page

@login_required
@admin_required
def course_record(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'SMS(Crecord).html', {'course': course})

@login_required
@admin_required
def course_list(request):
    search_query = request.GET.get('search', '')
    courses = Course.objects.all()  # Start with all courses

    if search_query:
        # Attempt to filter by credits as an integer if possible
        try:
            credits_query = int(search_query)
            courses = courses.filter(
                Q(course_id__icontains=search_query) |
                Q(name__icontains=search_query) |
                Q(credits=credits_query) |  # Match exact credits
                Q(department_name__name__icontains=search_query)
            )
        except ValueError:
            # If conversion fails, just filter by string fields
            courses = courses.filter(
                Q(course_id__icontains=search_query) |
                Q(name__icontains=search_query) |
                Q(department_name__name__icontains=search_query)
            )

    return render(request, 'SMS(Vcourse).html', {'courses': courses})

@login_required
@admin_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk)  # Retrieve the course by primary key
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)  # Bind the form to the course instance
        if form.is_valid():
            form.save()  # Save the updated course
            messages.success(request, "Course edited successfully.")
            return redirect('course_list')  # Redirect to the course list after saving
    else:
        form = CourseForm(instance=course)  # Create a form instance with the course data

    return render(request, 'SMS(editcor).html', {'form': form, 'course': course})  # Render the edit template 

@login_required(login_url='login')
@admin_required
def SMSstudent(request):
    students = Student.objects.filter(user__is_superuser=False)
    form = StudentProfileForm()
    return render(request, 'SMS(student).html', {'students': students, 'form': form})

@login_required
@admin_required
def add_student_save(request):
    form = StudentProfileForm()
    # Order students by course name, year level, last name, first name for orderly display
    students = Student.objects.order_by('course__name', 'year_level', 'last_name', 'first_name')

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES)
        user_email = request.POST.get('user_email', '').strip()

        if user_email:
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                messages.error(request, f"No user account found with email: {user_email}")
                return render(request, 'SMS(student).html', {'form': form, 'students': students})
        else:
            user = None

        if form.is_valid():
            try:
                student = form.save(commit=False)
                # Convert department_name string to Department instance if needed
                department_name = form.cleaned_data.get('department_name')
                if isinstance(department_name, str):
                    department_instance = Department.objects.filter(name=department_name).first()
                    if department_instance:
                        student.department_name = department_instance
                else:
                    student.department_name = department_name

                if user:
                    student.user = user
                    student.email = user.email
                    student.username = user.username

                # Automatically set academic_year to current year if not provided
                if not student.academic_year:
                    from django.utils import timezone
                    student.academic_year = str(timezone.now().year)

                # No need to manually assign course, form.save() will handle it
                student.save()
                if user:
                    messages.success(request, "Student added successfully and linked to user account!")
                else:
                    messages.success(request, "Student added successfully ") #without linking to a user account!
                return redirect('SMSstudent')
            except Exception as e:
                logging.error(f"Error saving student: {str(e)}")
                messages.error(request, f"Error saving student: {str(e)}")
                return render(request, 'SMS(student).html', {'form': form, 'students': students})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return render(request, 'SMS(student).html', {'form': form, 'students': students})

    # For GET or other methods, render the student list and form
    grouped_students = defaultdict(list)
    for student in students:
        course_name = student.course.name if student.course else "No Course Assigned"
        grouped_students[course_name].append(student)

    # Convert defaultdict to regular dict for template context
    grouped_students = dict(grouped_students)

    return render(request, 'SMS(Vstudent).html', {'form': form, 'students': students, 'grouped_students': grouped_students})




@login_required
@admin_required
def delete_student(request, student_id):
    try:
        # Retrieve the student or return a 404 if it doesn't exist
        student = Student.objects.get(id=student_id)
        student.delete()  # Delete the student
        messages.success(request, "Student deleted successfully.")
    except Student.DoesNotExist:
        messages.error(request, "Student not found.")
    except Exception as e:
        messages.error(request, "Failed to delete student: " + str(e))
    return redirect('student_list')  # Redirect to the student management page


@login_required
@admin_required
def change_student_subject(request, student_id, old_subject_id):
    student = get_object_or_404(Student, pk=student_id)
    old_subject = get_object_or_404(Subject, pk=old_subject_id)

    if request.method == 'POST':
        form = ChangeStudentSubjectForm(request.POST, student=student, old_subject=old_subject)
        if form.is_valid():
            new_subject = form.cleaned_data['new_subject']
            year_level = form.cleaned_data['year_level']
            semester = form.cleaned_data['semester']

            # Remove old subject's grade if exists
            student.grades.filter(subject=old_subject).delete()

            # Add new subject's grade with specified year_level and semester
            from .models import Grade
            Grade.objects.get_or_create(
                student=student,
                subject=new_subject,
                defaults={
                    'semester': semester,
                    'year_level': year_level,
                    'academic_year': timezone.now().year
                }
            )

            messages.success(request, f"Subject changed from {old_subject.subject_name} to {new_subject.subject_name} successfully.")
            return redirect('student_record', pk=student_id)
    else:
        form = ChangeStudentSubjectForm(student=student, old_subject=old_subject)

    return render(request, 'SMS(subject_select).html', {
        'form': form,
        'student': student,
        'old_subject': old_subject
    })


from django.core.paginator import Paginator

@login_required
@admin_required
def student_list(request):
    try:
        search_query = request.GET.get('search', '')
        all_students = Student.objects.all()  # Full list of all students
        students = all_students  # Start with all students for filtering
        
        if search_query:
            # Create a query that searches across multiple fields
            query = Q()
            search_fields = [
                'student_number__icontains',
                'first_name__icontains',
                'middle_Name__icontains',
                'last_name__icontains',
                'user__email__icontains',
                'course__name__icontains',
                'student_status__icontains',
                'year_level__icontains',
                'address__icontains',
                'phone__icontains',
                'school_name__icontains'
            ]
            
            # Build the OR conditions for all search fields
            for field in search_fields:
                query |= Q(**{field: search_query})
            
            # Also try searching by ID if query is numeric
            if search_query.isdigit():
                query |= Q(id=search_query)
            
            students = students.filter(query)
        
        # Order students by year level for grouping
        students = students.order_by('year_level')
        
        # Group students by course name
        from collections import defaultdict
        grouped_students = defaultdict(list)
        for student in students:
            course_name = student.course.name if student.course else "No Course Assigned"
            grouped_students[course_name].append(student)
        
        # Convert defaultdict to regular dict for template context
        grouped_students = dict(grouped_students)
        
        # Fetch grades for all students in the list
        from .models import Grade
        grades = Grade.objects.filter(student__in=students).select_related('subject', 'student')

        # Map student id to list of subjects
        student_subjects_map = {}
        for grade in grades:
            if grade.student_id not in student_subjects_map:
                student_subjects_map[grade.student_id] = []
            student_subjects_map[grade.student_id].append(grade.subject)

        return render(request, 'SMS(Vstudent).html', {
            'grouped_students': grouped_students,
            'student_subjects_map': student_subjects_map
        })
    except Exception as e:
        logging.error(f"Exception in student_list view: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while loading the student list. Please try again later.")
        return redirect('student_dashboard')

@login_required
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)

    def activate_grades_for_student(student):
        from .models import Grade
        student_semester = getattr(student, 'semester', None)
        student_academic_year = getattr(student, 'academic_year', None)
        grades_qs = Grade.objects.filter(student=student)
        if student_semester and student_academic_year:
            grades_to_activate = grades_qs.filter(year_level=student.year_level, semester=student_semester, academic_year=student_academic_year)
        elif student_semester:
            grades_to_activate = grades_qs.filter(year_level=student.year_level, semester=student_semester)
        elif student_academic_year:
            grades_to_activate = grades_qs.filter(year_level=student.year_level, academic_year=student_academic_year)
        else:
            grades_to_activate = grades_qs.filter(year_level=student.year_level)
        count = grades_to_activate.update(is_active=True)
        logging.info(f"Activated {count} grades for student id {student.id} with year_level {student.year_level}, semester {student_semester}, and academic_year {student_academic_year}")

    if request.method == 'POST':
        logging.info(f"edit_student POST request received for student id {pk}")
        logging.info(f"POST data keys: {list(request.POST.keys())}")
        form = StudentProfileForm(request.POST, request.FILES, instance=student, user=request.user)
        if form.is_valid():
            student = form.save(commit=False)
            picture_fields = [
                'f137', 'psa_photocopy', 'shs_diploma_photocopy', 'good_moral',
                'honorable_dismissal', 'original_tor', 'pictures', 'profile_pic'
            ]
            for field_name in picture_fields:
                clear_field_name = f"{field_name}-clear"
                if clear_field_name in request.POST:
                    old_file = getattr(student, field_name)
                    if old_file:
                        file_path = os.path.join(settings.MEDIA_ROOT, old_file.name)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                                logging.info(f"Deleted file {file_path} for field {field_name}")
                            except Exception as e:
                                logging.error(f"Error deleting file {file_path}: {str(e)}")
                    setattr(student, field_name, None)

            department_name = form.cleaned_data.get('department_name')
            if isinstance(department_name, str):
                department_instance = Department.objects.filter(name=department_name).first()
                if department_instance:
                    student.department_name = department_instance
            else:
                student.department_name = department_name

            student.course = form.cleaned_data.get('course')

            # Automatically set academic_year to current year if not provided
            if not student.academic_year:
                from django.utils import timezone
                student.academic_year = str(timezone.now().year)

            student.save()

            activate_grades_for_student(student)

            logging.info(f"Form saved for student id {pk}, pictures field is now: {student.pictures}")
            messages.success(request, "Student edited successfully.")

            return redirect('student_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, 'SMS(editstu).html', {
        'form': StudentProfileForm(instance=student, user=request.user),
        'student': student
    })

@login_required
@student_required
def student_profile(request):
    # Get the student profile for the current user
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "No student profile found for the current user.")
        return redirect('student_dashboard')  # Redirect to a safe page

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    # For GET requests, show the profile form with all fields
    form = StudentProfileForm(instance=student, user=request.user)

    return render(request, 'SMS(profile).html', {
        'form': form,
        'student': student
    })
    
@admin_required
@login_required(login_url='login')
def SMSsubject(request):
    search_query = request.GET.get('search', '')
    subjects = Subject.objects.select_related('course_id').all()  # Start with all subjects and fetch related course data

    import logging
    logging.debug(f"SMSsubject: Total subjects found: {subjects.count()}")
    for subj in subjects:
        logging.debug(f"SMSsubject: Subject: {subj.subject_name}, Year Level: {subj.year_level}, Course: {subj.course_id.name if subj.course_id else 'None'}")

    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )

    logging.debug(f"SMSsubject: Subjects after filtering: {subjects.count()}")
    for subj in subjects:
        logging.debug(f"SMSsubject: Filtered Subject: {subj.subject_name}, Year Level: {subj.year_level}, Course: {subj.course_id.name if subj.course_id else 'None'}")

    grouped_by_year = {}
    for subject in subjects:
        year = subject.year_level if subject.year_level else "Unassigned Year"
        course_name = subject.course_id.name if subject.course_id else "Unassigned Courses"
        if year not in grouped_by_year:
            grouped_by_year[year] = {}
        if course_name not in grouped_by_year[year]:
            grouped_by_year[year][course_name] = []
        grouped_by_year[year][course_name].append(subject)

    courses = Course.objects.all()
    form = SubjectForm()

    return render(request, 'SMS(subject).html', {'grouped_by_year': grouped_by_year, 'courses': courses, 'form': form})

from .models import Department

from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import SubjectForm
from .models import Department, Subject
from django.db.models import Q

@admin_required
@login_required
def SMSsubjectsave(request):
    if request.method == "POST":
        subject_name = request.POST.get("subject_name")
        subject_code = request.POST.get("subject_code")
        credits = request.POST.get("credits")
        department_name = request.POST.get("department_name")
        semester_offered = request.POST.get("semester_offered")
        professor_name = request.POST.get("professor_name")
        year_level = request.POST.get("year_level")
        course_id = request.POST.get("course_id")
        lecture_hour = request.POST.get("lecture_hour")
        laboratory_hour = request.POST.get("laboratory_hour")

        if not course_id:
            messages.error(request, "Course selection is required.")
            return redirect('SMSsubjectsave')

        if all([subject_name, subject_code, credits, department_name, semester_offered, professor_name, year_level, course_id]):
            try:
                course_instance = Course.objects.get(id=course_id)
                # Get or create Department instance from department_name string or ID
                department_instance = None
                try:
                    # Try to get by ID if department_name is numeric
                    if str(department_name).isdigit():
                        department_instance = Department.objects.get(id=int(department_name))
                    else:
                        department_instance = Department.objects.get(name=department_name)
                except Department.DoesNotExist:
                    # If not found, create new Department with given name
                    department_instance = Department.objects.create(name=department_name)

                subject_id = f"{subject_code}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                subject_model = Subject(
                    subject_id=subject_id,
                    subject_name=subject_name,
                    subject_code=subject_code,
                    credits=int(credits),
                    department_name=department_instance,
                    semester_offered=semester_offered,
                    professor_name=professor_name,
                    year_level=int(year_level),
                    course_id=course_instance,
                    lecture_hour=int(lecture_hour) if lecture_hour else 0,
                    laboratory_hour=int(laboratory_hour) if laboratory_hour else 0
                )
                subject_model.save()
                messages.success(request, "Subject added successfully!")
                return redirect('SMSsubjectsave')
            except Course.DoesNotExist:
                messages.error(request, f"Course with ID {course_id} does not exist. Please select a valid course.")
                return redirect('SMSsubjectsave')
            except Exception as e:
                messages.error(request, "Failed to add subject: " + str(e))
                return redirect('SMSsubjectsave')
        else:
            messages.error(request, "All fields are required.")
            return redirect('SMSsubjectsave')

    subjects = Subject.objects.select_related('course_id').all()
    search_query = request.GET.get('search', '')

    if search_query:
        try:
            credits_query = int(search_query)
            subjects = subjects.filter(
                Q(subject_name__icontains=search_query) |
                Q(subject_code__icontains=search_query) |
                Q(credits=credits_query) |
                Q(department_name__name__icontains=search_query) |
                Q(semester_offered__icontains=search_query) |
                Q(professor_name__icontains=search_query) |
                Q(year_level=credits_query) |
                Q(course_id__name__icontains=search_query)
            )
        except ValueError:
            subjects = subjects.filter(
                Q(subject_name__icontains=search_query) |
                Q(subject_code__icontains=search_query) |
                Q(department_name__name__icontains=search_query) |
                Q(semester_offered__icontains=search_query) |
                Q(professor_name__icontains=search_query) |
                Q(year_level__icontains=search_query) |
                Q(course_id__name__icontains=search_query)
            )

    # Sort subjects by course name, year_level, and semester_offered for proper grouping and ordering
    subjects = subjects.order_by('course_id__name', 'year_level', 'semester_offered')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    return render(request, "SMS(Vsubject).html", {
        'grouped_by_course': grouped_by_course,
        'search_query': search_query,
    })

    # Apply search filtering
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(course_id__name__icontains=search_query) |
                    Q(year_level__icontains=search_query)
                )

    # Group subjects by course name only
    grouped_by_course_semester_only = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        if course_name not in grouped_by_course_semester_only:
            grouped_by_course_semester_only[course_name] = []
        grouped_by_course_semester_only[course_name].append(subject)

    # Regroup subjects by semester_offered inside each course
    from django.template.defaultfilters import register
    def group_by_semester(subjects):
        semester_dict = {}
        for subj in subjects:
            semester = subj.semester_offered if subj.semester_offered else "Unassigned Semester"
            if semester not in semester_dict:
                semester_dict[semester] = []
            semester_dict[semester].append(subj)
        return semester_dict

    grouped_by_course_semester_only_regrouped = {}
    for course, subjects_list in grouped_by_course_semester_only.items():
        grouped_by_course_semester_only_regrouped[course] = group_by_semester(subjects_list)

    return render(request, "SMS(Vsubject).html", {
        'grouped_by_course_semester_only': grouped_by_course_semester_only_regrouped,
        'search_query': search_query,
    })

@admin_required
@login_required
def delete_subject(request, subject_id):
    try:
        # Retrieve the subject or return a 404 if it doesn't exist
        subject = get_object_or_404(Subject, id=subject_id)
        subject.delete()  # Delete the subject
        messages.success(request, "Subject deleted successfully.")  # Corrected message
    except Exception as e:
        messages.error(request, "Failed to delete subject: " + str(e))  # Corrected message
    return redirect('SMSsubjectsave')  # Redirect to the course management page

@admin_required
@login_required
def subject_record(request, pk):
    # Retrieve the subject or return a 404 if not found
    subject = get_object_or_404(Subject, pk=pk)
    return render(request, 'SMS(Csubject).html', {'subject': subject})

from django.core.paginator import Paginator

@admin_required
@login_required
def subject_list(request):
    subjects = Subject.objects.select_related('course_id').all()  # Fetch all subjects

    # Sort subjects by course name, year_level, and semester_offered for proper grouping and ordering
    subjects = subjects.order_by('course_id__name', 'year_level', 'semester_offered')

    import logging
    logging.debug(f"subject_list: Total subjects found: {subjects.count()}")  # Debug print total subjects
    for subj in subjects:
        logging.debug(f"subject_list: Subject: {subj.subject_name}, Year Level: {subj.year_level}, Course: {subj.course_id.name if subj.course_id else 'None'}")

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    return render(request, 'SMS(Vsubject).html', {
        'grouped_by_course': grouped_by_course,
        'search_query': '',
    })

@admin_required
@login_required
def edit_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject edited successfully.")
            return redirect('SMSsubjectsave')  # Redirect to the subject list after saving
    else:
        form = SubjectForm(instance=subject)

    return render(request, 'SMS(editsub).html', {'form': form, 'subject': subject})

@admin_required
@login_required
def select_subject(request):
    if request.method == 'POST':
        form = SubjectSelectForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            return redirect('edit_subject', pk=subject.pk)
    else:
        form = SubjectSelectForm()
    return render(request, 'SMS(subject_select).html', {'form': form})

import os
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

@login_required
def delete_student_picture(request, student_id, picture_field):
    allowed_fields = [
        'f137',
        'psa_photocopy',
        'shs_diploma_photocopy',
        'good_moral',
        'honorable_dismissal',
        'original_tor',
        'pictures',
        'profile_pic'
    ]

    if picture_field not in allowed_fields:
        messages.error(request, "Invalid picture field.")
        return redirect('student_profile')

    student = get_object_or_404(Student, pk=student_id)
    picture_file = getattr(student, picture_field)

    if not picture_file:
        messages.error(request, f"No file found for {picture_field}.")
        return redirect('student_profile')

    # Delete the file from the filesystem
    file_path = os.path.join(settings.MEDIA_ROOT, picture_file.name)
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            messages.error(request, f"Error deleting file: {str(e)}")
            return redirect('student_profile')

    # Set the field to None and save
    setattr(student, picture_field, None)
    student.save()

    messages.success(request, f"{picture_field.replace('_', ' ').title()} deleted successfully.")
    return redirect('student_profile')

@admin_required
@login_required
def delete_student_doc(request, student_id, document_field):
    allowed_fields = [
        'f137',
        'psa_photocopy',
        'shs_diploma_photocopy',
        'good_moral',
        'honorable_dismissal',
        'original_tor',
        'pictures',
        'profile_pic'
    ]

    if document_field not in allowed_fields:
        messages.error(request, "Invalid document field.")
        return redirect('edit_student', pk=student_id)

    student = get_object_or_404(Student, pk=student_id)
    document_file = getattr(student, document_field)

    if not document_file:
        messages.error(request, f"No file found for {document_field}.")
        return redirect('edit_student', pk=student_id)

    # Delete the file from the filesystem
    file_path = os.path.join(settings.MEDIA_ROOT, document_file.name)
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            messages.error(request, f"Error deleting file: {str(e)}")
            return redirect('edit_student', pk=student_id)

    # Set the field to None and save
    setattr(student, document_field, None)
    student.save()

    messages.success(request, f"{document_field.replace('_', ' ').title()} deleted successfully.")
    return redirect('edit_student', pk=student_id)

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, "Thank you for your email confirmation. Now you can login your account.")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid!")

    return redirect('homepage')

def register_page(request):
    """
    Handles student registration.
    If a student record exists without account info, fills account info without deleting or changing the record.
    Ensures existing student status is preserved and not changed during linking.
    """
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = StudentProfileForm(request.POST, request.FILES)

        def is_account_incomplete(user, student):
            if not user or not student:
                return False
            if not user.is_active:
                return True
            if not user.username or not student.username:
                return True
            return False

        if user_form.is_valid() and profile_form.is_valid():
            email = user_form.cleaned_data.get('email')
            username = user_form.cleaned_data.get('username')

            # Check if a user with this email exists
            existing_user = User.objects.filter(email=email).first()

            # Check if a student with this email exists
            existing_student = Student.objects.filter(user__email=email).first()

            # Check if a student with the same full name exists
            existing_student_by_name = Student.objects.filter(
                first_name=profile_form.cleaned_data.get('first_name'),
                middle_Name=profile_form.cleaned_data.get('middle_Name'),
                last_name=profile_form.cleaned_data.get('last_name')
            ).first()

            if existing_student_by_name and (not existing_student_by_name.user or is_account_incomplete(existing_student_by_name.user, existing_student_by_name)):
                # Update existing student with missing account info
                user = existing_student_by_name.user
                if user:
                    user_form = UserRegistrationForm(request.POST, instance=user)
                else:
                    user_form = UserRegistrationForm(request.POST)
                if user_form.is_valid():
                    user = user_form.save(commit=False)
                    user.is_active = False
                    user.save()
                else:
                    messages.error(request, "User form invalid during update.")
                    return render(request, 'SMS(Regis).html', {'user_form': user_form, 'profile_form': profile_form})

                student = existing_student_by_name
                profile_form = StudentProfileForm(request.POST, request.FILES, instance=student)
                if profile_form.is_valid():
                    student = profile_form.save(commit=False)
                    # Preserve existing student_number and student_status to prevent deletion or modification
                    student.student_number = existing_student_by_name.student_number
                    student.student_status = existing_student_by_name.student_status  # Preserve existing status
                    student.user = user
                    student.email = user.email
                    student.username = user.username
                    student.save()
                else:
                    messages.error(request, "Profile form invalid during update.")
                    return render(request, 'SMS(Regis).html', {'user_form': user_form, 'profile_form': profile_form})

                activateEmail(request, user, user.email)
                messages.success(request, 'Re-registration successful! Please check your email to activate your account.')
                return redirect('login')

            elif existing_user or existing_student:
                messages.error(request, 'An account with this email already exists and is active. Please login or use a different email.')
                return render(request, 'SMS(Regis).html', {'user_form': user_form, 'profile_form': profile_form})

            else:
                # Proceed with normal registration
                user = user_form.save(commit=False)
                user.is_active = False
                user.save()

                student = profile_form.save(commit=False)
                student.user = user
                student.email = user.email
                student.username = user.username

                student.save()

                activateEmail(request, user, user.email)
                messages.success(request, 'Registration successful! Please check your email to activate your account.')
                return redirect('login')
        else:
            # Add error messages for user_form errors
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"User form - {field}: {error}")
            # Add error messages for profile_form errors
            for field, errors in profile_form.errors.items():
                for error in errors:
                    messages.error(request, f"Profile form - {field}: {error}")

    else:
        user_form = UserRegistrationForm()
        profile_form = StudentProfileForm()

    return render(request, 'SMS(Regis).html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def staff_register_page(request):
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            activateEmail(request, user, user.email)
            messages.success(request, 'Staff registration successful! Please check your email to activate your account.')
            return redirect('login')
    else:
        form = StaffRegistrationForm()
    return render(request, 'SMS(RegisStaff).html', {'form': form})

@login_required
@admin_required
def edit_grade(request, student_id, subject_id):
    student = get_object_or_404(Student, id=student_id)
    subject = get_object_or_404(Subject, id=subject_id)
    
    current_semester = '1st'
    current_academic_year = str(timezone.now().year)
    try:
        grade_instance = Grade.objects.get(
            student=student,
            subject=subject,
            semester=current_semester,
            academic_year=current_academic_year
        )
    except Grade.DoesNotExist:
        messages.error(request, "Grade record not found for editing.")
        return redirect('student_record', pk=student_id)

    grades = {g.subject_id: g for g in student.grades.all()}
    grade_values = {g.subject_id: g.grade_value for g in student.grades.all()}

    def update_subject_status_based_on_grade(grade_obj):
        if grade_obj.grade_value is not None and grade_obj.grade_value != '' and grade_obj.grade_value != '-':
            subject_to_update = grade_obj.subject
            if subject_to_update.status != 'Done':
                subject_to_update.status = 'Done'
                subject_to_update.save()

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade_instance)
        if form.is_valid():
            saved_grade = form.save()
            update_subject_status_based_on_grade(saved_grade)
            messages.success(request, "Grade updated successfully!")
            return redirect('student_record', pk=student_id)
    else:
        form = GradeForm(instance=grade_instance)

    return render(request, 'SMS(editgrade).html', {
        'form': form,
        'student': student,
        'subject': subject,
        'grade': grade_instance,
        'grades': grades,
        'grade_values': grade_values
    })

from .models import Grade
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def delete_grade_ajax(request):
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_id')
            subject_id = request.POST.get('subject_id')
            semester = request.POST.get('semester')
            academic_year = request.POST.get('academic_year')

            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)

            grade = Grade.objects.filter(
                student=student,
                subject=subject,
                semester=semester,
                academic_year=academic_year
            ).first()

            if grade:
                grade.delete()
                # Update subject status to 'Drop' when grade is deleted
                subject.status = 'Drop'
                subject.save()
                return JsonResponse({'success': True, 'message': 'Grade deleted successfully and subject status updated to Drop.'})
            else:
                return JsonResponse({'success': False, 'error': 'Grade not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def edit_grade_ajax(request):
    import logging
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_id')
            subject_id = request.POST.get('subject_id')
            semester = request.POST.get('semester')
            academic_year = request.POST.get('academic_year')
            grade_value = request.POST.get('grade_value')
            year_level = request.POST.get('year_level')

            # Validate required parameters
            if not all([student_id, subject_id, semester, academic_year]):
                logging.error("edit_grade_ajax: Missing required parameters.")
                return JsonResponse({'success': False, 'error': 'Missing required parameters.'})

            # Validate semester
            valid_semesters = ['1st', '2nd']
            if semester not in valid_semesters:
                logging.error(f"edit_grade_ajax: Invalid semester value: {semester}")
                return JsonResponse({'success': False, 'error': f'Invalid semester value. Must be one of {valid_semesters}.'})

            # Validate year_level if provided
            valid_year_levels = ['1', '2', '3', '4']
            if year_level and year_level not in valid_year_levels:
                logging.error(f"edit_grade_ajax: Invalid year_level value: {year_level}")
                return JsonResponse({'success': False, 'error': f'Invalid year_level value. Must be one of {valid_year_levels}.'})

            # Convert grade_value to None if it is '-' or empty string
            if grade_value == '-' or grade_value == '':
                grade_value = None

            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)

            grade, created = Grade.objects.get_or_create(
                student=student,
                subject=subject,
                semester=semester,
                academic_year=academic_year,
                defaults={'grade_value': grade_value, 'year_level': year_level}
            )

            if not created:
                grade.grade_value = grade_value
                if year_level:
                    grade.year_level = year_level
            # Set status to "Currently Taking" if semester and academic_year are filled
            if semester and academic_year:
                grade.status = "Currently Taking"
            grade.save()
            logging.info(f"edit_grade_ajax: {'Created new' if created else 'Updated existing'} grade for student_id={student_id}, subject_id={subject_id}")

            # Update subject.status to "Done" if grade_value is set (not None or empty)
            if grade.grade_value is not None and grade.grade_value != '' and grade.grade_value != '-':
                if subject.status != 'Done':
                    subject.status = 'Done'
                    subject.save()

            return JsonResponse({
                'success': True,
                'message': 'Grade updated successfully.',
                'grade_value': grade.grade_value,
                'year_level': grade.year_level,
                'semester': grade.semester,
                'academic_year': grade.academic_year,
                'status': grade.status,
                'subject_status': subject.status
            })
        except Exception as e:
            logging.error(f"edit_grade_ajax: Exception occurred: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        logging.error("edit_grade_ajax: Invalid request method")
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@admin_required
def change_subject_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            student_id = request.POST.get('student_id')
            old_subject_id = request.POST.get('old_subject_id')
            new_subject_id = request.POST.get('new_subject')
            new_subject_status = request.POST.get('new_subject_status')
            new_subject_year_level = request.POST.get('new_subject_year_level')
            new_subject_semester = request.POST.get('new_subject_semester')

            student = get_object_or_404(Student, pk=student_id)
            old_subject = get_object_or_404(Subject, pk=old_subject_id)
            new_subject = get_object_or_404(Subject, pk=new_subject_id)

            # Remove old subject's grade if exists
            student.grades.filter(subject=old_subject).delete()

            # Add or update new subject's grade with provided status, year level, semester
            from .models import Grade
            grade, created = Grade.objects.get_or_create(
                student=student,
                subject=new_subject,
                defaults={
                    'semester': new_subject_semester if new_subject_semester else '1st',
                    'academic_year': timezone.now().year,
                    'year_level': int(new_subject_year_level) if new_subject_year_level else None,
                    'status': new_subject_status if new_subject_status else None,
                }
            )
            if not created:
                # Update existing grade fields
                if new_subject_semester:
                    grade.semester = new_subject_semester
                if new_subject_year_level:
                    grade.year_level = int(new_subject_year_level)
                if new_subject_status:
                    grade.status = new_subject_status
                grade.save()

            return JsonResponse({
                'success': True,
                'message': f"Subject changed from {old_subject.subject_name} to {new_subject.subject_name} successfully.",
                'new_subject_name': new_subject.subject_name,
                'old_subject_id': old_subject_id,
                'new_subject_id': new_subject_id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method or not AJAX'
    })

@login_required
@admin_required
def add_student_subject_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            student_id = request.POST.get('student_id')
            new_subject_id = request.POST.get('new_subject')
            selected_course_id = request.POST.get('course')
            semester_to_use = request.POST.get('semester')

            student = get_object_or_404(Student, pk=student_id)
            new_subject = get_object_or_404(Subject, pk=new_subject_id)

            # Use the selected course if provided, else fallback to student's course
            if selected_course_id:
                selected_course = get_object_or_404(Course, pk=selected_course_id)
            else:
                selected_course = student.course

            # Check if the subject belongs to the student's department
            if new_subject.department_name != student.department_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Selected subject does not belong to the student\'s department.'
                })

            # Check if the subject belongs to the selected course
            if new_subject.course_id != selected_course:
                return JsonResponse({
                    'success': False,
                    'error': 'Selected subject does not belong to the selected course.'
                })

            current_academic_year = student.academic_year if student.academic_year else str(timezone.now().year)

            # Require semester from the form, do not fallback to subject defaults
            if not semester_to_use:
                return JsonResponse({
                    'success': False,
                    'error': 'Semester is required.'
                })

            existing_grade = Grade.objects.filter(
                student=student,
                subject=new_subject,
                semester=semester_to_use,
                academic_year=current_academic_year,
                is_active=True
            ).first()
            if existing_grade:
                return JsonResponse({
                    'success': False,
                    'error': 'Subject is already assigned to the student for the selected semester and academic year.'
                })

            Grade.objects.create(
                student=student,
                subject=new_subject,
                semester=semester_to_use,
                academic_year=current_academic_year,
                is_active=True
            )

            return JsonResponse({
                'success': True,
                'message': f"Subject {new_subject.subject_name} added successfully.",
                'new_subject_name': new_subject.subject_name,
                'new_subject_id': new_subject_id,
                'semester_offered': semester_to_use,
                'subject_code': new_subject.subject_code,
                'credits': new_subject.credits,
                'number_of_hours': getattr(new_subject, 'number_of_hours', 'N/A'),
                'status': getattr(new_subject, 'status', 'N/A')
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while assigning the subject. Please try again later.'
            })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method or not AJAX'
    })

def activateEmail(request, user, to_email):
    import logging
    mail_subject = "Activate your user account."
    message = render_to_string("email_verification.html", {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        "protocol": 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    try:
        if email.send():
            messages.success(request, f'Dear <b>{user}</b>, please go to you email <b>{to_email}</b> inbox and click on \
                    received activation link to confirm and complete the registration. <b>Note:</b> Check your spam folder.')
        else:
            messages.error(request, f'Problem sending email to {to_email}, check if you typed it correctly.')
    except Exception as e:
        logging.error(f"Error sending activation email to {to_email}: {str(e)}")
        messages.error(request, f'Error sending email to {to_email}. Please try again later.')

import logging

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import logging
from .models import Student, Subject

@login_required
@admin_required
def delete_removed_subject_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            student_id = request.POST.get('student_id')
            subject_id = request.POST.get('subject_id')

            logging.info(f"delete_removed_subject_ajax called with student_id={student_id}, subject_id={subject_id}")

            student = get_object_or_404(Student, pk=student_id)
            subject = get_object_or_404(Subject, pk=subject_id)

            # Find the Grade record where is_active=False for the given student and subject
            grade_qs = student.grades.filter(subject=subject, is_active=False)
            count = grade_qs.count()
            logging.info(f"Found {count} grade records with is_active=False for student_id={student_id} and subject_id={subject_id}")

            if count == 0:
                logging.warning(f"No removed subject found for student_id={student_id} and subject_id={subject_id}")
                return JsonResponse({
                    'success': False,
                    'error': 'Removed subject not found for the student.'
                })

            grade = grade_qs.first()

            # Permanently delete the grade record
            grade.delete()
            logging.info(f"Removed subject {subject.subject_name} deleted successfully for student_id={student_id}")

            return JsonResponse({
                'success': True,
                'message': f'Removed subject {subject.subject_name} deleted successfully.'
            })
        except Exception as e:
            logging.error(f"Error in delete_removed_subject_ajax: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while deleting the removed subject. Please try again later.'
            })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method or not AJAX'
    })

@login_required
@admin_required
def remove_student_subject_ajax(request):
    import logging
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            student_id = request.POST.get('student_id')
            subject_id = request.POST.get('subject_id')

            logging.info(f"remove_student_subject_ajax called with student_id={student_id}, subject_id={subject_id}")

            student = get_object_or_404(Student, pk=student_id)
            subject = get_object_or_404(Subject, pk=subject_id)

            # Find the active Grade record for the given student and subject
            grade_qs = student.grades.filter(subject=subject, is_active=True)
            count = grade_qs.count()
            logging.info(f"Found {count} active grade records for student_id={student_id} and subject_id={subject_id}")

            if count == 0:
                logging.warning(f"No active subject found for student_id={student_id} and subject_id={subject_id}")
                return JsonResponse({
                    'success': False,
                    'error': 'Active subject not found for the student.'
                })

            grade = grade_qs.first()

            # Mark the grade record as inactive (soft delete)
            grade.is_active = False
            grade.save()
            logging.info(f"Subject {subject.subject_name} marked as inactive for student_id={student_id}")

            return JsonResponse({
                'success': True,
                'message': f'Subject {subject.subject_name} removed successfully.'
            })
        except Exception as e:
            logging.error(f"Error in remove_student_subject_ajax: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while removing the subject. Please try again later.'
            })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method or not AJAX'
    })

@login_required
@admin_required
def restore_student_subject_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            student_id = request.POST.get('student_id')
            subject_id = request.POST.get('subject_id')

            student = get_object_or_404(Student, pk=student_id)
            subject = get_object_or_404(Subject, pk=subject_id)

            # Mark the Grade record as active to restore
            grade = student.grades.filter(subject=subject, is_active=False).first()
            if grade:
                grade.is_active = True
                grade.save()
                return JsonResponse({
                    'success': True,
                    'message': f'Subject {subject.subject_name} restored successfully.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Subject not found for the student or already active.'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method or not AJAX'
    })

@login_required
@admin_required
def student_record(request, pk):
    import logging
    import traceback

    logging.info(f"Accessing student_record view with pk={pk}")
    try:
        student = Student.objects.get(pk=pk)

        documents = [
            ('F137', student.f137),
            ('PSA Photocopy', student.psa_photocopy),
            ('SHS Diploma Photocopy', student.shs_diploma_photocopy),
            ('Good Moral', student.good_moral),
            ('Honorable Dismissal', student.honorable_dismissal),
            ('Original TOR', student.original_tor),
            ('Pictures', student.pictures)
        ]

        if not student.id:
            messages.error(request, "Invalid student ID.")
            return redirect('student_list')

        # Activate grades matching student's year_level, semester, and academic_year if not active
        student_semester = getattr(student, 'semester', None)
        student_academic_year = getattr(student, 'academic_year', None)
        if student_semester and student_academic_year:
            inactive_grades = student.grades.filter(
                year_level=student.year_level,
                semester=student_semester,
                academic_year=student_academic_year,
                is_active=False
            )
            count_activated = inactive_grades.update(is_active=True)
            logging.info(f"Activated {count_activated} grades for student id {student.id} in student_record view")

        # Save grades with filled semester or academic_year to update status automatically
        grades_to_update = student.grades.filter(
            semester__isnull=False
        ).exclude(semester='').filter(
            academic_year__isnull=False
        ).exclude(academic_year='')
        for grade in grades_to_update:
            grade.save()

        student = Student.objects.get(pk=pk)

        if not student.id:
            messages.error(request, "Invalid student ID.")
            return redirect('student_list')

        # Activate grades matching student's year_level, semester, and academic_year if not active
        student_semester = getattr(student, 'semester', None)
        student_academic_year = getattr(student, 'academic_year', None)
        if student_semester and student_academic_year:
            inactive_grades = student.grades.filter(
                year_level=student.year_level,
                semester=student_semester,
                academic_year=student_academic_year,
                is_active=False
            )
            count_activated = inactive_grades.update(is_active=True)
            logging.info(f"Activated {count_activated} grades for student id {student.id} in student_record view")

        # Get all subjects for the student's course that the student has grades for (active or inactive)
        subject_ids = student.grades.values_list('subject_id', flat=True).distinct()
        all_subjects_qs = Subject.objects.filter(id__in=subject_ids).order_by('year_level', 'semester_offered', 'subject_name')

        # Get active grades for the student
        active_grades_qs = student.grades.filter(is_active=True).select_related('subject')

        # Bulk update grades with null or empty academic_year to student's academic_year
        if student_academic_year:
            student.grades.filter(Q(academic_year__isnull=True) | Q(academic_year='')).update(academic_year=student_academic_year)

        # Re-fetch active grades after update
        active_grades_qs = student.grades.filter(is_active=True).select_related('subject')

        # Query distinct academic years from active grades
        academic_years_qs = active_grades_qs.values_list('academic_year', flat=True).distinct()
        academic_years = sorted([ay for ay in academic_years_qs if ay is not None])

        # Map subject id to grade
        subject_grade_map = {grade.subject_id: grade for grade in active_grades_qs}

        # Build list of subjects with their grades (or None if no grade)
        subjects_with_grades = []
        for subject in all_subjects_qs:
            grade = subject_grade_map.get(subject.id)
            # Fill missing semester and academic_year from student if grade exists
            if grade:
                if not grade.semester and student_semester:
                    grade.semester = student_semester
                if not grade.academic_year and student_academic_year:
                    grade.academic_year = student_academic_year
            subjects_with_grades.append({
                'subject': subject,
                'grade': grade,
                'semester': grade.semester if grade else None,
                'academic_year': grade.academic_year if grade else None,
            })

        # Group by subject year_level and semester_offered then by subject name
        grouped_grades = {}
        def semester_sort_key(semester):
            order = {'1st': 1, '2nd': 2, '3rd': 3}
            return order.get(semester.lower(), 99)

        for item in subjects_with_grades:
            subject = item['subject']
            grade = item['grade']
            year_key = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester_key = grade.semester if grade and grade.semester else (subject.semester_offered if subject.semester_offered else "Unassigned Semester")

            if year_key not in grouped_grades:
                grouped_grades[year_key] = {}
            if semester_key not in grouped_grades[year_key]:
                grouped_grades[year_key][semester_key] = []
            grouped_grades[year_key][semester_key].append(item)

        sorted_grouped_grades = {}
        for year in sorted(grouped_grades.keys(), key=lambda x: int(x) if isinstance(x, int) or (isinstance(x, str) and x.isdigit()) else 99):
            semesters = grouped_grades[year]
            sorted_semesters = dict(sorted(semesters.items(), key=lambda x: semester_sort_key(x[0])))
            sorted_grouped_grades[year] = sorted_semesters

        grouped_grades = sorted_grouped_grades

        # Add subject_grade_map to context for template use

        # Create a mapping from year level to academic years present in that year level's grades
        year_level_academic_years = {}
        for year_level, semesters in grouped_grades.items():
            academic_years_set = set()
            for semester, items in semesters.items():
                for item in items:
                    ay = item.get('academic_year')
                    if ay:
                        academic_years_set.add(ay)
            year_level_academic_years[year_level] = sorted(academic_years_set)

        # Fetch inactive grades for removed subjects
        removed_grades = student.grades.filter(is_active=False).select_related('subject')

        add_subject_form = AddStudentSubjectForm(student=student)

        # Group all subjects by year_level and semester_offered for the add subject form
        grouped_subjects = {}
        # Create a map of subject id to active grade for quick lookup
        active_grades_map = {grade.subject_id: grade for grade in active_grades_qs}

        for subject in all_subjects_qs:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"

            # Update subject status based on student's grade if exists for the subject
            grade = active_grades_map.get(subject.id)
            if grade:
                # Use grade's semester and academic_year to determine if status should be updated
                # For simplicity, update subject.status to grade.status if grade exists
                # But since subject.status is a model field, we should not modify it directly here
                # Instead, we can add a dynamic attribute for template use
                subject.current_status = grade.subject.status if hasattr(grade.subject, 'status') else subject.status
            else:
                subject.current_status = subject.status

            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)

        # Fetch all subjects for the student's course regardless of grades
        all_course_subjects_qs = Subject.objects.filter(course_id=student.course).order_by('year_level', 'semester_offered', 'subject_name')

        # Create a mapping of all subjects to their grades (active or inactive)
        subject_grade_map_all = {}
        all_grades_qs = student.grades.select_related('subject').filter(subject__in=all_course_subjects_qs)
        for grade in all_grades_qs:
            subject_grade_map_all[grade.subject_id] = grade

        grouped_all_course_subjects = {}
        for subject in all_course_subjects_qs:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            # Use grade's semester if available, else fallback to subject.semester_offered
            grade = subject_grade_map_all.get(subject.id)
            semester = grade.semester if grade and grade.semester else (subject.semester_offered if subject.semester_offered else "Unassigned Semester")
            if year_level not in grouped_all_course_subjects:
                grouped_all_course_subjects[year_level] = {}
            if semester not in grouped_all_course_subjects[year_level]:
                grouped_all_course_subjects[year_level][semester] = []
            grouped_all_course_subjects[year_level][semester].append(subject)

        logging.info(f"student_record view: student_id={student.id}, total subjects={len(all_subjects_qs)}, total course subjects={len(all_course_subjects_qs)}")

        subjects = all_subjects_qs
        return render(request, 'SMS(Cstudent).html', {
            'student': student,
            'grouped_grades': grouped_grades,
            'year_level_academic_years': year_level_academic_years,
            'removed_grades': removed_grades,
            'add_subject_form': add_subject_form,
            'grouped_subjects': grouped_subjects,
            'subjects': subjects,
            'academic_years': academic_years,
            'documents': documents,
            'grouped_all_course_subjects': grouped_all_course_subjects,
            'subject_grade_map_all': subject_grade_map_all,
        })
    except Student.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect('student_list')
    except Exception as e:
        logging.error(f"Unexpected error in student_record view: {str(e)}")
        logging.error(traceback.format_exc())
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect('student_list')

@login_required
@student_required
def SMS_grade(request):
    import logging
    try:
        student = Student.objects.filter(user=request.user).first()
        if not student:
            messages.error(request, "Student profile not found.")
            return redirect('student_dashboard')

        # Get all subjects for the student's course or department
        all_subjects_qs = Subject.objects.filter(
            Q(course_id=student.course) | Q(department_name=student.department_name)
        ).order_by('year_level', 'semester_offered', 'subject_name')

        # Get active grades for the student
        active_grades_qs = student.grades.filter(is_active=True).select_related('subject')

        # Map subject id to grade
        subject_grade_map = {grade.subject_id: grade for grade in active_grades_qs}

        # Build list of subjects with their grades (or None if no grade)
        subjects_with_grades = []
        for subject in all_subjects_qs:
            grade = subject_grade_map.get(subject.id)
            subjects_with_grades.append({
                'subject': subject,
                'grade': grade,
                'semester': grade.semester if grade else None,
                'academic_year': grade.academic_year if grade else None,
            })

        # Group by subject year_level and semester_offered then by subject name
        grouped_grades = {}
        def semester_sort_key(semester):
            order = {'1st': 1, '2nd': 2, '3rd': 3}
            if semester is None:
                return 99
            return order.get(semester.lower(), 99)

        for item in subjects_with_grades:
            subject = item['subject']
            grade = item['grade']
            year_key = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester_key = grade.semester if grade and grade.semester else (subject.semester_offered if subject.semester_offered else "Unassigned Semester")

            if year_key not in grouped_grades:
                grouped_grades[year_key] = {}
            if semester_key not in grouped_grades[year_key]:
                grouped_grades[year_key][semester_key] = []
            grouped_grades[year_key][semester_key].append(item)

        sorted_grouped_grades = {}
        for year in sorted(grouped_grades.keys(), key=lambda x: int(x) if isinstance(x, int) or (isinstance(x, str) and x.isdigit()) else 99):
            semesters = grouped_grades[year]
            sorted_semesters = dict(sorted(semesters.items(), key=lambda x: semester_sort_key(x[0])))
            sorted_grouped_grades[year] = sorted_semesters

        grouped_grades = sorted_grouped_grades

        # Paginate by year_level
        year_levels = list(grouped_grades.keys())
        paginator = Paginator(year_levels, 1)  # 1 year_level per page

        page_number = request.GET.get('page', 1)
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            logging.warning(f"Invalid page number '{page_number}', defaulting to 1")
            page_number = 1

        try:
            page_obj = paginator.page(page_number)
        except Exception as e:
            logging.warning(f"Paginator error: {str(e)} - defaulting to page 1")
            page_obj = paginator.page(1)

        current_year_level = page_obj.object_list[0]
        paginated_grades = {current_year_level: grouped_grades[current_year_level]}

        pagination_data = {
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'current_page': page_obj.number,
            'num_pages': paginator.num_pages,
            'page_param': 'page',
        }

        logging.info(f"SMS_grade pagination: page {page_obj.number} of {paginator.num_pages}, showing year_level {current_year_level}")

        return render(request, 'SMS(grade).html', {
            'grouped_grades': paginated_grades,
            'student': student,
            'pagination_data': pagination_data,
        })
    except Exception as e:
        logging.error(f"Unexpected error in SMS_grade view: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect('student_dashboard')


@login_required
@student_required
def student_subjects(request, student_id):
    # Get the student object
    student = get_object_or_404(Student, id=student_id)

    # Get all subjects in the student's course
    subjects = Subject.objects.filter(course_id=student.course).order_by('year_level', 'semester_offered', 'subject_name')

    # Get active grades for the student for these subjects
    active_grades_qs = student.grades.filter(subject__in=subjects, is_active=True).select_related('subject')

    # Create a dictionary mapping subject id to grade object
    subject_grade_map_all = {grade.subject_id: grade for grade in active_grades_qs}

    context = {
        'student': student,
        'subjects': subjects,
        'subject_grade_map_all': subject_grade_map_all,
    }

    return render(request, 'SMS(Coursesub).html', context)  # Replace with your actual template name

@login_required
@staff_required
def SMSstudentandstaff(request):
    return render(request, 'SMS(studentandstaff).html')

def background_template_view(request):
    return render(request, 'background_template.html')

from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Subject

@login_required
@staff_required
def SMSstaffit(request):
    """
    View to render the staff IT dashboard page.
    Requires user to be logged in.
    """
    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Science in Computer Science",
        "Bachelor of Science in Computer Engineering",
        "Bachelor of Science in Information Technology"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    return render(request, 'staffpage/SMS(staffit).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
    })

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Student



@login_required
@staff_required
def SMSstaffvstu(request, subject_id, professor_name=None):
    search_query = request.GET.get('search', '')
    from django.db.models import Q

    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        subject = None

    if not subject:
        # If subject not found, try to get a default subject in the department
        default_subject = Subject.objects.filter(course_id__department_name__name="College of Computer Studies").first()
        if default_subject:
            subject = default_subject
            subject_id = default_subject.id

    # Get distinct professor names for the subject's subject_name
    professor_names = []
    if subject:
        professor_names = list(Subject.objects.filter(subject_name=subject.subject_name).values_list('professor_name', flat=True).distinct())

    if subject:
     # Filter students who have an active grade for the subject or a subject with the same subject_name
        students = Student.objects.filter(
            grades__subject__subject_name=subject.subject_name,
            grades__is_active=True,
            grades__status='Currently Taking',
            course__department_name__name="College of Computer Studies",
            student_status='Enrolled'
        ).distinct()

        # If professor_name is provided, filter students by professor_name
        if professor_name:
            students = students.filter(
                grades__subject__professor_name=professor_name
            ).distinct()
    else:
        # If no subject found, fallback to all students in department
        students = Student.objects.filter(course__department_name__name="College of Computer Studies", student_status='Enrolled')

    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_number__icontains=search_query) |
            Q(course__name__icontains=search_query)
        )

    # Add ordering by year_level for proper grouping and display
    students = students.order_by('year_level')

    grouped_students = defaultdict(list)
    for student in students:
        year = student.year_level if student.year_level else "Unassigned Year"
        grouped_students[year].append(student)
    # Convert defaultdict to regular dict for template context
    grouped_students = dict(grouped_students)
    return render(request, 'staffpage/SMS(staffvstu).html', {
        'grouped_students': grouped_students,
        'search_query': search_query,
        'subject_id': subject_id,
        'professor_names': professor_names,
        'selected_professor': professor_name,
    })

@login_required
@staff_required
def SMSstaffcstu(request, pk):
    """
    View to render the staff computer studies dashboard page for a specific student.
    Requires user to be logged in.
    """
    from django.shortcuts import get_object_or_404
    student = get_object_or_404(Student, pk=pk)

    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Science in Computer Science",
        "Bachelor of Science in Computer Engineering",
        "Bachelor of Science in Information Technology"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    subject_id = None
    if subjects.exists():
        subject_id = subjects.first().id

    documents = [
        ('F137', student.f137),
        ('PSA Photocopy', student.psa_photocopy),
        ('SHS Diploma Photocopy', student.shs_diploma_photocopy),
        ('Good Moral', student.good_moral),
        ('Honorable Dismissal', student.honorable_dismissal),
        ('Original TOR', student.original_tor),
        ('Pictures', student.pictures)
    ]

    return render(request, 'staffpage/SMS(staffcstu).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
        'student': student,
        'subject_id': subject_id,
        'documents': documents,
    })

#new

@login_required
@staff_required
def SMSstaffhm(request):
    """
    View to render the staff IT dashboard page.
    Requires user to be logged in.
    """
    search_query = request.GET.get('search', '')
    course_names = [
         "Bachelor of Science in Hospitality Management",
        "Associate in Hospitality Management"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    return render(request, 'staffpage/SMS(staffhm).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
    })

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Student

@login_required
@staff_required
def SMSstaffvstuhm(request, subject_id):
    search_query = request.GET.get('search', '')
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    try:
        subject = Subject.objects.get(subject_id=subject_id)
    except Subject.DoesNotExist:
        subject = None

    if subject:
        students = Student.objects.filter(
            grades__subject__subject_name=subject.subject_name,
            grades__is_active=True,
            grades__status='Currently Taking',
            course__department_name__name="College of Hotel and Restaurant Management",
            student_status='Enrolled'
        ).distinct()
    else:
        students = Student.objects.filter(course__department_name__name="College of Hotel and Restaurant Management")

    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_number__icontains=search_query) |
            Q(course__name__icontains=search_query)
        )

    grouped_students = defaultdict(list)
    for student in students:
        year = student.year_level if student.year_level else "Unassigned Year"
        grouped_students[year].append(student)
    # Convert defaultdict to regular dict for template context
    grouped_students = dict(grouped_students)
    return render(request, 'staffpage/SMS(staffvstuhm).html', {'grouped_students': grouped_students, 'search_query': search_query, 'subject_id': subject_id})

@login_required
@staff_required
def SMSstaffcstuhm(request, pk):
    """
    View to render the staff computer studies dashboard page for a specific student.
    Requires user to be logged in.
    """
    from django.shortcuts import get_object_or_404
    student = get_object_or_404(Student, pk=pk)

    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Science in Hospitality Management",
        "Associate in Hospitality Management"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    # Determine a subject_id to pass to the template for the URL
    subject_id = None
    if subjects.exists():
        subject_id = subjects.first().id

    documents = [
        ('F137', student.f137),
        ('PSA Photocopy', student.psa_photocopy),
        ('SHS Diploma Photocopy', student.shs_diploma_photocopy),
        ('Good Moral', student.good_moral),
        ('Honorable Dismissal', student.honorable_dismissal),
        ('Original TOR', student.original_tor),
        ('Pictures', student.pictures)
    ]

    return render(request, 'staffpage/SMS(staffcstuhm).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
        'student': student,
        'subject_id': subject_id,
        'documents': documents,
    })

#newba

@login_required
@staff_required
def SMSstaffba(request):
    """
    View to render the staff IT dashboard page.
    Requires user to be logged in.
    """
    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Science in Business Administration HDRM",
        "Bachelor of Science in Business Administration Marketing"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    return render(request, 'staffpage/SMS(staffba).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
    })

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Student

@login_required
@staff_required
def SMSstaffvstuba(request, subject_id):
    search_query = request.GET.get('search', '')
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    try:
        subject = Subject.objects.get(subject_id=subject_id)
    except Subject.DoesNotExist:
        subject = None

    if subject:
        students = Student.objects.filter(
            grades__subject__subject_name=subject.subject_name,
            grades__is_active=True,
            grades__status='Currently Taking',
            course__department_name__name="College of Business Administration",
            student_status='Enrolled'
        ).distinct()
    else:
        students = Student.objects.filter(course__department_name__name="College of Business Administration")

    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_number__icontains=search_query) |
            Q(course__name__icontains=search_query)
        )

    grouped_students = defaultdict(list)
    for student in students:
        year = student.year_level if student.year_level else "Unassigned Year"
        grouped_students[year].append(student)
    # Convert defaultdict to regular dict for template context
    grouped_students = dict(grouped_students)
    return render(request, 'staffpage/SMS(staffvstuba).html', {'grouped_students': grouped_students, 'search_query': search_query})

@login_required
@staff_required
def SMSstaffcstuba(request, pk):
    """
    View to render the staff computer studies dashboard page for a specific student.
    Requires user to be logged in.
    """
    from django.shortcuts import get_object_or_404
    student = get_object_or_404(Student, pk=pk)

    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Science in Business Administration HDRM",
        "Bachelor of Science in Business Administration Marketing"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    subject_id = None
    if subjects.exists():
        subject_id = subjects.first().id

    documents = [
        ('F137', student.f137),
        ('PSA Photocopy', student.psa_photocopy),
        ('SHS Diploma Photocopy', student.shs_diploma_photocopy),
        ('Good Moral', student.good_moral),
        ('Honorable Dismissal', student.honorable_dismissal),
        ('Original TOR', student.original_tor),
        ('Pictures', student.pictures)
    ]

    return render(request, 'staffpage/SMS(staffcstuba).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
        'student': student,
        'subject_id': subject_id,
        'documents': documents,
    })

#newA

@login_required
@staff_required
def SMSstaffA(request):
    """
    View to render the staff IT dashboard page.
    Requires user to be logged in.
    """
    search_query = request.GET.get('search', '')
    course_names = [
         "Bachelor of Science in Accountancy"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    return render(request, 'staffpage/SMS(staffA).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
    })

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Student

@login_required
@staff_required
def SMSstaffvstuA(request, subject_id):
    search_query = request.GET.get('search', '')
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    try:
        subject = Subject.objects.get(subject_id=subject_id)
    except Subject.DoesNotExist:
        subject = None

    if subject:
        students = Student.objects.filter(
            grades__subject__subject_name=subject.subject_name,
            grades__is_active=True,
            grades__status='Currently Taking',
            course__department_name__name="College of Business Administration",
            student_status='Enrolled'
        ).distinct()
    else:
        students = Student.objects.filter(course__department_name__name="College of Business Administration")

    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_number__icontains=search_query) |
            Q(course__name__icontains=search_query)
        )

    grouped_students = defaultdict(list)
    for student in students:
        year = student.year_level if student.year_level else "Unassigned Year"
        grouped_students[year].append(student)
    # Convert defaultdict to regular dict for template context
    grouped_students = dict(grouped_students)
    return render(request, 'staffpage/SMS(staffvstuA).html', {'grouped_students': grouped_students, 'search_query': search_query, 'subject_id': subject_id})

@login_required
@staff_required
def SMSstaffcstuA(request, pk):
    """
    View to render the staff computer studies dashboard page for a specific student.
    Requires user to be logged in.
    """
    from django.shortcuts import get_object_or_404
    student = get_object_or_404(Student, pk=pk)

    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Science in Accountancy"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    subject_id = None
    if subjects.exists():
        subject_id = subjects.first().id

    documents = [
        ('F137', student.f137),
        ('PSA Photocopy', student.psa_photocopy),
        ('SHS Diploma Photocopy', student.shs_diploma_photocopy),
        ('Good Moral', student.good_moral),
        ('Honorable Dismissal', student.honorable_dismissal),
        ('Original TOR', student.original_tor),
        ('Pictures', student.pictures)
    ]

    return render(request, 'staffpage/SMS(staffcstuA).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
        'student': student,
        'subject_id': subject_id,
        'documents': documents,
    })

#newE

@login_required
@staff_required
def SMSstaffE(request):
    """
    View to render the staff IT dashboard page.
    Requires user to be logged in.
    """
    search_query = request.GET.get('search', '')
    course_names = [
         "Bachelor of Elementary Education",
        "Bachelor of Secondary Education Specialization Science",
        "Bachelor of Secondary Education Specialization English",
        "Bachelor of Secondary Education Specialization Filipino",
        "Bachelor of Secondary Education Specialization Mathematics",
        "Bachelor of Secondary Education Specialization Social Studies"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    return render(request, 'staffpage/SMS(staffE).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
    })

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Student

@login_required
@staff_required
def SMSstaffvstuE(request, subject_id):
    search_query = request.GET.get('search', '')
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    try:
        subject = Subject.objects.get(subject_id=subject_id)
    except Subject.DoesNotExist:
        subject = None

    if subject:
        students = Student.objects.filter(
            grades__subject__subject_name=subject.subject_name,
            grades__is_active=True,
            grades__status='Currently Taking',
            course__department_name__name="College of Education",
            student_status='Enrolled'
        ).distinct()
    else:
        students = Student.objects.filter(course__department_name__name="College of Education")

    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_number__icontains=search_query) |
            Q(course__name__icontains=search_query)
        )

    grouped_students = defaultdict(list)
    for student in students:
        year = student.year_level if student.year_level else "Unassigned Year"
        grouped_students[year].append(student)
    # Convert defaultdict to regular dict for template context
    grouped_students = dict(grouped_students)
    return render(request, 'staffpage/SMS(staffvstuE).html', {'grouped_students': grouped_students, 'search_query': search_query})

@login_required
@staff_required
def SMSstaffcstuE(request, pk):
    """
    View to render the staff computer studies dashboard page for a specific student.
    Requires user to be logged in.
    """
    from django.shortcuts import get_object_or_404
    student = get_object_or_404(Student, pk=pk)

    search_query = request.GET.get('search', '')
    course_names = [
        "Bachelor of Elementary Education",
        "Bachelor of Secondary Education Specialization Science",
        "Bachelor of Secondary Education Specialization English",
        "Bachelor of Secondary Education Specialization Filipino",
        "Bachelor of Secondary Education Specialization Mathematics",
        "Bachelor of Secondary Education Specialization Social Studies"
    ]
    # Build Q object for case-insensitive partial matching of course names
    course_name_filter = Q()
    for name in course_names:
        course_name_filter |= Q(course_id__name__icontains=name)

    subjects = Subject.objects.filter(course_name_filter)
    if search_query:
            try:
                credits_query = int(search_query)
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(credits=credits_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level=credits_query) |
                    Q(course_id__name__icontains=search_query)
                )
            except ValueError:
                subjects = subjects.filter(
                    Q(subject_name__icontains=search_query) |
                    Q(subject_code__icontains=search_query) |
                    Q(department_name__name__icontains=search_query) |
                    Q(semester_offered__icontains=search_query) |
                    Q(professor_name__icontains=search_query) |
                    Q(year_level__icontains=search_query) |
                    Q(course_id__name__icontains=search_query)
                )
    subjects = subjects.order_by('course_id__name', 'year_level')

    grouped_by_course = {}
    for subject in subjects:
        course_name = subject.course_id.name if subject.course_id and subject.course_id.name else "Unassigned Courses"
        year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
        if course_name not in grouped_by_course:
            grouped_by_course[course_name] = {}
        if year_level not in grouped_by_course[course_name]:
            grouped_by_course[course_name][year_level] = []
        grouped_by_course[course_name][year_level].append(subject)

    # Build courses_dict for template, grouping subjects by year_level and semester_offered
    courses_dict = {}
    for course_name in course_names:
        course_subjects = subjects.filter(course_id__name__icontains=course_name)
        grouped_subjects = {}
        for subject in course_subjects:
            year_level = subject.year_level if subject.year_level is not None else "Unassigned Year"
            semester = subject.semester_offered if subject.semester_offered else "Unassigned Semester"
            if year_level not in grouped_subjects:
                grouped_subjects[year_level] = {}
            if semester not in grouped_subjects[year_level]:
                grouped_subjects[year_level][semester] = []
            grouped_subjects[year_level][semester].append(subject)
        # Get course object for course_name
        course_obj = None
        if course_subjects.exists():
            course_obj = course_subjects.first().course_id
        courses_dict[course_name] = {
            'course': course_obj,
            'grouped_subjects': grouped_subjects
        }

    subject_id = None
    if subjects.exists():
        subject_id = subjects.first().id

    documents = [
        ('F137', student.f137),
        ('PSA Photocopy', student.psa_photocopy),
        ('SHS Diploma Photocopy', student.shs_diploma_photocopy),
        ('Good Moral', student.good_moral),
        ('Honorable Dismissal', student.honorable_dismissal),
        ('Original TOR', student.original_tor),
        ('Pictures', student.pictures)
    ]

    return render(request, 'staffpage/SMS(staffcstuE).html', {
        'grouped_by_course': grouped_by_course,
        'course_names': course_names,
        'search_query': search_query,
        'courses_dict': courses_dict,
        'student': student,
        'subject_id': subject_id,
        'documents': documents,
    })

@student_required
@login_required
def SMS_it(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    departments = Department.objects.all()
    return render(request, 'SMScourse/SMS(it).html', {'user': request.user, 'student': student, 'departments': departments})

@student_required
@login_required
def SMS_hm(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    departments = Department.objects.all()
    return render(request, 'SMScourse/SMS(hm).html', {'user': request.user, 'student': student, 'departments': departments})

@student_required
@login_required
def SMS_ba(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    departments = Department.objects.all()
    return render(request, 'SMScourse/SMS(BA).html', {'user': request.user, 'student': student, 'departments': departments})

@student_required
@login_required
def SMS_ed(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    departments = Department.objects.all()
    return render(request, 'SMScourse/SMS(ED).html', {'user': request.user, 'student': student, 'departments': departments})

@student_required
@login_required
def SMS_a(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    departments = Department.objects.all()
    return render(request, 'SMScourse/SMS(A).html', {'user': request.user, 'student': student, 'departments': departments})

from django.contrib import messages
from .forms import StudentProfileForm
from .models import Student

@student_required
@login_required
def account(request):
    user = request.user

    if request.method == 'POST':
        from .forms import AccountEditForm
        form = AccountEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Account information updated successfully!")
            return redirect('account')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        from .forms import AccountEditForm
        form = AccountEditForm(instance=user)

    return render(request, 'SMS(account).html', {
        'form': form,
        'student': getattr(user, 'student_profile', None)
    })

@staff_required
@login_required
def accountstaff(request):
    user = request.user

    if request.method == 'POST':
        from .forms import AccountEditForm
        form = AccountEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Account information updated successfully!")
            return redirect('accountstaff')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        from .forms import AccountEditForm
        form = AccountEditForm(instance=user)

    return render(request, 'SMS(accountstaff).html', {
        'form': form,
        'student': getattr(user, 'student_profile', None)
    })

