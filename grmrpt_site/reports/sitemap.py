from django.contrib.sitemaps import Sitemap
from django.db.models.query import QuerySet
from django.urls import reverse

from reports.models import *


class ApiSitemap(Sitemap):
    """
    Generic sitemap for API objects
    """
    model = None
    url = None

    def items(self) -> QuerySet:
        return self.model.objects.all()

    def location(self, obj) -> str:
        if self.url is None:
            link = '{}-detail'.format(self.model.__name__.lower())
        else:
            link = self.url

        return reverse(link, args=[obj.id])


class ReportSitemap(ApiSitemap):
    """
    Sitemap for reports
    """
    model = Report


class RunSitemap(ApiSitemap):
    """
    Sitemap for runs
    """
    model = Run


class ResortSitemap(ApiSitemap):
    """
    Sitemap for resorts
    """
    model = Resort


class BMReportsitemap(ApiSitemap):
    """
    Sitemap for BMReports
    """
    model = BMReport


class ApiStaticSitemap(Sitemap):
    """
    Sitemap for api index and other static pages
    """
    def items(self) -> List[str]:
        return [
            'api-index',
            'api_token_auth'
        ]

    def location(self, obj: str) -> str:
        return reverse(obj)
