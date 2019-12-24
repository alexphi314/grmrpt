from django.db import models


class Resort(models.Model):
    """
    Ski resort model
    """
    name = models.CharField("Name of the resort", max_length=1000)
    location = models.CharField("Location of the resort", max_length=1000, blank=True, null=True)
    report_url = models.CharField("URL to grooming report", max_length=2000, blank=True, null=True)

    def __str__(self):
        return self.name


class Report(models.Model):
    """
    Object model for grooming report
    """
    date = models.DateTimeField("Date of Grooming Report")
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE)

    def __str__(self):
        return '{}: {}'.format(self.resort, self.date.strftime('%Y-%m-%d'))

class Run(models.Model):
    """
    Object model for ski run
    """
    name = models.CharField("Name of the run", max_length=1000)
    difficulty = models.CharField("Difficulty of run, green/blue/black", max_length=100, blank=True, null=True)
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE)
    report = models.ManyToManyField(Report)

    def __str__(self):
        return self.name
