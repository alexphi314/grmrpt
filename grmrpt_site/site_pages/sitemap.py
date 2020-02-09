from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticSitemap(Sitemap):
    """
    Sitemap for static pages
    """
    def items(self):
        return [
            'signup',
            'profile',
            'login',
            'logout',
            'about',
            'contact_us',
            'delete',
            'index',
            'reports'
        ]

    def location(self, obj: str) -> str:
        return reverse(obj)
