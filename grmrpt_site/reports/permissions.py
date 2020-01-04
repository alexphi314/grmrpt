from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only admins edit access
    """
    def has_object_permission(self, request, view, *args):
        """
        Return True if permission granted
        """
        # Read permissions are allowed to any request,
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the staff
        return bool(request.user and request.user.is_staff)

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return self.has_object_permission(request, view)
