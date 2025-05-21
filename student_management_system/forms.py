from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, SetPasswordForm
from .models import User, Student, Course, Subject, Grade, Staff
from django.forms.widgets import DateInput, FileInput, Select

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email
        
    def save(self, commit=True):
        user = super(UserRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control'})

class AccountEditForm(forms.ModelForm):
    password1 = forms.CharField(label='New Password', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Confirm New Password', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.id
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields must match.")
        return cleaned_data

    def save(self, commit=True):
        user = super(AccountEditForm, self).save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

class StaffRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super(StaffRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = User.Role.STAFF
        if commit:
            user.save()
            Staff.objects.create(user=user)
        return user

from .models import Department

class StudentProfileForm(forms.ModelForm):
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=False, empty_label="Choose a course")

    class Meta:
        model = Student
        fields = [
            'student_number', 'first_name', 'middle_Name', 'last_name',
            'place_of_birth', 'date_of_birth', 'email', 'gender', 'address', 'phone',
            'year_level', 'course', 'department_name', 'f137', 'psa_photocopy',
            'shs_diploma_photocopy', 'good_moral', 'honorable_dismissal',
            'original_tor', 'pictures', 'profile_pic', 'student_type',
            'school_name', 'student_status', 'citizenship', 'status',
            'father_name', 'mother_name', 'guardian_contact_number',
            'academic_year', 'semester', 'elementary_name_year_graduated',
            'junior_high_name_year_graduated', 'senior_high_name_year_graduated'
        ]
        widgets = {
            'date_of_birth': DateInput(attrs={'type': 'date'}),
            'f137': FileInput(),
            'psa_photocopy': FileInput(),
            'shs_diploma_photocopy': FileInput(),
            'good_moral': FileInput(),
            'honorable_dismissal': FileInput(),
            'original_tor': FileInput(),
            'pictures': FileInput(),
            'profile_pic': FileInput(),
            'year_level': Select(choices=Student.YEAR_LEVEL_CHOICES),
            'student_type': Select(choices=Student.STUDENT_TYPE_CHOICES),
            'student_status': Select(choices=Student.STUDENT_STATUS_CHOICES),
            'status': Select(choices=Student.STATUS_CHOICES),
            'semester': Select(choices=Student.SEMESTER_CHOICES),
            'gender': Select(choices=Student.GENDER_CHOICES),
            'first_name': forms.TextInput(attrs={
                'placeholder': 'Enter your first name',
                'minlength': '2',
                'maxlength': '50'
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': 'Enter your last name',
                'minlength': '2',
                'maxlength': '50'
            }),
            'department_name': forms.Select(attrs={
                'placeholder': 'Choose your department'
            }),
            'mother_name': forms.TextInput(attrs={
                'placeholder': 'Enter your mother\'s name',
                'minlength': '2',
                'maxlength': '50'
            })
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Disable student_number and student_status fields if instance exists (updating)
        if self.instance and self.instance.pk:
            if 'student_number' in self.fields:
                self.fields['student_number'].disabled = True
            # Removed disabling of student_status to make it editable
            # if 'student_status' in self.fields:
            #     self.fields['student_status'].disabled = True
        if self.user and not (self.user.is_staff or self.user.is_superuser):
            fields_to_disable = [
                'department_name', 'year_level', 'course',
                'student_type', 'student_status', 'school_name',
                'academic_year', 'semester'
            ]
            for field_name in fields_to_disable:
                if field_name in self.fields:
                    self.fields[field_name].disabled = True
        for field in self.fields.values():
            field.error_messages = {'required': 'This field is required.'}

    def clean(self):
        cleaned_data = super().clean()
        # Restore student_number and student_status if disabled
        if self.instance and self.instance.pk:
            if 'student_number' in self.fields and self.fields['student_number'].disabled:
                cleaned_data['student_number'] = getattr(self.instance, 'student_number')
            if 'student_status' in self.fields and self.fields['student_status'].disabled:
                cleaned_data['student_status'] = getattr(self.instance, 'student_status')
        # Validate required fields
        year_level = cleaned_data.get('year_level')
        semester = cleaned_data.get('semester')
        course = cleaned_data.get('course')
        department_name = cleaned_data.get('department_name')

        if not year_level:
            self.add_error('year_level', 'Year level is required.')
        if not semester:
            self.add_error('semester', 'Semester is required.')
        if not course:
            self.add_error('course', 'Course selection is required.')
        if not department_name:
            self.add_error('department_name', 'Department selection is required.')

        if self.user and not (self.user.is_staff or self.user.is_superuser):
            fields_to_disable = [
                'student_type', 'student_status', 'school_name',
                'academic_year'
            ]
            for field_name in fields_to_disable:
                if field_name in self.fields:
                    # Restore the initial value for disabled fields to prevent loss on save
                    cleaned_data[field_name] = getattr(self.instance, field_name)
        return cleaned_data
    
    

from .models import Department

class SubjectForm(forms.ModelForm):
    department_name = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        empty_label="Choose a department",
        label="Choose a department",
        help_text="Choose a department"
    )
    from .models import Student

    year_level = forms.ChoiceField(
        choices=[('', 'Choose year level')] + Student.YEAR_LEVEL_CHOICES,
        required=True
    )
    semester_offered = forms.ChoiceField(
        choices=[('', 'Choose semester offered')] + Student.SEMESTER_CHOICES,
        required=True
    )

    class Meta:
        model = Subject
        fields = ['subject_name', 'subject_code', 'credits', 'department_name', 
                 'semester_offered', 'professor_name', 'year_level', 'course_id',
                 'lecture_hour', 'laboratory_hour']

class SubjectSelectForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        label="Select Subject",
        empty_label="Choose a subject",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class ChangeStudentSubjectForm(forms.Form):
    new_subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        label="Select New Subject",
        empty_label="Choose a new subject",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        old_subject = kwargs.pop('old_subject', None)
        super().__init__(*args, **kwargs)
        if student and old_subject:
            # Filter subjects to those in the student's course excluding the old subject
            self.fields['new_subject'].queryset = Subject.objects.filter(
                course_id=student.course
            ).exclude(id=old_subject.id)
        else:
            self.fields['new_subject'].queryset = Subject.objects.all()

class AddStudentSubjectForm(forms.Form):
    new_subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        label="Select Subject to Add",
        empty_label="Choose a subject",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        if student:
            # Filter subjects to those in the student's course excluding already assigned subjects
            assigned_subject_ids = student.grades.values_list('subject_id', flat=True)
            self.fields['new_subject'].queryset = Subject.objects.filter(
                course_id=student.course
            ).exclude(id__in=assigned_subject_ids)
        else:
            self.fields['new_subject'].queryset = Subject.objects.all()

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_id', 'name', 'credits', 'department_name']

class GradeForm(forms.ModelForm):
    year_level = forms.ChoiceField(
        choices=Student.YEAR_LEVEL_CHOICES,
        required=False,
        label="Year Level"
    )

    def __init__(self, *args, disable_semester_year=True, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show student and subject fields when creating a new grade
        if not self.instance.pk:
            self.fields['student'] = forms.ModelChoiceField(
                queryset=Student.objects.all(),
                widget=forms.HiddenInput()
            )
            self.fields['subject'] = forms.ModelChoiceField(
                queryset=Subject.objects.all(),
                widget=forms.HiddenInput()
            )
        else:
            # Disable semester and academic_year fields when editing existing grade
            if disable_semester_year:
                self.fields['semester'].disabled = True
                self.fields['academic_year'].disabled = True
            else:
                self.fields['semester'].disabled = False
                self.fields['academic_year'].disabled = False

    class Meta:
        model = Grade
        fields = ['student', 'subject', 'grade_value', 'semester', 'academic_year', 'year_level']
        widgets = {
            'semester': forms.Select(choices=[
                ('1st', '1st Semester'),
                ('2nd', '2nd Semester')
            ]),
            'grade_value': forms.NumberInput(attrs={
                'min': 0,
                'max': 100,
                'step': 0.01
            }),
            'student': forms.HiddenInput(),
            'subject': forms.HiddenInput()
        }

    def clean_grade_value(self):
        grade_value = self.cleaned_data.get('grade_value')
        if grade_value is not None and (grade_value < 0 or grade_value > 100):
            raise forms.ValidationError("Grade must be between 0 and 100")
