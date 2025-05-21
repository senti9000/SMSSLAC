from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Student, Subject, Course, User, Staff

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    actions = ['make_superuser_and_staff']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role'),
        }),
    )

    def make_superuser_and_staff(self, request, queryset):
        updated = queryset.update(is_superuser=True, is_staff=True)
        self.message_user(request, f"{updated} user(s) were successfully marked as superuser and staff.")
    make_superuser_and_staff.short_description = "Mark selected users as superuser and staff"

class StaffAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_number', 'year_level', 'course')
    search_fields = ('user__username', 'student_number', 'course__name')



admin.site.register(User, CustomUserAdmin)
admin.site.register(Staff, StaffAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Subject)
admin.site.register(Course)
