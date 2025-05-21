"""
URL configuration for studentmanagement project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Import the include() function: from other_app.views import Home
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from student_management_system import views 
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('admin/', admin.site.urls),
    path('login/', views.login_user, name='login'),
    path('accounts/login/', views.login_user, name='accounts_login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),  
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),  
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),  # Added staff dashboard URL
    path('SMS-course/', views.SMScourse, name='SMScourse'),
    path('SMS-course-save/', views.SMScourse_save, name='SMS-course-save'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),
    path('course/<int:pk>/', views.course_record, name='course_record'),
    path('courses/', views.course_list, name='course_list'),
    path('course/edit/<int:pk>/', views.edit_course, name='edit_course'),
    path('SMS-subject/', views.SMSsubject, name='SMSsubject'),
    path('SMS-subject-save/', views.SMSsubjectsave, name='SMSsubjectsave'),
    path('delete-subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('subject/<int:pk>/', views.subject_record, name='subject_record'),
    path('subject/', views.subject_list, name='subject_list'),
    path('subject/edit/<int:pk>/', views.edit_subject, name='edit_subject'),
    path('subject/select/', views.select_subject, name='select_subject'),
    path('SMS-student/', views.SMSstudent, name='SMSstudent'),
    path('add_student_save/', views.add_student_save, name='add_student_save'),
    path('student/<int:pk>/', views.student_record, name='student_record'),
    path('student/', views.student_list, name='student_list'),
    path('student/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('delete-student/<int:student_id>/', views.delete_student, name='delete_student'), 
    path('profile/', views.student_profile, name='student_profile'),
    path('register/', views.register_page, name='register'),
    path('register/staff/', views.staff_register_page, name='staff_register'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('grades/edit/<int:student_id>/<int:subject_id>/', views.edit_grade, name='edit_grade'),
    path('grades/edit-ajax/', views.edit_grade_ajax, name='edit_grade_ajax'),  # AJAX endpoint for grade editing
    path('grades/delete-ajax/', views.delete_grade_ajax, name='delete_grade_ajax'),  # AJAX endpoint for grade deleting
    path('student/<int:student_id>/change-subject/<int:old_subject_id>/', views.change_student_subject, name='change_student_subject'),
    path('student/change-subject-ajax/', views.change_subject_ajax, name='change_subject_ajax'),
    path('student/add-subject-ajax/', views.add_student_subject_ajax, name='add_student_subject_ajax'),
    path('SMS-grade/', views.SMS_grade, name='SMS_grade'),  # New URL pattern for SMS(grade)
    path('student/drop-subject-ajax/', views.delete_removed_subject_ajax, name='delete_removed_subject_ajax'),
    path('student/restore-subject-ajax/', views.restore_student_subject_ajax, name='restore_student_subject_ajax'),
    path('student/delete-removed-subject-ajax/', views.delete_removed_subject_ajax, name='delete_removed_subject_ajax'),
    path('student/remove-subject-ajax/', views.remove_student_subject_ajax, name='remove_student_subject_ajax'),
    path('student/<int:student_id>/subjects/', views.student_subjects, name='student_subjects'),
    path('background-template/', views.background_template_view, name='background_template'),
    path('SMS-staffit/', views.SMSstaffit, name='SMSstaffit'),  # Added URL pattern for SMSstaffit view
path('SMS-staffvstu/<int:subject_id>/', views.SMSstaffvstu, name='SMSstaffvstu'),  # Existing pattern
path('SMS-staffvstu/<int:subject_id>/<str:professor_name>/', views.SMSstaffvstu, name='SMSstaffvstu_by_professor'),  # New pattern to accept professor_name
    path('SMS-staffcstu/<int:pk>/', views.SMSstaffcstu, name='SMSstaffcstu'),  # Updated URL pattern to accept pk parameter
    path('SMS-staffhm/', views.SMSstaffhm, name='SMSstaffhm'),  # Added URL pattern for SMSstaffit view
    path('SMS-staffvstuhm/<str:subject_id>/', views.SMSstaffvstuhm, name='SMSstaffvstuhm'),  # Changed subject_id to str to match model field
    path('SMS-staffcstuhm/<int:pk>/', views.SMSstaffcstuhm, name='SMSstaffcstuhm'),
    path('SMS-staffba/', views.SMSstaffba, name='SMSstaffba'),  # Added URL pattern for SMSstaffit view
    path('SMS-staffvstuba/<int:subject_id>/', views.SMSstaffvstuba, name='SMSstaffvstuba'),  # Added URL pattern for SMSstaffvstu view
    path('SMS-staffcstuba/<int:pk>/', views.SMSstaffcstuba, name='SMSstaffcstuba'),
    path('SMS-staffA/', views.SMSstaffA, name='SMSstaffA'),  # Added URL pattern for SMSstaffit view
    path('SMS-staffvstuA/<int:subject_id>/', views.SMSstaffvstuA, name='SMSstaffvstuA'),  # Added URL pattern for SMSstaffvstu view
    path('SMS-staffcstuA/<int:pk>/', views.SMSstaffcstuA, name='SMSstaffcstuA'),
    path('SMS-staffE/', views.SMSstaffE, name='SMSstaffE'),  # Added URL pattern for SMSstaffit view
    path('SMS-staffvstuE/<int:subject_id>/', views.SMSstaffvstuE, name='SMSstaffvstuE'),  # Added URL pattern for SMSstaffvstu view
    path('SMS-staffcstuE/<int:pk>/', views.SMSstaffcstuE, name='SMSstaffcstuE'),
    path('student/<int:student_id>/delete-picture/<str:picture_field>/', views.delete_student_picture, name='delete_student_picture'),
    path('student/<int:student_id>/delete-doc/<str:document_field>/', views.delete_student_doc, name='delete_student_doc'),
    path('SMS-it/', views.SMS_it, name='SMS_it'),
    path('SMS-hm/', views.SMS_hm, name='SMS_hm'),
    path('SMS-ba/', views.SMS_ba, name='SMS_ba'),
    path('SMS-ed/', views.SMS_ed, name='SMS_ed'),
    path('SMS-a/', views.SMS_a, name='SMS_a'),
    path('account/', views.account, name='account'),
    path('account-staff/', views.accountstaff, name='accountstaff'),
    path('student/update-subject-status-ajax/', views.update_subject_status_ajax, name='update_subject_status_ajax'),

    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

