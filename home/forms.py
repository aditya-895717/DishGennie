from django import forms

class SignUpForm(forms.Form):
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    plan = forms.ChoiceField(
        choices=[
            ('free', 'Free'),
            ('premium', 'Premium'),
            ('family', 'Family')
        ],
        initial='free',
        widget=forms.RadioSelect
    )
    username = forms.CharField(max_length=30, required=True)


class ContactForm(forms.Form):
    first_name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com'})
    )
    phone = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Phone (optional)'})
    )
    subject = forms.CharField(
        max_length=200, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Subject'})
    )
    message = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Your message...', 'rows': 5})
    )
