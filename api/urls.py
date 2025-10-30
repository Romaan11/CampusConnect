
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api import views


#the r in this means raw data and tyo hale pani hunxa na hale pani
# Main router for ViewSets
# --------------------- Main Router ---------------------
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user') 
router.register(r'groups', views.GroupViewSet)
router.register(r'notices', views.NoticeViewSet)
router.register(r'routines', views.RoutineViewSet, basename='routine')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'admission-records', views.AdminAdmissionRecordViewSet, basename='admissionrecord')



# --------------------- Custom API Root ---------------------
# Custom API Root
@api_view(['GET'])
def custom_api_root(request, format=None):
    
    return Response({
        "users": reverse('user-list', request=request, format=format),
        "groups": reverse('group-list', request=request, format=format),
        "notices": reverse('notice-list', request=request, format=format),
        "routines": reverse('routine-list', request=request, format=format),
        "events": reverse('event-list', request=request, format=format),
        "admission-records": reverse('admissionrecord-list', request=request, format=format),
        "auth": {
            # "register": reverse('register', request=request, format=format),
            "login": reverse('login', request=request, format=format),   # custom email login
            "logout": reverse('logout', request=request, format=format), # use real logout view
            "change_password": reverse('change_password', request=request, format=format),
            "token_refresh": reverse('token_refresh', request=request, format=format),
            "profile": reverse('profile', request=request, format=format),
            "send_notice": reverse('send-notice', request=request, format=format),

            # ------------------ NEW: Forgot/Reset Password ------------------
            "forgot_password": reverse('forgot-password', request=request, format=format),
            "reset_password": reverse('reset-password', request=request, format=format),
            # "resend_code": reverse('resend-code', request=request, format=format),

            # optional logout link (manual implementation needed if you want real JWT blacklist logout)
            # "logout": request.build_absolute_uri('/api-auth/logout/'), 
        }
    })

# --------------------- URL Patterns ---------------------
urlpatterns = [

    # Override API root
    path('', custom_api_root, name='api-root'),

    # RESTful routes (CRUD for notices, routines, users, etc.)
    path('', include(router.urls)),         # main api endpoints
    

    # Authentication endpoints: /api/auth/
    # path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),   # use custom login
    path('auth/logout/', views.LogoutView.as_view(), name='logout'), # custom logout
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # login
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # refresh token
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),
    # Send notification endpoint
    path('auth/send-notice/', views.send_notice_notification, name='send-notice'),

    # ------------------ NEW: Forgot/Reset Password Endpoints ------------------    
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    # path('auth/resend-code/', views.ResendCodeView.as_view(), name='resend-code'),


    # Optional: DRF Browsable API login/logout 
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),   #for login in the rest api
]



