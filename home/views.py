from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm, ContactForm
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
from .models import Subscriber, Contact
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site



def password_reset_request(request):
    """Handle password reset request"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Check if user exists
        associated_users = User.objects.filter(email=email)
        if associated_users.exists():
            for user in associated_users:
                # Generate password reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset URL
                current_site = get_current_site(request)
                protocol = 'https' if request.is_secure() else 'http'
                reset_url = f"{protocol}://{current_site.domain}/password-reset-confirm/{uid}/{token}/"
                
                # Email subject and message
                subject = 'Password Reset Request - DishGennie'
                message = f"""
Hello {user.first_name or user.username},

You recently requested to reset your password for your DishGennie account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours for security reasons.

If you did not request a password reset, please ignore this email or contact support if you have concerns.

Best regards,
The DishGennie Team
                """
                
                # HTML version of the email
                html_message = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                        <h2 style="color: #ff6b35;">Password Reset Request</h2>
                        <p>Hello <strong>{user.first_name or user.username}</strong>,</p>
                        <p>You recently requested to reset your password for your DishGennie account.</p>
                        <p>Click the button below to reset your password:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_url}" 
                               style="background: linear-gradient(135deg, #ff6b35, #f7931e); 
                                      color: white; 
                                      padding: 12px 30px; 
                                      text-decoration: none; 
                                      border-radius: 25px; 
                                      font-weight: bold;
                                      display: inline-block;">
                                Reset Password
                            </a>
                        </div>
                        <p style="color: #666; font-size: 14px;">
                            Or copy and paste this link into your browser:<br>
                            <a href="{reset_url}" style="color: #ff6b35;">{reset_url}</a>
                        </p>
                        <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                            This link will expire in 24 hours for security reasons.<br>
                            If you did not request a password reset, please ignore this email.
                        </p>
                        <p style="margin-top: 20px;">
                            Best regards,<br>
                            <strong>The DishGennie Team</strong>
                        </p>
                    </div>
                </body>
                </html>
                """
                
                # Send email
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    messages.success(request, 'Password reset link has been sent to your email address.')
                except Exception as e:
                    messages.error(request, 'Error sending email. Please try again later.')
                    print(f"Email error: {e}")
        else:
            messages.error(request, 'No account found with this email address.')
        
        return redirect('password_reset_request')
    
    return render(request, 'password_reset.html')


def password_reset_confirm(request, uidb64, token):
    """Handle password reset confirmation"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            
            if password1 and password2:
                if password1 == password2:
                    if len(password1) >= 8:
                        user.set_password(password1)
                        user.save()
                        messages.success(request, 'Your password has been reset successfully! You can now login.')
                        return redirect('signin')
                    else:
                        messages.error(request, 'Password must be at least 8 characters long.')
                else:
                    messages.error(request, 'Passwords do not match.')
            else:
                messages.error(request, 'Please fill in both password fields.')
        
        return render(request, 'password_reset_confirm.html', {'validlink': True, 'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return render(request, 'password_reset_confirm.html', {'validlink': False})

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'aboutus.html')

def service(request):
    return render(request, 'service.html')

def contact(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Save to database
        contact_submission = Contact.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )
        
        messages.success(request, 'Thank you! Your message has been received. We will respond soon.')
        try:
            send_mail(
            subject='DishGennie Apology to you sir !!!',
            message='We are really sorry to hear such an incident sir !!! We will definetly work for it please be patience ',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        except:
            return HttpResponse('Exception sir')

        return redirect('contact')
    
    return render(request, 'contact.html')

def signup(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        plan = request.POST.get('plan', 'free')
        
        # Validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'signup.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            # Log the user in
            login(request, user)
            messages.success(request, f'Welcome to DishGennie, {first_name}! Your account has been created successfully.')
            return redirect('index')
            
        except Exception as e:
            messages.error(request, 'An error occurred. Please try again.')
            return render(request, 'signup.html')
    
    return render(request, 'signup.html')

def signin(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect to next page if specified, otherwise home
            next_page = request.GET.get('next', 'index')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'signin.html')
    
    return render(request, 'signin.html')

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('index')

@require_POST
def subscribe_newsletter(request):
    try:
        email = request.POST.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Email is required.'
            }, status=400)
        
        if Subscriber.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'This email is already subscribed!'
            }, status=400)
        
        subscriber = Subscriber.objects.create(email=email)
        
        subject = 'Welcome to DishGennie Newsletter! 🍳'
        message = 'Thank you for subscribing!'
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully subscribed! Check your email.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


def is_admin(user):
    return user.is_superuser

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard accessible only to staff members"""
    subscribers = Subscriber.objects.all()
    contacts = Contact.objects.all()
    users = User.objects.all()
    
    context = {
        'subscribers': subscribers,
        'contacts': contacts,
        'users': users,
        'total_subscribers': subscribers.count(),
        'total_contacts': contacts.count(),
        'total_users': users.count(),
    }
    return render(request, 'admin_dashboard.html', context)

@user_passes_test(is_admin)
def admin_manage_users(request):
    """Manage users - only for superadmins"""
    users = User.objects.all()
    return render(request, 'admin_users.html', {'users': users})

@user_passes_test(lambda u: u.is_staff)
@login_required
def admin_delete_contact(request, contact_id):
    """Delete contact submission - staff only"""
    if request.method == 'POST':
        contact = Contact.objects.get(id=contact_id)
        contact.delete()
        messages.success(request, 'Contact deleted successfully!')
    return redirect('admin_dashboard')

@user_passes_test(lambda u: u.is_staff)
@login_required
def admin_reply_contact(request, contact_id):
    """Reply to contact - staff only"""
    contact = Contact.objects.get(id=contact_id)
    if request.method == 'POST':
        reply_message = request.POST.get('reply_message')
        
        # Send email reply
        send_mail(
            subject=f"Re: {contact.subject}",
            message=reply_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact.email],
            fail_silently=False,
        )
        
        # Update contact
        contact.is_replied = True
        contact.reply_message = reply_message
        contact.replied_by = request.user
        contact.replied_at = timezone.now()
        contact.save()
        
        messages.success(request, 'Reply sent successfully!')
        return redirect('admin_dashboard')
    
    return render(request, 'admin_reply.html', {'contact': contact})

@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_toggle_user_status(request, user_id):
    """Toggle user active status - superuser only"""
    user = User.objects.get(id=user_id)
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} {status}!')
    return redirect('admin_manage_users')

