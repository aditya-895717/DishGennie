"""
API Views for accounts app.
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from .models import CustomUser, MaidProfile
from .serializers import (
    UserRegistrationSerializer, MaidRegistrationSerializer,
    UserProfileSerializer, MaidProfileSerializer, MaidCardSerializer,
    LoginSerializer,
)
from .permissions import IsAdmin, IsMaid, IsCustomer


class RegisterView(generics.CreateAPIView):
    """Customer registration endpoint."""
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Registration successful!',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class MaidRegisterView(generics.CreateAPIView):
    """Maid/partner registration endpoint."""
    serializer_class = MaidRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Maid registration successful! Verification pending.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    """JWT Login endpoint."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful!',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    """View/update own profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class MaidProfileView(generics.RetrieveUpdateAPIView):
    """View/update maid profile."""
    serializer_class = MaidProfileSerializer
    permission_classes = [IsAuthenticated, IsMaid]

    def get_object(self):
        profile, _ = MaidProfile.objects.get_or_create(user=self.request.user)
        return profile


class MaidListView(generics.ListAPIView):
    """List maids with search & filter."""
    serializer_class = MaidCardSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = MaidProfile.objects.filter(
            verification_status__in=['approved', 'verified'],
            is_available=True,
        ).select_related('user', 'user__city').prefetch_related('skills')

        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(user__city__name__icontains=city)

        # Filter by service/skill
        service = self.request.query_params.get('service')
        if service:
            qs = qs.filter(skills__name__icontains=service)

        # Filter by min rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            qs = qs.filter(avg_rating__gte=min_rating)

        # Filter by max price
        max_price = self.request.query_params.get('max_price')
        if max_price:
            qs = qs.filter(hourly_rate__lte=max_price)

        # Search by name
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        # Ordering
        ordering = self.request.query_params.get('ordering', '-avg_rating')
        qs = qs.order_by(ordering)

        return qs.distinct()


class MaidDetailView(generics.RetrieveAPIView):
    """Get maid profile details."""
    serializer_class = MaidProfileSerializer
    permission_classes = [AllowAny]
    queryset = MaidProfile.objects.filter(
        verification_status__in=['approved', 'verified']
    ).select_related('user', 'user__city').prefetch_related('skills')


class AdminUserListView(generics.ListAPIView):
    """Admin: List all users with filters."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = CustomUser.objects.all()
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs


class AdminMaidProfileListView(generics.ListAPIView):
    """Admin: List all maid profiles, including pending verification."""
    serializer_class = MaidProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = MaidProfile.objects.select_related('user', 'user__city').prefetch_related('skills')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(verification_status=status_filter)
        return qs.order_by('-user__created_at')


class AdminMaidVerificationView(views.APIView):
    """Admin: Approve or reject maid verification."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        from django.utils import timezone
        try:
            profile = MaidProfile.objects.get(pk=pk)
        except MaidProfile.DoesNotExist:
            return Response({'error': 'Maid profile not found.'}, status=404)

        action = request.data.get('action')  # 'approve' or 'reject'
        remarks = request.data.get('remarks', '')

        if action == 'approve':
            profile.verification_status = 'approved'
            profile.verified_at = timezone.now()
            profile.user.is_verified = True
            profile.user.save()
        elif action == 'reject':
            profile.verification_status = 'rejected'
            profile.user.is_active = False
            profile.user.save()
        else:
            return Response({'error': 'Invalid action. Use approve or reject.'}, status=400)

        profile.verification_remarks = remarks
        profile.save()
        return Response({
            'message': f'Maid {action}ed successfully.',
            'status': profile.verification_status,
        })
