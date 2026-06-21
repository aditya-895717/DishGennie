"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, MaidProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for customer registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    referral_code_input = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone', 'password', 'password_confirm', 'referral_code_input'
        ]

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        referral_input = validated_data.pop('referral_code_input', '')
        referred_by = None
        if referral_input:
            try:
                referred_by = CustomUser.objects.get(referral_code=referral_input)
            except CustomUser.DoesNotExist:
                pass

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            password=validated_data['password'],
            role=CustomUser.Role.CUSTOMER,
            referred_by=referred_by,
        )
        return user


class MaidRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for maid/partner registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    aadhaar_number = serializers.CharField(max_length=12, required=False)
    aadhaar_document = serializers.FileField(required=False)
    experience_years = serializers.IntegerField(required=False, default=0)
    hourly_rate = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    bio = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name', 'phone',
            'password', 'password_confirm',
            'aadhaar_number', 'aadhaar_document', 'experience_years',
            'hourly_rate', 'bio',
        ]

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        profile_data = {
            'aadhaar_number': validated_data.pop('aadhaar_number', ''),
            'aadhaar_document': validated_data.pop('aadhaar_document', None),
            'experience_years': validated_data.pop('experience_years', 0),
            'hourly_rate': validated_data.pop('hourly_rate', 200.00),
            'bio': validated_data.pop('bio', ''),
        }

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            password=validated_data['password'],
            role=CustomUser.Role.MAID,
        )

        MaidProfile.objects.create(user=user, **profile_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile view/update."""

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'avatar', 'role', 'city', 'address',
            'latitude', 'longitude', 'is_verified', 'referral_code',
            'date_of_birth', 'created_at',
        ]
        read_only_fields = ['id', 'username', 'role', 'is_verified', 'referral_code', 'created_at']


class MaidProfileSerializer(serializers.ModelSerializer):
    """Serializer for maid profile details."""
    user = UserProfileSerializer(read_only=True)
    skills = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = MaidProfile
        fields = [
            'id', 'user', 'aadhaar_number', 'verification_status',
            'skills', 'experience_years', 'hourly_rate',
            'is_available', 'bio', 'languages',
            'avg_rating', 'total_reviews', 'total_jobs',
            'profile_completion',
        ]
        read_only_fields = ['verification_status', 'avg_rating', 'total_reviews', 'total_jobs']


class MaidCardSerializer(serializers.ModelSerializer):
    """Lightweight serializer for maid listing cards."""
    name = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    skills = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = MaidProfile
        fields = [
            'id', 'user_id', 'name', 'avatar', 'city_name', 'skills',
            'experience_years', 'hourly_rate', 'is_available',
            'avg_rating', 'total_reviews', 'total_jobs', 'bio',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_user_id(self, obj):
        return str(obj.user_id)

    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None

    def get_city_name(self, obj):
        return obj.user.city.name if obj.user.city else ''


class LoginSerializer(serializers.Serializer):
    """Serializer for login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        data['user'] = user
        return data
