from django import template
from django.contrib.auth.models import AnonymousUser
from ..models import UserProfile

register = template.Library()

@register.filter
def is_researcher(user):
    """Check if user is a researcher"""
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        return False
    
    try:
        return user.profile.is_researcher()
    except UserProfile.DoesNotExist:
        return False

@register.filter
def is_novice(user):
    """Check if user is a novice"""
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        return False
    
    try:
        return user.profile.is_novice()
    except UserProfile.DoesNotExist:
        return True  # Default to novice if no profile
