import random
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager, Group, Permission
from django.utils.translation import gettext_lazy as _

# Create your models here.

class StudentManager(models.Manager):
    """Custom manager for Student model"""
    def get_queryset(self):
        return super().get_queryset()

class UserManager(UserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        STAFF = 'STAFF', _('Staff')
        STUDENT = 'STUDENT', _('Student')

    role = models.CharField(max_length=50, choices=Role.choices)
    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.role:
                self.role = User.Role.STUDENT
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF or self.is_staff

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

class Staff(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    objects = models.Manager()

    def __str__(self):
        return f"{self.user.username}"

class Course(models.Model):
    id = models.AutoField(primary_key=True)
    #course_name = models.CharField(max_length=100)
    course_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    credits = models.CharField(max_length=10)
    department_name = models.ForeignKey('Department', on_delete=models.SET_DEFAULT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    def save(self, *args, **kwargs):
        # Ensure the department exists or create it
        if self.department_name:
            if isinstance(self.department_name, str):
                department, created = Department.objects.get_or_create(name=self.department_name)
                self.department_name = department
            elif isinstance(self.department_name, Department):
                # Department instance already assigned
                pass
        else:
            # Assign default department if none provided
            default_department, created = Department.objects.get_or_create(name='General Studies')
            self.department_name = default_department
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Subject(models.Model):
    
    subject_id = models.CharField(max_length=255, unique=True) 
    subject_name = models.CharField(max_length=255, default='DEFAULT_NAME') 
    subject_code = models.CharField(max_length=10, default='CODE')   
    credits = models.IntegerField(default=0)                    
    department_name = models.ForeignKey('Department', on_delete=models.SET_DEFAULT, default=1)   
    semester_offered = models.CharField(max_length=10, default='1st') 
    professor_name = models.CharField(max_length=255)  
    year_level = models.IntegerField(default=1)    
    lecture_hour = models.IntegerField(default=0)  # Renamed from number_of_hours to lecture_hour
    laboratory_hour = models.IntegerField(default=0)  # New field for laboratory hours
    STATUS_CHOICES = [
        ('Currently Taking', 'Currently Taking'),
        ('Drop', 'Drop'),
        ('Done', 'Done'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Currently Taking')  # Fixed default value
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()             

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile', null=True)
    student_number = models.CharField(max_length=255, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=255, default='FirstName')
    middle_Name = models.CharField(max_length=255, default='MiddleName')
    last_name = models.CharField(max_length=255, default='LastName')
    place_of_birth = models.CharField(max_length=255, default='Unknown')
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    address = models.CharField(max_length=255, default='Unknown')
    phone = models.CharField(max_length=20, blank=True, default='')
    YEAR_LEVEL_CHOICES = [
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
    ]
    year_level = models.CharField(max_length=50, choices=YEAR_LEVEL_CHOICES, blank=True)  # Changed to year_level for consistency
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students', null=True, blank=True)
    department_name = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)  # Changed to ForeignKey
    
    # File fields for document uploads
    f137 = models.FileField(upload_to='documents/f137/', blank=True, null=True)
    psa_photocopy = models.FileField(upload_to='documents/psa/', blank=True, null=True)
    shs_diploma_photocopy = models.FileField(upload_to='documents/shs_diploma/', blank=True, null=True)
    good_moral = models.FileField(upload_to='documents/good_moral/', blank=True, null=True)
    honorable_dismissal = models.FileField(upload_to='documents/honorable_dismissal/', blank=True, null=True)
    original_tor = models.FileField(upload_to='documents/original_tor/', blank=True, null=True)
    pictures = models.ImageField(upload_to='pictures/', blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    STUDENT_TYPE_CHOICES = [
        ('new', 'New Student'),
        ('old', 'Old Student'),
        ('transferee', 'Transferee'),
    ]
    student_type = models.CharField(max_length=50, choices=STUDENT_TYPE_CHOICES, blank=True)
    school_name = models.CharField(max_length=255, blank=True)

    STUDENT_STATUS_CHOICES = [
        ('Enrolled', 'Enrolled'),
        ('Pending', 'Pending'),
        ('Dropped', 'Dropped'),
        ('Graduated', 'Graduated'),
    ]
    student_status = models.CharField(max_length=50, choices=STUDENT_STATUS_CHOICES, blank=True)
    verification_token = models.CharField(max_length=255, null=True, blank=True)
    verification_token_created = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    citizenship = models.CharField(max_length=50, default='Unknown')  # Changed to CharField
    STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, blank=True)  # Fixed choices

    father_name = models.CharField(max_length=255, default='Unknown')  # Changed to CharField
    mother_name = models.CharField(max_length=255, default='Unknown')  # Changed to CharField
    guardian_contact_number = models.CharField(max_length=20, default='Unknown')  # Changed to CharField
    academic_year = models.CharField(max_length=50, null=True, blank=True)  # Changed to CharField
    SEMESTER_CHOICES = [
        ('1st', '1st Semester'),
        ('2nd', '2nd Semester'),
    ]
    semester = models.CharField(max_length=50, choices=SEMESTER_CHOICES, blank=True)  # Changed to CharField
    elementary_name_year_graduated = models.CharField(max_length=255, default='Unknown')
    junior_high_name_year_graduated = models.CharField(max_length=255, default='Unknown')  # Changed to CharField
    senior_high_name_year_graduated = models.CharField(max_length=255, default='Unknown')  # Changed to CharField
    created_at = models.DateTimeField(auto_now_add=True)
    objects = StudentManager()

    def __str__(self):
        if self.user:
            return f"{self.user.username} ({self.student_status})"
        return f"Student ({self.student_status})"

    class Meta:
        # Removed default ordering by 'created_at' to avoid ordering by creation date
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def save(self, *args, **kwargs):
        if self.user and self.email and self.user.email != self.email:
            self.user.email = self.email
            self.user.save(update_fields=['email'])
        super().save(*args, **kwargs)


class Grade(models.Model):
    """Model for storing student grades for subjects"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    grade_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    semester = models.CharField(max_length=10, default='1st', blank=False, null=False)
    academic_year = models.CharField(max_length=20, blank=False, null=False)
    year_level = models.CharField(max_length=50, blank=True, null=True)  # Added year_level field
    is_active = models.BooleanField(default=True)  # New field to mark active/inactive grades

    STATUS_CHOICES = [
        ('Currently Taking', 'Currently Taking'),
        ('Drop', 'Drop'),
        ('Done', 'Done'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Currently Taking')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Automatically set semester and academic_year from student if missing or empty
        if (not self.semester or self.semester.strip() == '') and self.student and self.student.semester:
            self.semester = self.student.semester
        if (not self.academic_year or self.academic_year.strip() == '') and self.student and self.student.academic_year:
            self.academic_year = self.student.academic_year

        # Set status based on grade_value first
        if self.grade_value is not None and str(self.grade_value).strip() != '':
            self.status = "Done"
        else:
            self.status = "Currently Taking"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.grade_value}"

    class Meta:
        verbose_name = 'Grade'
        verbose_name_plural = 'Grades'
        unique_together = ('student', 'subject', 'semester', 'academic_year')

class EmailVerificationCode(models.Model):
    """Model for storing email verification codes"""
    email = models.EmailField(max_length=254)
    code = models.CharField(blank=True, max_length=6, null=True)

    def __str__(self):
        return f"Verification code for {self.email}"

    class Meta:
        verbose_name = 'Email Verification Code'
        verbose_name_plural = 'Email Verification Codes'
