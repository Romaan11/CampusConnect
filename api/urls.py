
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api import views


#the r in this means raw data and tyo hale pani hunxa na hale pani
# Main router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user') 
router.register(r'groups', views.GroupViewSet)
router.register(r'notices', views.NoticeViewSet)
router.register(r'routines', views.RoutineViewSet, basename='routine')


# Custom API Root
@api_view(['GET'])
def custom_api_root(request, format=None):
    return Response({
        "users": reverse('user-list', request=request, format=format),
        "groups": reverse('group-list', request=request, format=format),
        "notices": reverse('notice-list', request=request, format=format),
        "routines": reverse('routine-list', request=request, format=format),
        "auth": {
            "register": reverse('register', request=request, format=format),
            "login": reverse('login', request=request, format=format),   # custom email login
            "logout": reverse('logout', request=request, format=format), # use real logout view
            "token_refresh": reverse('token_refresh', request=request, format=format),
            "profile": reverse('profile', request=request, format=format),


            # optional logout link (manual implementation needed if you want real JWT blacklist logout)
            # "logout": request.build_absolute_uri('/api-auth/logout/'), 
        }
    })

urlpatterns = [

    # Override API root
    path('', custom_api_root, name='api-root'),

    # RESTful routes (CRUD for notices, routines, users, etc.)
    path('', include(router.urls)),         # main api endpoints
    

    # Authentication endpoints: /api/auth/
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),   # use custom login
    path('auth/logout/', views.LogoutView.as_view(), name='logout'), # custom logout
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),

    # Optional: DRF Browsable API login/logout
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),   #for login in the rest api
]



