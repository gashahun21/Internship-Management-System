from rest_framework import viewsets, generics
from django.shortcuts import render, redirect
from dateutil.relativedelta import relativedelta
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models.functions import Coalesce
from django.db.models import Value
from django.db.models import Avg
from django.db.models import Exists, OuterRef
from django.db.models import Subquery, OuterRef
from .models import *
from datetime import datetime
from django.http import JsonResponse
import myapp.templatetags.custom_filters
from django.db.models import Q
from .models import Feedback,CompanyFeedback,ChatMessage, PrivateMessage
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
import openai
from .serializers import *
from .models import UserRole
from .forms import *
    
def home(request):
    # Redirect authenticated users
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    return render(request, 'home.html')
@login_required
@user_passes_test(lambda u: u.is_department_head)
def advisor_assigned_student_departmenet_head(request, advisor_id):
    # Get the advisor
    advisor = get_object_or_404(Advisor, user_id=advisor_id)
    
    # Get the students assigned to this advisor
    assigned_students = Student.objects.filter(assigned_advisor=advisor)
    
    # Pass the data to the template
    return render(request, 'students/advisor_assigned_students.html', {
        'advisor': advisor,
        'assigned_students': assigned_students,
    })

@login_required
@user_passes_test(lambda u: u.is_advisor)
def advisor_assigned_students(request, advisor_id):
    # Get the advisor
    advisor = get_object_or_404(Advisor, user_id=advisor_id)
    
    # Get the students assigned to this advisor
    assigned_students = Student.objects.filter(assigned_advisor=advisor)
    
    # Pass the data to the template
    return render(request, 'advisors/assigned_students.html', {
        'advisor': advisor,
        'assigned_students': assigned_students,
    })
@login_required
@user_passes_test(lambda u: u.is_department_head)
def assign_advisor(request, student_user_id):
    student = get_object_or_404(Student, user_id=student_user_id)
    if request.method == 'POST':
        form = AssignAdvisorForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Advisor assigned successfully!')
            return redirect('student_management')
    else:
        form = AssignAdvisorForm(instance=student)
    return render(request, 'advisors/assign_advisor.html', {'form': form, 'student': student})

@login_required
def communication_page(request):
    return render(request, 'departement_head/communication_page.html')
@login_required
def existing_internships(request):
    # Fetch all internships
    internships = Internship.objects.all()
    
    # Pass the internships to the template
    context = {
        'internships': internships,
    }
    return render(request, 'company/existing_internships.html', context)


@login_required
def accept_application(request, application_id):
    # Ensure only company admins can accept applications
    if not request.user.is_company_admin:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('applicant_list', internship_id=application.internship.id)

    # Get the application
    application = get_object_or_404(Application, id=application_id)

    # Update the application status to "Approved"
    application.status = 'Approved'
    application.save()

    messages.success(request, f"Application {application_id} has been approved.")
    return redirect('applicant_list', internship_id=application.internship.id)

@login_required
def reject_application(request, application_id):
    # Ensure only company admins can reject applications
    if not request.user.is_company_admin:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('applicant_list', internship_id=application.internship.id)

    # Get the application
    application = get_object_or_404(Application, id=application_id)

    # Update the application status to "Rejected"
    application.status = 'Rejected'
    application.save()

    messages.success(request, f"Application {application_id} has been rejected.")
    return redirect('applicant_list', internship_id=application.internship.id)

def post_internship(request):
    if request.method == 'POST':
        form = InternshipForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('company_admin_dashboard')
    else:
        form = InternshipForm()
    return render(request, 'company/post_internship.html', {'form': form})
def view_internships(request):
    internships = Internship.objects.filter(company=request.user.companyadmin.company)
    return render(request, 'company/view_internships.html', {'internships': internships})
def update_internship(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)
    if request.method == "POST":
        # Handle form submission to update the internship
        form = InternshipForm(request.POST, instance=internship)
        if form.is_valid():
            form.save()
            messages.success(request, 'Internship updated successfully!')
            return redirect('view_internships')
    else:
        form = InternshipForm(instance=internship)
    return render(request, 'company/update_intern.html', {'form': form})

def delete_internship(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)
    if request.method == "POST":
        internship.delete()
        messages.success(request, 'Internship deleted successfully!')
    return redirect('view_internships')

def toggle_internship_status(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)
    internship.is_open = not internship.is_open  # Toggle the status
    internship.save()
    messages.success(request, f'Internship status updated to {"Open" if internship.is_open else "Closed"}.')
    return redirect('view_internships')

def apply_internship(request, internship_id):
    # Get the internship
    internship = get_object_or_404(Internship, id=internship_id)
    
    # Get the logged-in student
    student = get_object_or_404(Student, user=request.user)

    # Check if the internship is open
    if not internship.is_open:
        messages.error(request, 'This internship is closed and cannot be applied to.')
        return redirect('view_internships')

    # Check if the student has already applied
    if Application.objects.filter(student=student, internship=internship).exists():
        messages.warning(request, 'You have already applied for this internship.')
        return redirect('view_internships')

    # Create a new application
    Application.objects.create(
        student=student,
        internship=internship,
        status='Pending'  # Default status
    )
    messages.success(request, 'Your application has been submitted successfully!')
    return redirect('view_internships')

def applicant_list(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)
    applications = Application.objects.filter(internship=internship).select_related('student')

    # Prepare a list of applicants with their details
    applicants = []
    for application in applications:
        student = application.student
        applicant_data = {
            'name': f"{student.user.first_name} {student.user.last_name}",
            'email': student.user.email,
            'id': application.id,  # Application ID
            'status': application.status,  # Application status
        }
        applicants.append(applicant_data)

    context = {
        'internship': internship,
        'applicants': applicants,
    }
    return render(request, 'company/applicant_list.html', context)

@login_required
def apply_internship(request, internship_id):
    # Get the internship by its ID
    internship = get_object_or_404(Internship, id=internship_id)

    # Ensure only students can apply for internships
    if not hasattr(request.user, 'student'):
        messages.error(request, "Only students can apply for internships.")
        return redirect('existing_internships')

    student = request.user.student

    # Check if the student has already applied to this internship
    if Application.objects.filter(internship=internship, student=student).exists():
        messages.error(request, "You have already applied to this internship.")
        return redirect('existing_internships')

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.internship = internship  # Assign the internship from the URL
            application.student = student  # Assign the logged-in student
            application.save()  # Save the application to the database
            messages.success(request, "Your application has been submitted!")
            return redirect('applicant_list', internship_id=internship.id)  # Redirect to the applicant list
        else:
            messages.error(request, "There was an error with your application. Please try again.")
    else:
        form = ApplicationForm()

    return render(request, 'students/apply_internship.html', {'internship': internship, 'form': form})
@login_required
@user_passes_test(lambda u: hasattr(u, 'departmenthead'))  # Only Department Heads
def grant_chat_permission(request, student_id):
    department_head = request.user.departmenthead
    student = get_object_or_404(Student, user_id=student_id)

    # Get the approved internship for this student
    application = Application.objects.filter(student=student, status='Approved').first()
    if not application:
        messages.error(request, "Student has no approved internship.")
        return redirect('list_internships')  # Redirect to internship selection

    internship = application.internship

    # Prevent duplicate permissions
    if ChatGroupPermission.objects.filter(student=student, internship=internship).exists():
        messages.error(request, "Permission already exists for this student.")
        return redirect('list_students', internship_id=internship.id)

    if request.method == 'POST':
        form = ChatGroupPermissionForm(request.POST, department_head=department_head, student=student, internship=internship)
        if form.is_valid():
            ChatGroupPermission.objects.create(
                student=student,
                internship=internship,
                department_head=department_head
            )
            messages.success(request, "Chat permission granted successfully!")
            return redirect('list_students_for_permission', internship_id=internship.id)
    else:
        form = ChatGroupPermissionForm(department_head=department_head, student=student, internship=internship)

    return render(request, 'departement_head/grant_permission.html', {
        'form': form,
        'student': student,
        'internship': internship
    })

@login_required
def list_students_for_permission(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)
    students = Student.objects.filter(
        application__internship=internship,
        application__status='Approved'
    ).distinct()

    return render(request, 'departement_head/list_students.html', {
        'internship': internship,
        'students': students,
    })

@login_required
@user_passes_test(lambda u: hasattr(u, 'departmenthead'))  # Only Department Heads
def list_internships_for_permission(request):
    department_head = request.user.departmenthead

    internships = Internship.objects.filter(
        application__status='Approved',
        application__student__department=department_head.department
    ).distinct()

    return render(request, 'departement_head/list_internships.html', {
        'internships': internships,
    })

@login_required
def chat_with_company_admin(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    company_admins = CompanyAdmin.objects.filter(company=company)
    
    if not company_admins.exists():
        messages.error(request, "No company admin found for this company.")
        return redirect('view_company', company_id=company_id)

    # Assuming a one-to-one chat with the first company admin
    company_admin = company_admins.first()

    return redirect('private_chat', user_id=company_admin.user.id)

def company_supervisors(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    supervisors = Supervisor.objects.filter(company=company)  # Ensure this query is correct

    return render(request, 'supervisor/supervisors.html', {
        'company': company,
        'supervisors': supervisors
    })


@login_required
def private_chat_list(request, role):
    """Displays a list of users the logged-in user can chat with, based on their role."""
    users = []
    user = request.user

    # Department Head Logic
    if hasattr(user, 'departmenthead'):
        department = user.departmenthead.department

        if role == 'supervisors':
            # Only show supervisors who have students from the department head's department
            users = Supervisor.objects.filter(
                assigned__student__department=department  # Filter supervisors by students in the department
            ).distinct()
        elif role == 'advisors':
            users = Advisor.objects.filter(department=department).distinct()

        elif role == 'company_admins':
            # Company Admins with approved students from the department head's department
            users = CompanyAdmin.objects.filter(
                company__internship__application__student__department=department,
                company__internship__application__status='Approved'
            ).distinct()

    # Advisor Logic
    elif hasattr(user, 'advisor'):
        advisor = user.advisor
        department = advisor.department

        if role == 'department_heads':
            # Department Head of the same department
            users = DepartmentHead.objects.filter(department=department)

        elif role == 'supervisors':
            # Supervisors with common assigned students
            users = Supervisor.objects.filter(
                student__assigned_advisor=advisor
            ).distinct()

    # Supervisor Logic
    elif hasattr(user, 'supervisor'):
        supervisor = user.supervisor

        if role == 'advisors':
            # Advisors with common assigned students
            users = Advisor.objects.filter(
                student__assigned_supervisor=supervisor
            ).distinct()

        elif role == 'department_heads':
            # Department Heads where students from their department are assigned to this supervisor
            users = DepartmentHead.objects.filter(
                department__student__assigned_supervisor=supervisor
            ).distinct()

    # Company Admin Logic
    elif hasattr(user, 'companyadmin'):
        company = user.companyadmin.company

        if role == 'department_heads':
            # Department Heads with approved students from their department in this company's internships
            users = DepartmentHead.objects.filter(
                department__student__application__internship__company=company,
                department__student__application__status='Approved'
            ).distinct()

    return render(request, 'private_chat_list.html', {
        'users': users,
        'role': role
    })
@login_required
def private_chat(request, user_id):
    if request.user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(request.user, "is_department_head", False):
        base_template = "departement_head/base.html"
    elif getattr(request.user, "is_advisor", False):
        base_template = "advisors/base.html"
    elif getattr(request.user, "is_supervisor", False):
        base_template = "supervisor/base.html"
    elif getattr(request.user, "is_student", False):
        base_template = "students/base.html"
    elif getattr(request.user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        base_template = "base.html"

    receiver = get_object_or_404(User, id=user_id)
    sender = request.user
    allowed = False

    # Department Head
    if hasattr(sender, 'departmenthead'):
        department = sender.departmenthead.department
        if hasattr(receiver, 'supervisor'):
            allowed = Application.objects.filter(
                internship__company=receiver.supervisor.company,
                student__department=department,
                status='Approved'
            ).exists()
        elif hasattr(receiver, 'companyadmin'):
            allowed = Application.objects.filter(
                internship__company=receiver.companyadmin.company,
                student__department=department,
                status='Approved'
            ).exists()
        elif hasattr(receiver, 'advisor'):
            allowed = department == receiver.advisor.department

    # Advisor
    elif hasattr(sender, 'advisor'):
        advisor = sender.advisor
        if hasattr(receiver, 'departmenthead'):
            allowed = advisor.department == receiver.departmenthead.department
        elif hasattr(receiver, 'supervisor'):
            allowed = Student.objects.filter(
                assigned_advisor=advisor,
                assigned_supervisor=receiver.supervisor
            ).exists()

    # Supervisor
    elif hasattr(sender, 'supervisor'):
        supervisor = sender.supervisor
        if hasattr(receiver, 'advisor'):
            allowed = Student.objects.filter(
                assigned_supervisor=supervisor,
                assigned_advisor=receiver.advisor
            ).exists()
        elif hasattr(receiver, 'departmenthead'):
            allowed = Student.objects.filter(
                assigned_supervisor=supervisor,
                department=receiver.departmenthead.department
            ).exists()

    # Company Admin
    elif hasattr(sender, 'companyadmin'):
        company = sender.companyadmin.company
        if hasattr(receiver, 'departmenthead'):
            allowed = Application.objects.filter(
                internship__company=company,
                student__department=receiver.departmenthead.department,
                status='Approved'
            ).exists()

    if not allowed:
        messages.error(request, "You are not allowed to chat with this user.")
        return redirect('dashboard_redirect')

    # Handle POST
    if request.method == 'POST':
        message_content = request.POST.get('message')
        file = request.FILES.get('file')

        if message_content or file:
            message_type = 'text'
            if file:
                if file.content_type.startswith('image'):
                    message_type = 'image'
                elif file.content_type.startswith('video'):
                    message_type = 'video'
                else:
                    message_type = 'file'

            PrivateMessage.objects.create(
                sender=sender,
                receiver=receiver,
                content=message_content,
                file=file,
                message_type=message_type
            )
            messages.success(request, "Message sent successfully!")
        else:
            messages.warning(request, "Message cannot be empty!")
        return redirect('private_chat', user_id=user_id)

    chat_messages = PrivateMessage.objects.filter(
        Q(sender=sender, receiver=receiver) |
        Q(sender=receiver, receiver=sender)
    ).order_by('timestamp')

    return render(request, 'departement_head/private_chat.html', {
        'receiver': receiver,
        'chat_messages': chat_messages,
        'base_template': base_template
    })
@login_required
def clear_chat_history(request, user_id):
    """
    Clears the chat history between the logged-in user and the specified user.
    """
    receiver = get_object_or_404(User, id=user_id)
    
    # Ensure the user has permission to clear the chat history
    allowed = False
    sender = request.user

    # Department Head Chat Permissions
    if hasattr(sender, 'departmenthead'):
        department = sender.departmenthead.department

        if hasattr(receiver, 'supervisor'):
            allowed = Application.objects.filter(
                internship__company=receiver.supervisor.company,
                student__department=department,
                status='Approved'
            ).exists()

        elif hasattr(receiver, 'companyadmin'):
            allowed = Application.objects.filter(
                internship__company=receiver.companyadmin.company,
                student__department=department,
                status='Approved'
            ).exists()
        elif hasattr(receiver, 'advisor'):
            allowed = sender.departmenthead.department == receiver.advisor.department

    # Advisor Chat Permissions
    elif hasattr(sender, 'advisor'):
        advisor = sender.advisor

        if hasattr(receiver, 'departmenthead'):
            allowed = advisor.department == receiver.departmenthead.department

        elif hasattr(receiver, 'supervisor'):
            allowed = Student.objects.filter(
                assigned_advisor=advisor,
                assigned_supervisor=receiver.supervisor
            ).exists()

    # Supervisor Chat Permissions
    elif hasattr(sender, 'supervisor'):
        supervisor = sender.supervisor

        if hasattr(receiver, 'advisor'):
            allowed = Student.objects.filter(
                assigned_supervisor=supervisor,
                assigned_advisor=receiver.advisor
            ).exists()

        elif hasattr(receiver, 'departmenthead'):
            allowed = Student.objects.filter(
                assigned_supervisor=supervisor,
                department=receiver.departmenthead.department
            ).exists()

    # Company Admin Chat Permissions
    elif hasattr(sender, 'companyadmin'):
        company = sender.companyadmin.company

        if hasattr(receiver, 'departmenthead'):
            allowed = Application.objects.filter(
                internship__company=company,
                student__department=receiver.departmenthead.department,
                status='Approved'
            ).exists()

    if not allowed:
        messages.error(request, "You are not allowed to clear chat history with this user.")
        return redirect('dashboard_redirect')

    # Delete all messages between the sender and receiver
    PrivateMessage.objects.filter(
        Q(sender=sender, receiver=receiver) |
        Q(sender=receiver, receiver=sender)
    ).delete()

    messages.success(request, "Chat history cleared successfully!")
    return redirect('private_chat', user_id=user_id)

@login_required
def group_chat(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)

    # Determine base template based on user role
    user = request.user
    if user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(user, "is_department_head", False):
        base_template = "departement_head/base.html"
    elif getattr(user, "is_advisor", False):
        base_template = "advisors/base.html"
    elif getattr(user, "is_supervisor", False):
        base_template = "supervisor/base.html"
    elif getattr(user, "is_student", False):
        base_template = "students/base.html"
    elif getattr(user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        base_template = "base.html"

    # Permission check
    if not group.can_communicate(user):
        messages.error(request, "You don't have permission to access this group")
        return redirect('communication_page')

    # Handle message post
    if request.method == 'POST':
        form = GroupMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = user
            message.group = group

            # Determine message type
            if message.file:
                file_type = message.file.name.split('.')[-1].lower()
                if file_type in ['jpg', 'jpeg', 'png', 'gif']:
                    message.message_type = 'image'
                elif file_type in ['mp4', 'mov', 'avi']:
                    message.message_type = 'video'
                else:
                    message.message_type = 'file'
            else:
                message.message_type = 'text'

            message.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'file_url': message.file.url if message.file else None,
                        'message_type': message.message_type,
                        'sender': user.username,
                        'timestamp': message.timestamp.isoformat()
                    }
                })
            return redirect('group_chat', group_id=group.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                }, status=400)

    # Fetch messages and form
    messages = GroupMessage.objects.filter(group=group).order_by('timestamp')
    form = GroupMessageForm()

    return render(request, 'departement_head/group_chat.html', {
        'group': group,
        'messages': messages,
        'form': form,
        'base_template': base_template
    })
@login_required
@user_passes_test(lambda u: u.is_department_head)
def create_department_group(request):
    if request.method == 'POST':
        form = ChatGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.created_by_role = 'department_head'
            group.department = request.user.departmenthead.department
            group.save()
            
            # Add participants: students in the department AND the department head
            group.add_participants()  # Adds students
            group.participants.add(request.user)  # Add department head as a participant
            
            messages.success(request, "Department group created successfully!")
            return redirect('group_chat', group_id=group.id)
    else:
        form = ChatGroupForm()
    
    return render(request, 'departement_head/create_department.html', {'form': form})

# Advisor Group Creation
# views.py
@login_required
@user_passes_test(lambda u: u.is_advisor)
def create_advisor_group(request):
    advisor = request.user.advisor  # Get the logged-in advisor

    if request.method == 'POST':
        form = AdvisorChatGroupForm(request.POST, advisor=advisor)
        if form.is_valid():
            group = form.save()
            messages.success(request, "Advisor group created successfully!")
            return redirect('group_chat', group_id=group.id)
    else:
        form = AdvisorChatGroupForm(advisor=advisor)
    
    return render(request, 'advisors/create_advisor.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_supervisor)
def create_supervisor_group(request):
    if request.method == 'POST':
        form = ChatGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.created_by_role = 'supervisor'
            group.supervisor = request.user.supervisor
            group.save()
            
            # Automatically add participants
            group.add_participants()
            
            messages.success(request, "Supervisor group created successfully!")
            return redirect('group_chat', group_id=group.id)
    else:
        form = ChatGroupForm()
    
    return render(request, 'groups/create_supervisor.html', {'form': form})
@login_required
@user_passes_test(lambda u: u.is_student)
def create_student_group(request):
    if request.method == 'POST':
        form = ChatGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.created_by_role = 'student'
            group.internship = request.user.student.internship
            group.save()
            
            # Automatically add participants
            group.add_participants()
            
            messages.success(request, "Student group created successfully!")
            return redirect('group_chat', group_id=group.id)
    else:
        form = ChatGroupForm()
    
    return render(request, 'students/create_student.html', {'form': form})

@login_required
def list_chat_groups(request):
    user = request.user
    groups = ChatGroup.objects.none()

    # Determine base template
    if user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(user, "is_department_head", False):
        base_template = "departement_head/base.html"
    elif getattr(user, "is_advisor", False):
        base_template = "advisors/base.html"
    elif getattr(user, "is_supervisor", False):
        base_template = "supervisor/base.html"
    elif getattr(user, "is_student", False):
        base_template = "students/base.html"
    elif getattr(user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        base_template = "base.html"

    # Fetch groups based on role
    if getattr(user, "is_department_head", False):
        department = user.departmenthead.department
        groups = ChatGroup.objects.filter(
            Q(department=department) |
            Q(participants=user)
        )
    elif getattr(user, "is_student", False):
        department = user.student.department
        groups = ChatGroup.objects.filter(
            Q(department=department) |
            Q(participants=user)
        )
    elif getattr(user, "is_advisor", False):
        groups = ChatGroup.objects.filter(
            Q(advisor=user.advisor) |
            Q(participants=user)
        )
    elif getattr(user, "is_supervisor", False):
        groups = ChatGroup.objects.filter(
            Q(supervisor=user.supervisor) |
            Q(participants=user)
        )

    return render(request, 'departement_head/list_chat_groups.html', {
        'groups': groups.distinct().order_by('-created_at'),
        'base_template': base_template
    })

from django.views.decorators.csrf import csrf_exempt
@login_required
@csrf_exempt
def send_group_message(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)
    
    if not group.can_communicate(request.user):
        return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)

    if request.method == "POST":
        form = GroupMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.group = group
            message.sender = request.user
            
            # Handle file upload and set message type
            if 'file' in request.FILES:
                file = request.FILES['file']
                message.file = file
                
                # Determine message type based on file content type
                if file.content_type.startswith('image'):
                    message.message_type = 'image'
                elif file.content_type.startswith('video'):
                    message.message_type = 'video'
                else:
                    message.message_type = 'file'
            else:
                message.message_type = 'text'
                
            message.save()
            
            # Mark message as read by sender
            message.read_by.add(request.user)
            
            # Prepare response data
            response_data = {
                'status': 'success',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'file_url': message.file.url if message.file else None,
                    'file_name': message.file.name if message.file else None,
                    'file_size': message.file.size if message.file else None,
                    'message_type': message.message_type,
                    'sender': request.user.username,
                    'timestamp': message.timestamp.strftime('%H:%M'),
                    'is_sender': True,
                    'is_admin': request.user in group.admins.all(),
                    'read': False
                }
            }
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

# views.py
@login_required
@require_POST
def edit_message(request, message_id):
    message = get_object_or_404(GroupMessage, id=message_id)
    
    if message.sender != request.user and not request.user in message.group.admins.all():
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    form = GroupMessageForm(request.POST, request.FILES, instance=message)
    if form.is_valid():
        form.save()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'errors': form.errors})

@login_required
@require_POST
def delete_message(request, message_id):
    message = get_object_or_404(GroupMessage, id=message_id)
    
    if message.sender != request.user and not request.user in message.group.admins.all():
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    message.soft_delete()
    return JsonResponse({'status': 'success'})
@login_required
def manage_group(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)
    
    if not group.can_edit(request.user):
        messages.error(request, "You don't have permission to manage this group")
        return redirect('list_chat_groups')
    
    if request.method == 'POST':
        if 'delete_group' in request.POST:
            group.soft_delete()
            messages.success(request, "Group deleted successfully")
            return redirect('list_chat_groups')
        
        form = ChatGroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Group updated successfully")
            return redirect('group_chat', group_id=group.id)
    
    return render(request, 'groups/manage.html', {
        'group': group,
        'form': ChatGroupForm(instance=group)
    })
def profile(request):
    if request.user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(request.user, "is_department_head", False):
        base_template = "departement_head/base.html"
    elif getattr(request.user, "is_advisor", False):
        base_template = "advisors/base.html"
    elif getattr(request.user, "is_supervisor", False):
        base_template = "supervisor/base.html"
    elif getattr(request.user, "is_student", False):
        base_template = "students/base.html"
    elif getattr(request.user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        base_template = "base.html"  # Default fallback template

    return render(request, "departement_head/profile.html", {"base_template": base_template})


@login_required
def edit_profile(request):
    user = request.user

    # Determine base template based on user role
    if user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(user, "is_department_head", False):
        base_template = "departement_head/base.html"
    elif getattr(user, "is_advisor", False):
        base_template = "advisors/base.html"
    elif getattr(user, "is_supervisor", False):
        base_template = "supervisor/base.html"
    elif getattr(user, "is_student", False):
        base_template = "students/base.html"
    elif getattr(user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        base_template = "base.html"  # Default fallback template

    if request.method == "POST":
        user.email = request.POST.get("email")
        user.phone = request.POST.get("phone")
        user.bio = request.POST.get("bio")
        user.address = request.POST.get("address")

        if "profile_image" in request.FILES:
            user.profile_image = request.FILES["profile_image"]
            print("Profile image uploaded.")

        user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return render(request, "departement_head/edit_profile.html", {"base_template": base_template})


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class CRUDMixin(LoginRequiredMixin):
    model = None
    form_class = None
    success_url = reverse_lazy('home')
    template_name = 'crud_form.html'
# ---------------------------- USER CRUD VIEWS ----------------------------
class RoleSelectionView(TemplateView):
    template_name = 'role_selection.html'
def user_create(request):
    if request.method == 'POST':
        # Get the selected role from the POST data
        role = request.POST.get('role')
        form = UserCreationWithRoleForm(request.POST)
        if form.is_valid():
            # Save the user with the selected role
            form.save()
            messages.success(request, 'User created successfully!')
            return redirect('admin_dashboard')
        else:
            print("Form errors:", form.errors)  # Debugging: Print form errors
    else:
        # Get the selected role from the query parameters
        role = request.GET.get('role')
        form = UserCreationWithRoleForm(initial={'role': role})
    
    return render(request, 'user_create.html', {'form': form})
class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating a new user.
    Accessible only by superusers.
    """
    model = User
    form_class = UserForm
    template_name = 'form.html'  # Template for the form
    success_url = reverse_lazy('admin_dashboard')  # Redirect to admin dashboard after creation

    def test_func(self):
        """Ensure only superusers can create users."""
        return self.request.user.is_superuser

    def form_valid(self, form):
        """Set additional fields or perform actions before saving the user."""
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for updating user information based on their role.
    Accessible only by superadmins.
    """
    model = get_user_model()
    template_name = 'form.html'
    success_url = reverse_lazy('admin_dashboard')  # Redirect after update

    def test_func(self):
        """Ensure only superadmins can update users."""
        return self.request.user.is_superuser

    def get_form_class(self):
        """Return the appropriate form based on the user's role."""
        user = self.get_object()
        if user.is_student:
            return SuperadminStudentForm
        elif user.is_advisor:
            return SuperadminAdvisorForm
        elif user.is_supervisor:
            return SuperadminSupervisorForm
        elif user.is_department_head:
            return DepartmentHeadRegistrationForm  # Updated for Department Head role
        elif user.is_company_admin:
            return CompanyAdminRegistrationForm  # Updated for Company Admin role
        else:
            return BaseRegistrationForm  # Default form for system admins, etc.

    def form_valid(self, form):
        """Perform actions before saving the form."""
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)
    """
    View for updating an existing user.
    Accessible only by superusers.
    """
    model = User
    form_class = UserForm
    template_name = 'form.html'  # Template for the form
    success_url = reverse_lazy('admin_dashboard')  # Redirect to admin dashboard after update

    def test_func(self):
        """Ensure only superusers can update users."""
        return self.request.user.is_superuser

    def form_valid(self, form):
        """Set additional fields or perform actions before saving the user."""
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)

class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View for deleting an existing user.
    Accessible only by superusers.
    """
    model = User
    template_name = 'users/user_confirm_delete.html'  # Template for delete confirmation
    success_url = reverse_lazy('admin_dashboard')  # Redirect to admin dashboard after deletion

    def test_func(self):
        """Ensure only superusers can delete users."""
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        """Display a success message after deletion."""
        messages.success(self.request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)
# UserRole CRUD
class UserRoleListView(CRUDMixin, ListView):
    model = UserRole
    template_name = 'user_role/list.html'
    context_object_name = 'user_roles'

class UserRoleCreateView(CreateView):
    model = UserRole
    form_class = UserRoleForm
    template_name = 'crud_form.html'  # Ensure this matches the template name
    success_url = reverse_lazy('admin_dashboard')

class UserRoleUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = UserRole
    form_class = UserRoleForm
    success_url = reverse_lazy('user_role_list')

class UserRoleDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = UserRole
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('user_role_list')
# CustomFieldValue CRUD
class CustomFieldValueListView(CRUDMixin, ListView):
    model = CustomFieldValue
    template_name = 'custom_field_value/list.html'
    context_object_name = 'custom_field_values'

class CustomFieldValueCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = CustomFieldValue
    form_class = CustomFieldValueForm
    success_url = reverse_lazy('custom_field_value_list')

class CustomFieldValueUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = CustomFieldValue
    form_class = CustomFieldValueForm
    success_url = reverse_lazy('custom_field_value_list')

class CustomFieldValueDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = CustomFieldValue
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('custom_field_value_list')
# CustomField CRUD
class CustomFieldListView(CRUDMixin, ListView):
    model = CustomField
    template_name = 'custom_field/list.html'
    context_object_name = 'custom_fields'

class CustomFieldCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = CustomField
    form_class = CustomFieldForm
    success_url = reverse_lazy('custom_field_list')

class CustomFieldUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = CustomField
    form_class = CustomFieldForm
    success_url = reverse_lazy('custom_field_list')

class CustomFieldDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = CustomField
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('custom_field_list')

# Department CRUD
class DepartmentListView(CRUDMixin, ListView):
    model = Department
    template_name = 'department/list.html'
    context_object_name = 'departments'
class DepartmentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'department/department_form.html'
    success_url = reverse_lazy('admin_dashboard')

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, 'Department created successfully!')
        return super().form_valid(form)

class DepartmentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'department/department_form.html'
    success_url = reverse_lazy('admin_dashboard')

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, 'Department updated successfully!')
        return super().form_valid(form)

class DepartmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Department
    template_name = 'departments/department_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard')

    def test_func(self):
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Department deleted successfully!')
        return super().delete(request, *args, **kwargs)


def department_head_create(request):
    if request.method == 'POST':
        form = DepartmentHeadRegistrationForm(request.POST)
        if form.is_valid():
            # Save the form (this will create a new user and department head)
            form.save()
            messages.success(request, 'Department head registered successfully.')
            return redirect('admin_dashboard')  # Redirect to the admin dashboard
        else:
            print("Form errors:", form.errors)  # Debugging: Print form errors
    else:
        form = DepartmentHeadRegistrationForm()
    
    return render(request, 'departement_head/department_head_create.html', {'form': form})

def department_head_update(request, department_id):
    department = get_object_or_404(Department, id=department_id)  # Get the department
    department_head = DepartmentHead.objects.filter(department=department).first()  # Get the current department head

    if request.method == 'POST':
        form = DepartmentHeadUpdateForm(request.POST, instance=department_head)
        if form.is_valid():
            # Save the form (this will update or create the department head)
            department_head = form.save(commit=False)
            department_head.department = department  # Associate with the department
            department_head.save()
            messages.success(request, 'Department head updated successfully.')
            return redirect('admin_dashboard')  # Redirect to the admin dashboard
        else:
            print("Form errors:", form.errors)  # Debugging: Print form errors
    else:
        # Pre-fill the form with the current department head (if it exists)
        form = DepartmentHeadUpdateForm(instance=department_head)
    
    return render(request, 'departement_head/department_head_update.html', {'form': form, 'department': department})
# Student CRUD
class StudentListView(CRUDMixin, ListView):
    model = Student
    template_name = 'student/list.html'
    context_object_name = 'students'

class StudentCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    success_url = reverse_lazy('student_list')

class StudentUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    success_url = reverse_lazy('student_list')

class StudentDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Student
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('student_list')

# Advisor CRUD
def is_department_head(user):
    return user.is_authenticated and hasattr(user, 'is_department_head') and user.is_department_head
@login_required
@user_passes_test(is_department_head)
def advisor_management(request):
    department = request.user.departmenthead.department
    advisors = Advisor.objects.filter(department=department)
    return render(request, 'advisors/advisor_management.html', {
        'advisors': advisors,
        'departments': Department.objects.all()
    })
@login_required
def advisor_register(request):
    user = request.user

    # Determine base template based on role
    if user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(user, "is_department_head", False):
        base_template = "departement_head/base.html"
    else:
        return redirect('unauthorized_access')

    # Superadmin case
    if user.is_superuser:
        if request.method == 'POST':
            form = SuperadminAdvisorForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'Advisor registered successfully!')
                return redirect('admin_dashboard')  # Or any appropriate view
        else:
            form = SuperadminAdvisorForm()

    # Department Head case
    elif hasattr(user, 'departmenthead'):
        department = user.departmenthead.department
        if request.method == 'POST':
            form = DepartmentHeadAdvisorForm(request.POST, request.FILES, department=department)
            if form.is_valid():
                form.save()
                messages.success(request, 'Advisor registered successfully!')
                return redirect('advisor_management')  # Or any appropriate view
        else:
            form = DepartmentHeadAdvisorForm(department=department)

    return render(request, 'advisors/advisor_register.html', {
        'form': form,
        'base_template': base_template,
        'is_superuser': user.is_superuser
    })

@login_required
@user_passes_test(is_department_head)
def view_advisor_details(request, advisor_user_id):
    advisor = get_object_or_404(Advisor, user_id=advisor_user_id)
    chat_messages = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=advisor.user) |
        Q(sender=advisor.user, receiver=request.user)
    ).order_by('timestamp')
    
    return render(request, 'advisors/view_advisor_details.html', {
        'advisor': advisor,
        'chat_messages': chat_messages
    })

@login_required
def update_advisor(request, advisor_user_id):
    advisor = get_object_or_404(Advisor, user_id=advisor_user_id)
    if request.method == 'POST':
        form = AdvisorForm(request.POST, request.FILES, instance=advisor)
        if form.is_valid():
            form.save()
            return redirect('advisor_management')
    else:
        form = AdvisorForm(instance=advisor)
    return render(request, 'advisors/update_advisor.html', {'form': form})


@login_required
@user_passes_test(is_department_head)
def send_message(request, advisor_user_id):
    advisor = get_object_or_404(Advisor, user_id=advisor_user_id)
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=advisor.user,
                content=message
            )
    return redirect('view_advisor_details', advisor_user_id=advisor_user_id)
@login_required
@user_passes_test(is_department_head)
def delete_advisor(request, advisor_id):
    advisor = get_object_or_404(Advisor, id=advisor_id)
    if request.method == 'POST':
        advisor.user.delete()
        messages.success(request, 'Advisor deleted successfully')
    return redirect('advisor_management')
class AdvisorListView(CRUDMixin, ListView):
    model = Advisor
    template_name = 'advisor/list.html'
    context_object_name = 'advisors'

class AdvisorCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Advisor
    form_class = AdvisorForm
    success_url = reverse_lazy('advisor_list')

class AdvisorUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = Advisor
    form_class = AdvisorForm
    success_url = reverse_lazy('advisor_list')

class AdvisorDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Advisor
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('advisor_list')

# Application CRUD
class ApplicationListView(CRUDMixin, ListView):
    model = Application
    template_name = 'application/list.html'
    context_object_name = 'applications'

class ApplicationCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Application
    form_class = ApplicationForm
    success_url = reverse_lazy('application_list')

class ApplicationUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = Application
    form_class = ApplicationForm
    success_url = reverse_lazy('application_list')

class ApplicationDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Application
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('application_list')
# Role CRUD
class RoleListView(CRUDMixin, ListView):
    model = Role
    template_name = 'role/list.html'
    context_object_name = 'roles'

class RoleCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Role
    form_class = RoleForm
    success_url = reverse_lazy('role_list')

class RoleUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = Role
    form_class = RoleForm
    success_url = reverse_lazy('role_list')

class RoleDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Role
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('role_list')

# Internship CRUD
class InternshipListView(CRUDMixin, ListView):
    model = Internship
    template_name = 'internship/list.html'
    context_object_name = 'internships'

class InternshipCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Internship
    form_class = InternshipForm
    success_url = reverse_lazy('internship_list')

class InternshipUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = Internship
    form_class = InternshipForm
    success_url = reverse_lazy('internship_list')

class InternshipDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Internship
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('internship_list')

# Task CRUD
class TaskListView(CRUDMixin, ListView):
    model = Task
    template_name = 'task/list.html'
    context_object_name = 'tasks'

class TaskCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy('task_list')

class TaskUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy('task_list')

class TaskDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Task
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('task_list')
# CompanyAdmin CRUD
class CompanyAdminListView(CRUDMixin, ListView):
    model = CompanyAdmin
    template_name = 'company_admin/list.html'
    context_object_name = 'company_admins'

class CompanyAdminCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = CompanyAdmin
    form_class = CompanyAdminForm
    success_url = reverse_lazy('company_admin_list')

class CompanyAdminUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model = CompanyAdmin
    form_class = CompanyAdminForm
    success_url = reverse_lazy('company_admin_list')

class CompanyAdminDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = CompanyAdmin
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('company_admin_list')
#   CRUD FOR Notification

class NotificationListView(CRUDMixin, ListView):
    model = Notification
    template_name = 'notification/list.html'
    context_object_name = 'notification'

class NotificationCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = Notification
    form_class = NotificationForm
    success_url = reverse_lazy('notificationForm_list')

class NotificationUpdateView(CRUDMixin, AdminRequiredMixin, UpdateView):
    model =Notification
    form_class = NotificationForm
    success_url = reverse_lazy('notification_list')

class NotificationDeleteView(CRUDMixin, AdminRequiredMixin, DeleteView):
    model = Notification
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('notification_list')
# Example for Evaluation
class EvaluationListView(CRUDMixin, ListView):
    model = MonthlyEvaluation
    template_name = 'evaluation/list.html'
    context_object_name = 'evaluations'

class EvaluationCreateView(CRUDMixin, AdminRequiredMixin, CreateView):
    model = MonthlyEvaluation
    form_class = MonthlyEvaluationForm
    success_url = reverse_lazy('evaluation_list')

# Create similar classes for all other models...
@login_required
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')   # Redirect to Django admin dashboard
    if hasattr(request.user, 'is_company_admin') and request.user.is_company_admin:
        return redirect('company_admin_dashboard')
    elif hasattr(request.user, 'is_student') and request.user.is_student:
        return redirect('student_dashboard')
    elif hasattr(request.user, 'is_department_head') and request.user.is_department_head:
        return redirect('department_head_dashboard')
    elif hasattr(request.user, 'is_supervisor') and request.user.is_supervisor:
        return redirect('supervisor_dashboard')
    elif hasattr(request.user, 'is_advisor') and request.user.is_advisor:
        return redirect('advisor_dashboard')

    return redirect('home')


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Incorrect username or password")
    
    return redirect('home')  # Redirect back to home with error mess
def is_admin(user):
    return user.is_superuser
# Company Admin Registration View
def company_admin_register(request):
    if user.is_superuser:
        base_template = "admin/admin_base.html"

    else:
        base_template = "base.html"
    if request.method == "POST":
        form = CompanyAdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Company Admin registered successfully!')
            return redirect('company_admin_dashboard')
    else:
        form = CompanyAdminRegistrationForm()
    return render(request, 'Company_Admin/company_admin_register.html', {'form': form})

# Company Admin Dashboard
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def company_admin_dashboard(request):
    company = request.user.companyadmin.company  # Get the admin's company
    
    stats = {
        'total_applications': Application.objects.filter(internship__company=company).count(),
        'open_internships': Internship.objects.filter(company=company).count(),
        'pending_applications': Application.objects.filter(internship__company=company, status='Pending').count(),
    }
    
    return render(request, 'Company_Admin/company_admin_dashboard.html', {'stats': stats, 'company': company})

# Manage Applications (Approve/Reject)
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def manage_applications(request):
    company = request.user.companyadmin.company
    applications = Application.objects.filter(company=company).order_by('-date_applied')
    return render(request, 'company_admin/applications.html', {'applications': applications})

# Assign Supervisor to Application
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def assign_supervisor_to_students(request):
    # Get the company of the logged-in company admin
    company_admin = request.user.companyadmin
    company = company_admin.company

    # Fetch students with approved applications for this company
    students = Student.objects.filter(
        application__internship__company=company,
        application__status='Approved'
    ).distinct()

    # Fetch supervisors for the company
    supervisors = Supervisor.objects.filter(company=company)

    # Initialize the form with the company
    form = AssignSupervisorForm(company=company)

    if request.method == 'POST':
        # Bind the form to the POST data
        form = AssignSupervisorForm(request.POST, company=company)
        if form.is_valid():
            # Get the selected student and supervisor
            student = form.cleaned_data['student']
            supervisor = form.cleaned_data['supervisor']

            # Assign the supervisor to the student
            student.assigned_supervisor = supervisor
            student.save()

            # Show a success message
            messages.success(request, f"Supervisor {supervisor.user.get_full_name()} assigned to {student.user.get_full_name()}.")
            return redirect('company_admin_dashboard')  # Redirect to the dashboard
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'company_admin/assign_supervisor.html', {
        'form': form,
        'students': students,  # ✅ Add students to the template context
        'supervisors': supervisors,  # ✅ Add supervisors to the template context
    })

@login_required
def assigned_students(request):
    # Ensure the user is a supervisor
    if not request.user.is_supervisor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('supervisor_dashboard')

    # Get the supervisor
    supervisor = get_object_or_404(Supervisor, user=request.user)

    # Get students assigned to this supervisor
    students = Student.objects.filter(assigned_supervisor=supervisor)

    # Debug: Print the students queryset
    print("Students assigned to supervisor:", students)

    return render(request, 'supervisor/assigned_students.html', {
        'students': students,
    })

# Toggle Application Status (Open/Close)
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def toggle_applications(request):
    company = request.user.companyadmin.company
    if request.method == "POST":
        company.is_accepting_applications = not company.is_accepting_applications
        company.save()
    return redirect('company_admin_dashboard')

import openai

def suggest_fields(form_type, description):
    prompt = f"Suggest fields for a {form_type} form with the followiCDng description: {description}."
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=100
    )
    return response.choices[0].text.strip().split(',')
def internship_activity(request):
    # Fetch all internships
    internships = Internship.objects.all()

    # Fetch tasks and evaluations for each internship
    internship_data = []
    for internship in internships:
        tasks = Task.objects.filter(internship=internship)
        evaluations = Evaluation.objects.filter(internship=internship)
        internship_data.append({
            'internship': internship,
            'tasks': tasks,
            'evaluations': evaluations,
        })

    return render(request, 'departement_head/internship_activity.html', {
        'internship_data': internship_data,
    })


def form_list(request):
    forms = FormTemplate.objects.all()
    return render(request, 'departement_head/form_list.html', {'forms': forms})
def generate_evaluation_form(request):
    if request.method == 'POST':
        form = MonthlyPerformanceEvaluationForm(request.POST)
        if form.is_valid():
            # Generate the PDF
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer)

            # Add content to the PDF
            pdf.drawString(100, 800, "ADDIS ABABA SCIENCE AND TECHNOLOGY UNIVERSITY")
            pdf.drawString(100, 780, "INTERNSHIP INDUSTRY SUPERVISOR MONTHLY PERFORMANCE EVALUATION FORMAT")
            pdf.drawString(100, 760, f"Month: {form.cleaned_data['month']}")
            pdf.drawString(100, 740, f"Company Name: {form.cleaned_data['company_name']}")
            pdf.drawString(100, 720, f"Supervisor's Name: {form.cleaned_data['supervisor_name']}")
            pdf.drawString(100, 700, f"Supervisor's Phone No.: {form.cleaned_data['supervisor_phone']}")
            pdf.drawString(100, 680, f"Student's Full Name: {form.cleaned_data['student_name']}")
            pdf.drawString(100, 660, f"Student's ID No.: {form.cleaned_data['student_id']}")
            pdf.drawString(100, 640, f"Student's Department: {form.cleaned_data['student_department']}")

            # General Performance
            pdf.drawString(100, 620, "General Performance (25%)")
            pdf.drawString(120, 600, f"Punctuality (5%): {form.cleaned_data['punctuality']}")
            pdf.drawString(120, 580, f"Reliability (5%): {form.cleaned_data['reliability']}")
            pdf.drawString(120, 560, f"Independence In Work (5%): {form.cleaned_data['independence']}")
            pdf.drawString(120, 540, f"Communication Skills (5%): {form.cleaned_data['communication']}")
            pdf.drawString(120, 520, f"Professionalism (5%): {form.cleaned_data['professionalism']}")

            # Personal Skill
            pdf.drawString(100, 500, "Personal Skill (25%)")
            pdf.drawString(120, 480, f"Speed of Work (5%): {form.cleaned_data['speed_of_work']}")
            pdf.drawString(120, 460, f"Accuracy (5%): {form.cleaned_data['accuracy']}")
            pdf.drawString(120, 440, f"Engagement (5%): {form.cleaned_data['engagement']}")
            pdf.drawString(120, 420, f"Do you need him for your work (5%): {form.cleaned_data['need_for_work']}")
            pdf.drawString(120, 400, f"Cooperation with colleagues (5%): {form.cleaned_data['cooperation']}")

            # Professional Skills
            pdf.drawString(100, 380, "Professional Skills (50%)")
            pdf.drawString(120, 360, f"Technical Skills (5%): {form.cleaned_data['technical_skills']}")
            pdf.drawString(120, 340, f"Organizational Skills (5%): {form.cleaned_data['organizational_skills']}")
            pdf.drawString(120, 320, f"Support of the project tasks (5%): {form.cleaned_data['project_support']}")
            pdf.drawString(120, 300, f"Responsibility in the task fulfillment (15%): {form.cleaned_data['responsibility']}")
            pdf.drawString(120, 280, f"Quality as a team member (20%): {form.cleaned_data['team_quality']}")

            # Additional Comments
            pdf.drawString(100, 260, "Additional Comments:")
            pdf.drawString(120, 240, form.cleaned_data['additional_comments'])

            # Save the PDF
            pdf.save()
            buffer.seek(0)
            return HttpResponse(buffer, content_type='application/pdf')
    else:
        form = MonthlyPerformanceEvaluationForm()

    return render(request, 'departement_head/generate_form.html', {'form': form})

def generate_logbook_form(request):
    if request.method == 'POST':
        form = InternshipLogbookForm(request.POST)
        if form.is_valid():
            # Generate the PDF
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer)

            # Add content to the PDF
            pdf.drawString(100, 800, "ADDIS ABABA SCIENCE AND TECHNOLOGY UNIVERSITY")
            pdf.drawString(100, 780, "INTERNSHIP STUDENT LOGBOOK FORM")
            pdf.drawString(100, 760, f"Student’s Name: {form.cleaned_data['student_name']}")
            pdf.drawString(100, 740, f"Name of Company: {form.cleaned_data['company_name']}")
            pdf.drawString(100, 720, f"Name of Supervisor: {form.cleaned_data['supervisor_name']}")
            pdf.drawString(100, 700, f"Safety Guidelines: {form.cleaned_data['safety_guidelines']}")

            # Logbook Table
            pdf.drawString(100, 680, "| Week | Day | Date | Work Performed | Supervisor’s Signature and Comment |")
            pdf.drawString(100, 660, "|---|---|---|---|---|")

            # Week 1, Day 1
            pdf.drawString(100, 640, f"| 1 | 1 | {form.cleaned_data['week_1_day_1_date']} | {form.cleaned_data['week_1_day_1_work']} | {form.cleaned_data['week_1_day_1_comment']} |")

            # Week 1, Day 2
            pdf.drawString(100, 620, f"| 1 | 2 | {form.cleaned_data['week_1_day_2_date']} | {form.cleaned_data['week_1_day_2_work']} | {form.cleaned_data['week_1_day_2_comment']} |")

            # Add more rows for other days and weeks as needed...

            # Save the PDF
            pdf.save()
            buffer.seek(0)
            return HttpResponse(buffer, content_type='application/pdf')
    else:
        form = InternshipLogbookForm()

    return render(request, 'departement_head/generate_logbook_form.html', {'form': form})

def form_generated(request):
    return render(request, 'departement_head/form_generated.html')
def is_department_head(user):
    return user.is_authenticated and hasattr(user, 'is_department_head') and user.is_department_head

def is_admin(user):
    return user.is_authenticated and user.is_superuser
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # System statistics
    active_section = request.GET.get('section', 'admin_dashboard')
    total_departments = Department.objects.count()
    total_students = Student.objects.count()
    total_advisors = Advisor.objects.count()
    total_supervisors = Supervisor.objects.count()
    total_companies = Company.objects.count()
    total_internships = Internship.objects.count()
    total_notifications = Notification.objects.count()
    total_users = User.objects.count()
    recent_users = User.objects.order_by('username')[:1000]
    active_internships = Internship.objects.filter(is_open=True).count()

    # Get filter parameter from URL
    user_filter = request.GET.get('filter', None)

    # Initialize all role-specific counts
    student_count = User.objects.filter(is_student=True).count()
    advisor_count = User.objects.filter(is_advisor=True).count()
    supervisor_count = User.objects.filter(is_supervisor=True).count()
    company_admin_count = User.objects.filter(is_company_admin=True).count()
    department_head_count = User.objects.filter(is_department_head=True).count()

    # Additional statistics
    students_with_internships = Student.objects.filter(internship__isnull=False).distinct().count()
    
    # Calculate average students per advisor
    avg_students_per_advisor = Advisor.objects.annotate(
        student_count=Count('student')
    ).aggregate(avg=Avg('student_count'))['avg'] or 0
    
    # Calculate internships being supervised (through Student model)
    supervising_internships = Student.objects.filter(
        assigned_supervisor__isnull=False,
        internship__isnull=False
    ).count()
    
    departments_managed = DepartmentHead.objects.count()
    
    # Calculate companies managed by company admins
    managing_companies = Company.objects.filter(companyadmin__isnull=False).count()

    # Filter users based on role flags
    if user_filter == 'students':
        recent_users = User.objects.filter(is_student=True).order_by('username')[:10000]
    elif user_filter == 'advisors':
        recent_users = User.objects.filter(is_advisor=True).order_by('username')[:100]
    elif user_filter == 'department_heads':
        recent_users = User.objects.filter(is_department_head=True).order_by('username')[:100]
    elif user_filter == 'company_admins':
        recent_users = User.objects.filter(is_company_admin=True).order_by('username')[:100]
    elif user_filter == 'supervisors':
        recent_users = User.objects.filter(is_supervisor=True).order_by('username')[:100]

    # Department management data
    departments = Department.objects.annotate(
        student_count=Count('student'),
        head_name=Coalesce(
            Subquery(
                DepartmentHead.objects.filter(department=OuterRef('pk')).values('user__username')[:1]
            ),
            Value('Not assigned')
        )
    ).order_by('name')

    # Department statistics
    departments_with_heads_count = Department.objects.annotate(
        has_head=Exists(DepartmentHead.objects.filter(department=OuterRef('pk')))
    ).filter(has_head=True).count()
    
    avg_students_per_dept = Department.objects.annotate(
        student_count=Count('student')
    ).aggregate(avg=Avg('student_count'))['avg'] or 0

    # Company management data
    companies = Company.objects.annotate(
        internship_count=Count('internship')
    ).order_by('name')

    context = {
        'total_departments': total_departments,
        'total_users': total_users,
        'total_students': total_students,
        'total_advisors': total_advisors,
        'total_supervisors': total_supervisors,
        'total_companies': total_companies,
        'total_internships': total_internships,
        'total_notifications': total_notifications,
        'recent_users': recent_users,
        'active_internships': active_internships,
        'departments': departments,
        'companies': companies,
        'active_section': active_section,
        'current_filter': user_filter,
        'total_'
        
        # Role-specific counts
        'student_count': student_count,
        'advisor_count': advisor_count,
        'supervisor_count': supervisor_count,
        'company_admin_count': company_admin_count,
        'department_head_count': department_head_count,
        
        # Additional statistics
        'students_with_internships': students_with_internships,
        'avg_students_per_advisor': avg_students_per_advisor,
        'supervising_internships': supervising_internships,
        'departments_managed': departments_managed,
        'managing_companies': managing_companies,
        'departments_with_heads_count': departments_with_heads_count,
        'avg_students_per_dept': avg_students_per_dept,
    }

    return render(request, 'admin/admin_dashboard.html', context)

def company_register(request):
    if request.method == "POST":
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company registered successfully!')
            return redirect('company_admin_dashboard')  # Redirect to the dashboard or another page
    else:
        form = CompanyRegistrationForm()
    return render(request, 'company/register_company.html', {'form': form})

@login_required
def company_management(request):
    companies = Company.objects.all()
    company_names = [company.name for company in companies]
    internships_offered = [Internship.objects.filter(company=company).count() for company in companies]
    applications_received = [
    Application.objects.filter(internship__company=company).count() for company in companies
]

    company_feedbacks = CompanyFeedback.objects.all()

    context = {
        'companies': companies,
        'company_names': company_names,
        'internships_offered': internships_offered,
        'applications_received': applications_received,
        'company_feedbacks': company_feedbacks,
    }
    return render(request, 'company/company_management.html', context)

@login_required
def add_company(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company added successfully!')
            return redirect('admin_dashboard')
    else:
        form = CompanyForm()
    return render(request, 'company/register_company.html', {'form': form})

@login_required
def edit_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company updated successfully!')
            return redirect('company_management')
        else:
            print("Form Errors:", form.errors)  # Debugging: Print errors to console/log
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'company/edit_company.html', {'form': form, 'company': company})



@login_required
def delete_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    company.delete()
    messages.success(request, 'Company deleted successfully!')
    return redirect('company_management')
def is_department_head(user):
    return user.is_authenticated and hasattr(user, 'is_department_head') and user.is_department_head
from django.db.models import Count, Q
@login_required
@user_passes_test(is_department_head)
def view_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Annotate internships with the count of approved applications
    internships = Internship.objects.filter(company=company).annotate(
        approved_applications=Count('application', filter=Q(application__status='Approved'))
    )
    
    feedbacks = CompanyFeedback.objects.filter(company=company)

    context = {
        'company': company,
        'internships': internships,
        'feedbacks': feedbacks,
    }
    return render(request, 'company/view_company.html', context)

@login_required
def submit_company_feedback(request):
    if request.method == 'POST':
        form = CompanyFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.submitted_by = request.user
            feedback.save()
            messages.success(request, 'Feedback submitted successfully!')
            return redirect('company_management')
    else:
        form = CompanyFeedbackForm()
    return render(request, 'departement_head/submit_company_feedback.html', {'form': form})

@login_required
def export_company_data(request):
    # Example: Export company data as CSV
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="company_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Industry', 'Location', 'Contact Email', 'Contact Phone', 'Description'])

    companies = Company.objects.all()
    for company in companies:
        writer.writerow([company.name, company.industry, company.location, company.contact_email, company.contact_phone, company.description])

    return response
# Registration Views
class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer

class StudentRegistrationView(generics.CreateAPIView):
    serializer_class = StudentSerializer

class AdvisorRegistrationView(generics.CreateAPIView):
    serializer_class = AdvisorSerializer

class DepartmentHeadRegistrationView(generics.CreateAPIView):
    serializer_class = DepartmentHeadSerializer

class SupervisorRegistrationView(generics.CreateAPIView):
    serializer_class = SupervisorSerializer

# Browse student list
def student_list(request):
    students = Internship.objects.filter(start_date__year__lt=2024).select_related('student')
    return render(request, 'students/student_list.html', {'students': students})


@login_required
@user_passes_test(lambda u: u.is_department_head)
def student_management(request):
    # Get the department of the logged-in department head
    department_head = DepartmentHead.objects.get(user=request.user)
    department = department_head.department

    # Filter students by the department
    students = Student.objects.filter(department=department)

    # Identify students with approved applications
    students_with_approved_applications = []
    for student in students:
        if student.application_set.filter(status='Approved').exists():
            students_with_approved_applications.append(student)

    # Pass the students and the list of students with approved applications to the template
    return render(request, 'students/student_management.html', {
        'students': students,
        'students_with_approved_applications': students_with_approved_applications
    })

@login_required
@user_passes_test(lambda u: u.is_supervisor)
def monthly_evaluation(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = MonthlyEvaluationForm(request.POST)
        if form.is_valid():
            # Save to database
            evaluation = form.save(commit=False)
            evaluation.student = student
            evaluation.supervisor = request.user.supervisor
            evaluation.save()
            
            # Generate PDF (your existing code)
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer)
            
            # University Header
            pdf.drawString(100, 800, "ADDIS ABABA SCIENCE AND TECHNOLOGY UNIVERSITY")
            pdf.drawString(100, 780, "INTERNSHIP INDUSTRY SUPERVISOR MONTHLY PERFORMANCE EVALUATION FORMAT")
            
            # Student/Supervisor Info
            pdf.drawString(100, 760, f"Month: {form.cleaned_data['month']}")
            pdf.drawString(100, 740, f"Company Name: {student.internship.company.name}")
            pdf.drawString(100, 720, f"Supervisor's Name: {request.user.get_full_name()}")
            pdf.drawString(100, 700, f"Supervisor's Phone No.: {request.user.phone}")
            pdf.drawString(100, 680, f"Student's Full Name: {student.user.get_full_name()}")
            pdf.drawString(100, 660, f"Student's ID No.: {student.user.username}")
            pdf.drawString(100, 640, f"Student's Department: {student.department.name}")
            
            # Evaluation Sections (same as your template)
            pdf.drawString(100, 620, "General Performance (25%)")
            pdf.drawString(120, 600, f"Punctuality (5%): {form.cleaned_data['punctuality']}")
            # ... [Include all other sections from your original PDF code] ...
            
            pdf.save()
            buffer.seek(0)
            
            # Return PDF for download
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="monthly_evaluation_{student.user.username}.pdf"'
            return response
    else:
        # Auto-fill form with student/supervisor data
        initial_data = {
            'month': timezone.now().strftime("%B %Y"),
            'company_name': student.internship.company.name,
            'supervisor_name': request.user.get_full_name(),
            'supervisor_phone': request.user.phone,
            'student_name': student.user.get_full_name(),
            'student_id': student.user.username,
            'student_department': student.department.name
        }
        form = MonthlyEvaluationForm(initial=initial_data)
    
    return render(request, 'supervisors/monthly_evaluation.html', {
        'form': form,
        'student': student,
        'reports': DailyWorkReportForm.objects.filter(student=student).order_by('-work_date')[:28]  # Last 4 weeks
    })

@login_required
def submit_feedback(request, user_id):
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        student = get_object_or_404(Student, user_id=user_id)

        # Save feedback
        Feedback.objects.create(
            student=student,
            feedback=feedback_text,
            submitted_by=request.user
        )

        messages.success(request, 'Feedback submitted successfully!')
        return redirect('view_student_progress', user_id=user_id)


@login_required
def export_student_progress(request, user_id):
    # Fetch the student
    student = get_object_or_404(Student, user_id=user_id)

    # Fetch the student's internships through their applications
    internships = Internship.objects.filter(application__student=student)

    # Create a PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 800, f"Progress Report for {student.user.get_full_name()}")

    y = 780
    for internship in internships:
        pdf.drawString(100, y, f"Internship at {internship.company.name}")
        y -= 20
        tasks = Task.objects.filter(internship=internship)
        for task in tasks:
            pdf.drawString(120, y, f"Task: {task.description} - Status: {task.status}")
            y -= 15
        y -= 10

    pdf.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
# views.py
@login_required
@user_passes_test(lambda u: u.is_department_head)
def view_monthly_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(MonthlyEvaluation, id=evaluation_id)
    
    # Verify department head has access
    if evaluation.student.department != request.user.departmenthead.department:
        raise PermissionDenied()

    # Generate PDF (using your existing code)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    
    # Header
    pdf.drawString(100, 800, "ADDIS ABABA SCIENCE AND TECHNOLOGY UNIVERSITY")
    pdf.drawString(100, 780, "MONTHLY PERFORMANCE EVALUATION")
    
    # Student Info
    pdf.drawString(100, 760, f"Month: {evaluation.month}")
    pdf.drawString(100, 740, f"Student: {evaluation.student.user.get_full_name()}")
    
    # Evaluation Data
    pdf.drawString(100, 720, "General Performance (25%)")
    pdf.drawString(120, 700, f"Punctuality: {evaluation.punctuality}/5")
    # ... [include all evaluation fields] ...
    
    pdf.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
# views.py
def view_student_progress(request, user_id):
    student = get_object_or_404(Student, user_id=user_id)
    department_head = request.user.departmenthead
    
    # Basic task counts
    completed_tasks = Task.objects.filter(student=student, status='completed').count()
    pending_tasks = Task.objects.filter(student=student, status='pending').count()
    
    # Evaluation data
    evaluations = MonthlyEvaluation.objects.filter(student=student).order_by('created_at')
    evaluations_count = evaluations.count()
    
    # Calculate averages if evaluations exist
    if evaluations_count > 0:
        average_score = evaluations.aggregate(Avg('total_score'))['total_score__avg']
        
        # Calculate category averages
        avg_punctuality = evaluations.aggregate(Avg('punctuality'))['punctuality__avg']
        avg_reliability = evaluations.aggregate(Avg('reliability'))['reliability__avg']
        avg_communication = evaluations.aggregate(Avg('communication'))['communication__avg']
        avg_technical_skills = evaluations.aggregate(Avg('technical_skills'))['technical_skills__avg']
        avg_responsibility = evaluations.aggregate(Avg('responsibility'))['responsibility__avg'] / 3  # Normalize to 5-point scale
        avg_teamwork = evaluations.aggregate(Avg('team_quality'))['team_quality__avg'] / 4  # Normalize to 5-point scale
        
        # Prepare chart data
        evaluation_dates = [e.month for e in evaluations]
        evaluation_scores = [e.total_score for e in evaluations]
    else:
        average_score = None
        avg_punctuality = avg_reliability = avg_communication = 0
        avg_technical_skills = avg_responsibility = avg_teamwork = 0
        evaluation_dates = []
        evaluation_scores = []

    context = {
        'student': student,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'monthly_evaluations': evaluations,
        'evaluations_count': evaluations_count,
        'average_score': average_score,
        'evaluation_dates': evaluation_dates,
        'evaluation_scores': evaluation_scores,
        'avg_punctuality': avg_punctuality or 0,
        'avg_reliability': avg_reliability or 0,
        'avg_communication': avg_communication or 0,
        'avg_technical_skills': avg_technical_skills or 0,
        'avg_responsibility': avg_responsibility or 0,
        'avg_teamwork': avg_teamwork or 0,
    }
    
    return render(request, 'students/view_student_progress.html', context)

@login_required
def add_student(request):
    user = request.user

    # Determine base template based on user role
    if user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(user, "is_department_head", False):
        base_template = "departement_head/base.html"
    elif getattr(user, "is_advisor", False):
        base_template = "advisors/base.html"
    elif getattr(user, "is_supervisor", False):
        base_template = "supervisor/base.html"
    elif getattr(user, "is_student", False):
        base_template = "students/base.html"
    elif getattr(user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        base_template = "base.html"  # Default fallback

    # Superadmin case
    if user.is_superuser:
        if request.method == 'POST':
            form = SuperadminStudentForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'Student registered successfully!')
                return redirect('admin_dashboard')
        else:
            form = SuperadminStudentForm()

    # Department Head case
    elif getattr(user, "is_department_head", False):
        department = user.departmenthead.department
        if request.method == 'POST':
            form = DepartmentHeadStudentForm(
                request.POST, request.FILES, department=department
            )
            if form.is_valid():
                form.save()
                messages.success(request, 'Student registered successfully!')
                return redirect('student_management')
        else:
            form = DepartmentHeadStudentForm(department=department)

    # Unauthorized access
    else:
        return redirect('unauthorized_access')

    return render(request, 'students/add_student.html', {
        'form': form,
        'is_superuser': user.is_superuser,
        'base_template': base_template
    })
@login_required
def view_student(request, student_id):
    student = get_object_or_404(Student, user_id=student_id)
    return render(request, 'students/view_student.html', {'student': student})
@login_required
def student_activity(request, student_id):
    # Ensure the user is a supervisor
    if not request.user.is_supervisor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('supervisor_dashboard')

    # Get the student
    student = get_object_or_404(Student, user_id=student_id)

    # Debug: Print the student's details
    print(f"Student: {student.user.get_full_name()} (ID: {student.user.id})")

    # Get tasks assigned to the student
    tasks = Task.objects.filter(student=student).order_by('created_at')

    # Debug: Print the tasks queryset
    print(f"Tasks for {student.user.get_full_name()}: {tasks}")

    return render(request, 'supervisor/student_activity.html', {
        'student': student,
        'tasks': tasks,
    })
@login_required
@user_passes_test(lambda u: u.is_department_head)
def edit_student(request, student_user_id):
    student = get_object_or_404(Student, user_id=student_user_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('student_management')
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/edit_student.html', {'form': form, 'student': student})

@login_required
def delete_student(request, student_user_id):
    student = get_object_or_404(Student, user_id=student_user_id)
    student.delete()
    return redirect('student_management')
# views.py
@login_required
def student_dashboard(request):
    student = request.user.student  # Get the student object

    # Fetch the approved application (if any)
    approved_application = Application.objects.filter(
        student=student, 
        status='Approved'
    ).first()

    # Check if the student has permission to create chat groups
   

    return render(request, 'students/student_dashboard.html', {
        'approved_application': approved_application,
        'student': student,  # Pass the student object to the template
        'user': request.user,  # Ensure user is passed
        
    })

@login_required
def department_head_dashboard(request):
    return render(request, 'departement_head/department_head_dashboard.html', {'user': request.user})

@login_required
def industry_supervisor_dashboard(request):
    return render(request, 'supervisor/industry_supervisor_dashboard.html', {'user': request.user})
from django.contrib.auth import get_user_model
User = get_user_model()
def advisor_dashboard(request):
    # Ensure the logged-in user is an advisor
    advisor = Advisor.objects.filter(user=request.user).first()

    if not advisor:
        print("DEBUG: No Advisor found for user:", request.user)  # Debugging output

    context = {"advisor": advisor}
    return render(request, "advisors/advisor_dashboard.html", context)

# Registration Views for All Actors
@login_required
@user_passes_test(lambda u: u.is_department_head)
def student_register(request):
    department_head = DepartmentHead.objects.get(user=request.user)
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES, department_head=department_head)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student registered successfully!')
            return redirect('student_management')
    else:
        form = StudentRegistrationForm(department_head=department_head)
    return render(request, 'students/register_student.html', {'form': form})

def register_department(request):
    if request.method == 'POST':
        form = DepartmentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department registered successfully!")
            return redirect('')
    else:
        form = DepartmentRegistrationForm()

    return render(request, 'department/register_department.html', {'form': form})

def department_head_register(request):
    if request.method == "POST":
        form = DepartmentHeadRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Department Head registered successfully!')
                return redirect('department_head_dashboard')
            except Exception as e:
                messages.error(request, f'Error saving data: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = DepartmentHeadRegistrationForm()
    
    return render(request, 'departement_head/department_head_register.html', {
        'form': form,
        'departments': Department.objects.all()
    })
@login_required
def supervisor_register(request):
    user = request.user

    # Base template logic (optional for layout)
    if user.is_superuser:
        base_template = "admin/admin_base.html"
    elif getattr(user, "is_company_admin", False):
        base_template = "Company_Admin/base.html"
    else:
        return redirect('unauthorized_access')

    # Superadmin case
    if user.is_superuser:
        if request.method == 'POST':
            form = SuperadminSupervisorForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'Supervisor registered successfully!')
                return redirect('admin_dashboard')
        else:
            form = SuperadminSupervisorForm()

    # CompanyAdmin case
    elif hasattr(user, 'companyadmin'):
        company_admin = user.companyadmin
        if request.method == 'POST':
            form = CompanyAdminSupervisorForm(request.POST, request.FILES, company_admin=company_admin)
            if form.is_valid():
                form.save()
                messages.success(request, 'Supervisor registered successfully!')
                return redirect('supervisor_list')
        else:
            form = CompanyAdminSupervisorForm(company_admin=company_admin)

    return render(request, 'supervisor/supervisor_register.html', {
        'form': form,
        'base_template': base_template,
        'is_superuser': user.is_superuser
    })

@login_required
@user_passes_test(lambda u: u.is_company_admin)
def supervisor_list(request):
    # Get the company of the logged-in company admin
    company_admin = get_object_or_404(CompanyAdmin, user=request.user)
    company = company_admin.company

    # Get the supervisors belonging to the company
    supervisors = Supervisor.objects.filter(company=company)

    # Pass the data to the template
    return render(request, 'supervisor/supervisor_list.html', {
        'supervisors': supervisors,
        'company': company,
    })
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def view_supervisor_details(request, supervisor_id):
    # Get the supervisor
    supervisor = get_object_or_404(Supervisor, user_id=supervisor_id)
    
    # Pass the supervisor to the template
    return render(request, 'supervisor/view_supervisor_details.html', {
        'supervisor': supervisor,
    })
# views.py
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def update_supervisor(request, supervisor_id):
    company_admin = get_object_or_404(CompanyAdmin, user=request.user)
    supervisor = get_object_or_404(Supervisor, user_id=supervisor_id, company=company_admin.company)
    
    if request.method == 'POST':
        form = SupervisorForm(request.POST, instance=supervisor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supervisor updated successfully!')
            return redirect('supervisor_list')
    else:
        form = SupervisorForm(instance=supervisor)
    
    return render(request, 'supervisor/update_supervisor.html', {
        'form': form,
        'supervisor': supervisor,
    })
@login_required
@user_passes_test(lambda u: u.is_company_admin)
def delete_supervisor(request, supervisor_id):
    # Get the logged-in company admin
    company_admin = get_object_or_404(CompanyAdmin, user=request.user)
    
    # Get the supervisor (ensure they belong to the company admin's company)
    supervisor = get_object_or_404(Supervisor, user_id=supervisor_id, company=company_admin.company)
    
    # Delete the supervisor
    supervisor.user.delete()  # Delete the associated user
    messages.success(request, f"Supervisor {supervisor.user.get_full_name()} deleted successfully!")
    
    return redirect('supervisor_list')
@login_required
def internship_applications(request):
    return render(request, 'internship_applications.html')

@login_required
def progress_reports(request):
    return render(request, 'progress_reports.html')

@login_required
def feedback(request):
    return render(request, 'feedback.html')

@login_required
def request_support(request):
    return render(request, 'request_support.html')

@login_required
def final_report(request):
    return render(request, 'final_report.html')

@login_required
def manage_placements(request):
    return render(request, 'manage_placements.html')

@login_required
def student_progress(request):
    return render(request, 'student_progress.html')

@login_required
def generate_reports(request):
    return render(request, 'generate_reports.html')

@login_required
def set_policies(request):
    return render(request, 'set_policies.html')

@login_required
def manage_tasks(request):
    return render(request, 'manage_tasks.html')

@login_required
def monitor_performance(request):
    return render(request, 'monitor_performance.html')

@login_required
def provide_feedback(request):
    return render(request, 'provide_feedback.html')

@login_required
def communication(request):
    return render(request, 'communication.html')

@login_required
def review_applications(request):
    return render(request, 'review_applications.html')

@login_required
def reports(request):
    return render(request, 'reports.html')

@login_required
def give_feedback(request):
    return render(request, 'give_feedback.html')

@login_required
def performance_evaluation(request):
    return render(request, 'performance_evaluation.html')

# API ViewSets
class DepartmentHeadViewSet(viewsets.ModelViewSet):
    queryset = DepartmentHead.objects.all()
    serializer_class = DepartmentHeadSerializer

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

class AdvisorViewSet(viewsets.ModelViewSet):
    queryset = Advisor.objects.all()
    serializer_class = AdvisorSerializer

class SupervisorViewSet(viewsets.ModelViewSet):
    queryset = Supervisor.objects.all()
    serializer_class = SupervisorSerializer

class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

class InternshipViewSet(viewsets.ModelViewSet):
    queryset = Internship.objects.all()
    serializer_class = InternshipSerializer

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer

def notify_department_head(self, evaluation):
    """Notify the student's department head about the evaluation"""
    department_head = DepartmentHead.objects.filter(
        department=evaluation.student.department
    ).first()
    
    if department_head:
        message = (
            f"New monthly evaluation for {evaluation.student.user.get_full_name()} "
            f"({evaluation.month}) with score: {evaluation.total_score()}/100"
        )
        
        Notification.objects.create(
            user=department_head.user,
            message=message,
            link=f"/students/{evaluation.student.pk}/evaluations/"
        )
# views.py
@login_required
def view_student_evaluations(request, student_id):
    if not hasattr(request.user, 'departmenthead'):
        messages.error(request, "Only department heads can access this page")
        return redirect('dashboard')
    
    department_head = request.user.departmenthead
    student = get_object_or_404(Student, pk=student_id)
    
    # Verify student is in department head's department
    if student.department != department_head.department:
        messages.error(request, "This student is not in your department")
        return redirect('department_head_dashboard')
    
    evaluations = MonthlyEvaluation.objects.filter(
        student=student
    ).order_by('-created_at')
    
    context = {
        'student': student,
        'evaluations': evaluations,
    }
    return render(request, 'department_head/student_evaluations.html', context)

from datetime import timedelta
def weekly_tasks_view(request, student_id):
    # Fetch the student and their work schedule
    student = get_object_or_404(Student, id=student_id)
    work_schedule = WorkSchedule.objects.get(student=student)
    
    # Calculate the start date of the current week (example: Monday as the start of the week)
    today = timezone.now().date()
    week_start_date = today - timedelta(days=today.weekday())  # Monday as the start of the week
    
    # Fetch tasks for the current week
    tasks = Task.objects.filter(student=student, work_date__gte=week_start_date, work_date__lt=week_start_date + timedelta(days=7))
    
    # Determine the week number (example: week number since the start of the program)
    week_number = (today - work_schedule.start_date).days // 7 + 1
    
    context = {
        'student': student,
        'work_schedule': work_schedule,
        'tasks': tasks,
        'week_start_date': week_start_date,
        'week': week_number,
    }
    return render(request, 'supervisor/provide_weekly_feedback.html', context)
@user_passes_test(lambda u: u.is_student)
def view_tasks(request):
    student = get_object_or_404(Student, user=request.user)
    tasks = Task.objects.filter(student=student).order_by('-created_at')
    return render(request, 'students/view_tasks.html', {'tasks': tasks})
@login_required
def edit_task(request, task_id):
    task = Task.objects.get(id=task_id, student=request.user.student)
    
    if not task.can_edit_or_delete():
        messages.error(request, "You can only edit a task within 24 hours of submission.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = DailyTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated successfully!")
            return redirect('student_dashboard')
    else:
        form = DailyTaskForm(instance=task)

    return render(request, 'students/edit_task.html', {'form': form})

@login_required
def delete_task(request, task_id):
    task = Task.objects.get(id=task_id, student=request.user.student)
    
    if not task.can_edit_or_delete():
        messages.error(request, "You can only delete a task within 24 hours of submission.")
        return redirect('student_dashboard')

    task.delete()
    messages.success(request, "Task deleted successfully.")
    return redirect('student_dashboard')

# Student Views
def submit_task(request):
    student = request.user.student
    schedule = WorkSchedule.objects.get(student=student)
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            if timezone.now().date() in schedule.get_work_dates():
                task.student = student
                task.save()
                return redirect('student_dashboard')

def progress_report(request):
    student = request.user.student
    tasks = Task.objects.filter(student=student)
    return render(request, 'progress.html', {'tasks': tasks})

# Advisor Views
def advisor_feedback(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if task.supervisor_feedback:  # Can only comment after supervisor
        if request.method == 'POST':
            task.advisor_feedback = request.POST.get('feedback')
            task.save()
    return redirect('advisor_dashboard')
@login_required
@user_passes_test(lambda u: u.is_supervisor)
def assign_workdays(request):
    # Validate days parameter first
    days = request.POST.get('days')
    
    if not days:
        messages.error(request, "Missing required 'days' parameter")
        return redirect('assigned_students')

    try:
        days = int(days)
    except ValueError:
        messages.error(request, "Invalid value for workdays")
        return redirect('assigned_students')

    supervisor = request.user.supervisor
    
    # Update with validated value
    updated = WorkSchedule.objects.filter(
        supervisor=supervisor
    ).update(workdays_per_week=days)
    
    messages.success(request, f"Work schedule updated for {updated} students")
    return redirect('assigned_students')

# views.py

@login_required
@user_passes_test(lambda u: u.is_student)
def submit_daily_task(request):
    student = request.user.student
    today = timezone.now().date()

    try:
        work_schedule = WorkSchedule.objects.get(student=student, is_active=True)
    except WorkSchedule.DoesNotExist:
        messages.error(request, "No active work schedule assigned")
        return redirect('student_dashboard')

    try:
        existing_task = DailyWorkReport.objects.get(student=student, work_date=today)
        is_edit = True
    except DailyWorkReport.DoesNotExist:
        existing_task = None
        is_edit = False

    if request.method == 'POST':
        form = DailyTaskForm(request.POST, instance=existing_task)
        if form.is_valid():
            task = form.save(commit=False)
            task.student = student
            task.work_date = today
            task.supervisor = student.assigned_supervisor
            task.internship = student.internship
            task.week_number = work_schedule.current_week()  # This now uses the fixed method

            if 'save' in request.POST:
                task.status = 'draft'
                msg = "Draft saved successfully!"
            else:
                task.status = 'submitted'
                msg = "Task submitted successfully!"

            task.save()
            messages.success(request, msg)
            return redirect('view_submitted_tasks')
    else:
        form = DailyTaskForm(instance=existing_task)

    context = {
        'form': form,
        'today': today,
        'is_edit': is_edit,
        'work_schedule': work_schedule,
    }
    return render(request, 'students/submit_daily_task.html', context)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db.models import Avg
from .models import Student, WeeklyFeedback, MonthlyEvaluation
from .forms import MonthlyEvaluationForm

@login_required
@user_passes_test(lambda u: u.is_supervisor)
def submit_monthly_evaluation(request, student_id, month_number):
    student = get_object_or_404(Student, user_id=student_id)
    supervisor = request.user.supervisor

    if student.assigned_supervisor != supervisor:
        raise PermissionDenied("You are not assigned to this student")

    # Get all feedbacks (optional use only)
    all_feedbacks = WeeklyFeedback.objects.filter(student=student).order_by('id')
    start_index = (month_number - 1) * 4
    end_index = start_index + 4
    month_feedbacks = all_feedbacks[start_index:end_index]

    # Create or get evaluation
    evaluation, created = MonthlyEvaluation.objects.get_or_create(
        student=student,
        month_number=month_number,
        defaults={
            'supervisor': supervisor,
            'month': f"Month {month_number}"
        }
    )

    if request.method == 'POST':
        form = MonthlyEvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.supervisor = supervisor
            evaluation.total_score = evaluation.calculate_total_score()
            evaluation.save()
            messages.success(request, f"Evaluation for Month {month_number} submitted successfully!")
            return redirect('student_reported_tasks', student_id=student.user_id)
    else:
        # Optional: Pre-fill from averages if feedbacks exist
        if month_feedbacks.exists():
            avg_fields = ['punctuality', 'reliability', 'communication', 'engagement']
            avg_values = {
                field: month_feedbacks.aggregate(Avg(field))[f'{field}__avg'] or 0
                for field in avg_fields
            }
            initial_data = {k: round(v) for k, v in avg_values.items()}
        else:
            initial_data = {}
        form = MonthlyEvaluationForm(instance=evaluation, initial=initial_data)

    context = {
        'student': student,
        'form': form,
        'weekly_reports': month_feedbacks,  # Can be empty now
        'month_name': f"Month {month_number}",
        'month_number': month_number,
        'progress': evaluation.get_category_progress() if not created else None,
    }
    return render(request, 'Supervisor/submit_monthly_evaluation.html', context)

@login_required
def view_submitted_tasks(request):
    if not request.user.is_student:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('student_dashboard')

    student = request.user.student
    schedule = WorkSchedule.objects.filter(student=student, is_active=True).first()

    if not schedule:
        messages.warning(request, "No active work schedule found")
        return redirect('student_dashboard')

    # Get tasks ordered by date
    tasks = Task.objects.filter(student=student).select_related(
        'supervisor'
    ).order_by('work_date')
    
    # Group tasks using the same logic as student_progress_view
    grouped_tasks = []
    weekly_tasks = []
    week_number = 1
    workdays_per_week = schedule.workdays_per_week

    for i, task in enumerate(tasks):
        weekly_tasks.append(task)
        if len(weekly_tasks) == workdays_per_week:
            grouped_tasks.append({
                'week_number': week_number,
                'tasks': weekly_tasks,
                'week_start': weekly_tasks[0].work_date
            })
            weekly_tasks = []
            week_number += 1

    # Add remaining tasks as incomplete week
    if weekly_tasks:
        grouped_tasks.append({
            'week_number': week_number,
            'tasks': weekly_tasks,
            'week_start': weekly_tasks[0].work_date
        })

    return render(request, 'students/view_submitted_tasks.html', {
        'grouped_tasks': grouped_tasks,
        'workdays_per_week': workdays_per_week,
        'schedule': schedule
    })
@login_required
def supervisor_feedback_view(request):
    # Ensure the logged-in user is a supervisor
    if not request.user.is_supervisor:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('supervisor_dashboard')

    # Get the supervisor instance for the logged-in user
    supervisor = request.user.supervisor

    # Get the current week's start date (Monday)
    today = timezone.now().date()
    week_start_date = today - timedelta(days=today.weekday())

    # Fetch tasks for the current week for all students assigned to this supervisor
    tasks = Task.objects.filter(
        student__workschedule__supervisor=supervisor,
        work_date__gte=week_start_date,
        work_date__lt=week_start_date + timedelta(days=7)
    ).order_by('work_date')

    # Handle feedback submission
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        if feedback_text and feedback_text.strip():  # Ensure feedback is not empty
            # Get the first student assigned to the supervisor
            work_schedule = WorkSchedule.objects.filter(
                supervisor=supervisor
            ).first()

            if work_schedule:
                # Create or update weekly feedback
                WeeklyFeedback.objects.create(
                    student=work_schedule.student,
                    supervisor=supervisor,
                    week_start_date=week_start_date,
                    comments=feedback_text
                )
                messages.success(request, "Weekly feedback submitted successfully!")
            else:
                messages.error(request, "No student work schedule found for this supervisor.")
        else:
            messages.error(request, "Feedback cannot be empty.")
        return redirect('supervisor_feedback')

    return render(request, 'supervisor/supervisor_feedback.html', {
        'tasks': tasks,
        'week_start_date': week_start_date
    })

from django.shortcuts import get_object_or_404, render
from .models import Student, WorkSchedule, Task, MonthlyEvaluation

def student_progress_view(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    schedule = WorkSchedule.objects.filter(student=student, is_active=True).first()

    if not schedule:
        return redirect('create_schedule', student_id=student_id)

    tasks = student.tasks.all().order_by('work_date')
    workdays_per_week = schedule.workdays_per_week

    grouped_tasks = []
    weekly_tasks = []
    week_number = 1

    for i, task in enumerate(tasks):
        weekly_tasks.append(task)
        if len(weekly_tasks) == workdays_per_week:
            # Check if all tasks in the week have supervisor_feedback
            all_have_feedback = all(t.supervisor_feedback for t in weekly_tasks)

            # Check if monthly evaluation exists for this week
            month_number = (week_number - 1) // 4 + 1  # Calculate month_number based on week_number
            month_evaluation_exists = MonthlyEvaluation.objects.filter(student=student, month_number=month_number).exists()

            grouped_tasks.append({
                'week_number': week_number,
                'tasks': weekly_tasks,
                'is_complete': True,
                'has_feedback': all_have_feedback,
                'month_evaluation_exists': month_evaluation_exists,  # Pass this flag to the template
            })
            weekly_tasks = []
            week_number += 1

    # If tasks remain and do not form a full week
    if weekly_tasks:
        all_have_feedback = all(t.supervisor_feedback for t in weekly_tasks)
        month_number = (week_number - 1) // 4 + 1
        month_evaluation_exists = MonthlyEvaluation.objects.filter(student=student, month_number=month_number).exists()

        grouped_tasks.append({
            'week_number': week_number,
            'tasks': weekly_tasks,
            'is_complete': False,
            'has_feedback': all_have_feedback,
            'month_evaluation_exists': month_evaluation_exists,  # Pass this flag
        })

    context = {
        'student': student,
        'work_schedule': schedule,
        'grouped_tasks': grouped_tasks,
    }
    
    return render(request, 'Supervisor/student_reported_tasks.html', context)

def create_schedule(request, student_id):
    student = get_object_or_404(Student, user_id=student_id)
    
    if request.method == 'POST':
        form = WorkScheduleForm(request.POST)
        if form.is_valid():
            # Deactivate any existing schedules
            WorkSchedule.objects.filter(student=student).update(is_active=False)
            
            schedule = form.save(commit=False)
            schedule.student = student
            schedule.supervisor = request.user.supervisor
            schedule.save()
            return redirect('student_progress', student_id=student_id)
    else:
        form = WorkScheduleForm()
    
    return render(request, 'create_schedule.html', {'form': form, 'student': student})

def provide_weekly_feedback(request, student_id, week_number):
    student = get_object_or_404(Student, user_id=student_id)
    schedule = get_object_or_404(WorkSchedule, student=student, is_active=True)
    
    # Get tasks for the week
    start_index = (week_number - 1) * schedule.workdays_per_week
    end_index = start_index + schedule.workdays_per_week
    tasks = student.tasks.all().order_by('work_date')[start_index:end_index]
    
    if request.method == 'POST':
        form = TaskFeedbackForm(request.POST)
        if form.is_valid():
            # Save feedback for all tasks in the week
            for task in tasks:
                task.supervisor_feedback = form.cleaned_data['supervisor_feedback']
                task.save()
            return redirect('student_reported_tasks', student_id=student_id)
    else:
        form = TaskFeedbackForm()
    
    context = {
        'student': student,
        'week_number': week_number,
        'tasks': tasks,
        'form': form
    }
    return render(request,'Supervisor/provide_weekly_feedback.html', context)