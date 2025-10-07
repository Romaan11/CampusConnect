from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUser(BasePermission):
    """
    Allows access to admin users (is_staff=True).
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff
    

class ReadOnly(BasePermission):
    """
    Allows only GET, HEAD or OPTIONS requests.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
