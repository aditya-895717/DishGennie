"""
API Views for accounts app.
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from .models import CustomUser, MaidProfile
from .serializers import (
    UserRegistrationSerializer, MaidRegistrationSerializer,
    UserProfileSerializer, MaidProfileSerializer, MaidCardSerializer,
    LoginSerializer,
)
from .geo import (
    bounding_box, haversine_km, maid_coordinates,
    parse_coordinate, parse_radius_km,
)
from .permissions import IsAdmin, IsMaid, IsCustomer
from .email_utils import (
    send_welcome_email, notify_admin_new_registration,
    send_maid_approval_email, send_maid_rejection_email,
)


def _approve_maid_profile(profile, remarks=''):
    """Shared by AdminMaidVerificationView and ApproveMaidView."""
    profile.verification_status = MaidProfile.VerificationStatus.APPROVED
    profile.verification_remarks = remarks
    profile.verified_at = timezone.now()
    profile.save()
    profile.user.is_verified = True
    profile.user.save()
    send_maid_approval_email(profile.user)


def _reject_maid_profile(profile, remarks=''):
    """Shared by AdminMaidVerificationView and RejectMaidView."""
    profile.verification_status = MaidProfile.VerificationStatus.REJECTED
    profile.verification_remarks = remarks
    profile.save()
    profile.user.is_active = False
    profile.user.save()
    send_maid_rejection_email(profile.user, remarks)


class RegisterView(generics.CreateAPIView):
    """Customer registration endpoint."""
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # UniqueValidator on username already covers the common case; this is
        # defense-in-depth against a race between two simultaneous requests.
        try:
            user = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'That username was just taken by someone else. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_welcome_email(user)
        notify_admin_new_registration(user)
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
        try:
            user = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'That username was just taken by someone else. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_welcome_email(user)
        notify_admin_new_registration(user)
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
    """List maids with search & filter.

    Passing `lat` and `lng` switches this into the radius-based nearby search
    from Architecture.md §5.4: results are restricted to maids within
    `radius_km` (default 10, capped at 100) and ordered nearest-first, with
    the distance attached to each card.
    """
    serializer_class = MaidCardSerializer
    permission_classes = [AllowAny]

    def _nearby(self, qs):
        """Return a distance-sorted list, or None when no usable origin was
        supplied and the caller should keep the plain queryset."""
        params = self.request.query_params
        lat = parse_coordinate(params.get('lat'), 90)
        lng = parse_coordinate(params.get('lng'), 180)
        if lat is None or lng is None:
            return None

        radius_km = parse_radius_km(params.get('radius_km'))
        min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)

        # Cheap SQL window first — a maid qualifies on her live tracked
        # position or, failing that, the coordinates saved on her account.
        in_box = (
            Q(current_lat__range=(min_lat, max_lat), current_lng__range=(min_lng, max_lng))
            | Q(
                current_lat__isnull=True,
                user__latitude__range=(min_lat, max_lat),
                user__longitude__range=(min_lng, max_lng),
            )
        )

        nearby = []
        for profile in qs.filter(in_box):
            coordinates = maid_coordinates(profile)
            if coordinates is None:
                continue
            distance = haversine_km(lat, lng, coordinates[0], coordinates[1])
            if distance <= radius_km:
                profile.distance_km = round(distance, 2)
                nearby.append(profile)

        nearby.sort(key=lambda item: item.distance_km)
        return nearby

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

        qs = qs.distinct()

        # Nearest-first replaces the requested ordering when searching by
        # radius — "closest to me" is the whole point of that query.
        nearby = self._nearby(qs)
        if nearby is not None:
            return nearby

        ordering = self.request.query_params.get('ordering', '-avg_rating')
        return qs.order_by(ordering)


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
    """Admin: Approve or reject maid verification (generic action param).

    Kept for the existing admin verification page, which already calls this
    endpoint with {action: 'approve'|'reject', remarks}. ApproveMaidView and
    RejectMaidView below share the same underlying logic via
    _approve_maid_profile/_reject_maid_profile.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            profile = MaidProfile.objects.get(pk=pk)
        except MaidProfile.DoesNotExist:
            return Response({'error': 'Maid profile not found.'}, status=404)

        action = request.data.get('action')  # 'approve' or 'reject'
        remarks = request.data.get('remarks', '')

        if action == 'approve':
            _approve_maid_profile(profile, remarks)
        elif action == 'reject':
            _reject_maid_profile(profile, remarks)
        else:
            return Response({'error': 'Invalid action. Use approve or reject.'}, status=400)

        return Response({
            'message': f'Maid {action}ed successfully.',
            'status': profile.verification_status,
        })


class ApproveMaidView(views.APIView):
    """Admin: Approve a maid's verification (dedicated endpoint)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            profile = MaidProfile.objects.get(pk=pk)
        except MaidProfile.DoesNotExist:
            return Response({'error': 'Maid profile not found.'}, status=404)

        _approve_maid_profile(profile, request.data.get('remarks', ''))
        return Response({
            'message': 'Maid approved successfully.',
            'status': profile.verification_status,
        })


class RejectMaidView(views.APIView):
    """Admin: Reject a maid's verification (dedicated endpoint). Accepts an optional 'reason'."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            profile = MaidProfile.objects.get(pk=pk)
        except MaidProfile.DoesNotExist:
            return Response({'error': 'Maid profile not found.'}, status=404)

        _reject_maid_profile(profile, request.data.get('reason', ''))
        return Response({
            'message': 'Maid rejected successfully.',
            'status': profile.verification_status,
        })
