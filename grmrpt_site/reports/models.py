import os
from typing import Union, FrozenSet, Set, List
import json
from json.decoder import JSONDecodeError
import logging
import datetime as dt

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, m2m_changed, post_delete, pre_delete
from django.dispatch import receiver
from django.core.validators import RegexValidator, ValidationError
from rest_framework.authtoken.models import Token
import boto3


class Resort(models.Model):
    """
    Ski resort model
    """
    JSON = 'json'
    JSON_VAIL = 'json-vail'
    PARSE_METHOD_CHOICES = [
        (JSON, 'json'),
        (JSON_VAIL, 'json-vail')
    ]

    name = models.CharField("Name of the resort", max_length=1000)
    location = models.CharField("Location of the resort", max_length=1000, blank=True, null=True)
    report_url = models.CharField("URL to grooming report", max_length=2000, blank=True, null=True)
    site_id = models.IntegerField("site id identifier for vail resort properties", blank=True, null=True)
    sns_arn = models.CharField("AWS SNS Topic identifier", max_length=1000, blank=True, null=True)
    parse_mode = models.CharField("Type of parsing to apply to grooming report url", max_length=100,
                                  choices=PARSE_METHOD_CHOICES, default=JSON_VAIL)
    display_url = models.CharField("URL users can click on to view grooming report", max_length=2000,
                                   blank=True, null=True)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """
        Raise a ValidationError if the parse_mode is json-vail and site_id is None
        """
        if self.parse_mode == self.JSON_VAIL and self.site_id is None:
            raise ValidationError(
                'If json-vail parse mode is selected, site_id is required',
                code='missing_site_id'
            )


class Report(models.Model):
    """
    Object model for grooming report
    """
    date = models.DateField("Date of Grooming Report")
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='reports')

    def __str__(self) -> str:
        return '{}: {}'.format(self.resort, self.date.strftime('%Y-%m-%d'))


class Run(models.Model):
    """
    Object model for ski run
    """
    GREEN = 'green'
    BLUE = 'blue'
    BLUEBLACK = 'blueblack'
    BLACK = 'black'
    DOUBLE_BLACK = 'doubleblack'
    SNOWSHOE = 'snowshoe'
    TERRAIN_PARK = 'park'
    GREENBLUE = 'greenblack'
    DIFFICULTY_CHOICES = [
        (GREEN, 'Green'),
        (BLUE, 'Blue'),
        (BLUEBLACK, 'Blue/Black'),
        (BLACK, 'Black'),
        (DOUBLE_BLACK, 'Double Black'),
        (SNOWSHOE, 'Snowshoe'),
        (TERRAIN_PARK, 'Terrain Park'),
        (GREENBLUE, 'Green/Blue')
    ]
    name = models.CharField("Name of the run", max_length=1000)
    difficulty = models.CharField("Difficulty of run, green/blue/black", max_length=20, blank=True, null=True,
                                  choices=DIFFICULTY_CHOICES)
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='runs')
    reports = models.ManyToManyField(Report, related_name='runs')

    def __str__(self) -> str:
        return self.name


class BMReport(models.Model):
    """
    Object model for processed Hidden Diamond grooming report
    """
    date = models.DateField("Date of Grooming Report")
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='bm_reports')
    runs = models.ManyToManyField(Run, related_name='bm_reports')
    full_report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='bm_report')

    def __str__(self) -> str:
        return '{}: {}'.format(self.resort, self.date.strftime('%Y-%m-%d'))


phone_regex = RegexValidator(regex=r'^\+\d{9,16}$',
                             message="Phone number must be entered in the format: '+999999999'. "
                                     "Up to 16 digits allowed.")
class BMGUser(models.Model):
    """
    Extend the User model to include a few more fields
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bmg_user')
    favorite_runs = models.ManyToManyField(Run, related_name='users_favorited')
    phone = models.CharField("Phone Number", blank=True, null=True, max_length=17, unique=True,
                             validators=[phone_regex])
    resorts = models.ManyToManyField(Resort, related_name='bmg_users')
    sub_arn = models.CharField("AWS SNS Subscription arns", max_length=1000, blank=True, null=True)
    contact_days = models.CharField("string array of allowed contact days", max_length=1000, blank=True, null=True)

    PHONE = 'sms'
    EMAIL = 'email'
    CONTACT_METHOD_CHOICES = [
        (PHONE, 'Phone'),
        (EMAIL, 'Email')
    ]
    contact_method = models.CharField(max_length=5, choices=CONTACT_METHOD_CHOICES, default=EMAIL)

    def __str__(self) -> str:
        return self.user.username


class Notification(models.Model):
    """
    Model a notification sent about a report
    """
    bm_report = models.OneToOneField(BMReport, related_name='notification', on_delete=models.CASCADE)
    sent = models.DateTimeField("Time when the notification was sent", auto_now_add=True)
    type = models.CharField("Type of notification", max_length=100, blank=True, null=True)

    def __str__(self) -> str:
        return '{}'.format(self.bm_report.date.strftime('%Y-%m-%d'))


class Alert(models.Model):
    """
    Model an alert sent to developers about application errors
    """
    bm_report = models.OneToOneField(BMReport, related_name='alert', on_delete=models.CASCADE)
    sent = models.DateTimeField("Time when alert was sent", auto_now_add=True)

    def __str__(self) -> str:
        return '{}'.format(self.sent.strftime('%Y-%m-%dT%H:%M:%S'))

############################
### Define Model Signals ###
############################


def publish_sns_topic(resort: Resort) -> None:
    """
    Talk to SNS and create a topic for this resort

    :param resort: resort object to create a topic for
    """
    client = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                          aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
    response = client.create_topic(
        Name='{}_{}_bmgrm'.format(os.getenv('ENVIRON_TYPE', ''),
                                  resort.name.lower().replace(' ', '_')
                                  ),
        Attributes={
            'DisplayName': '{} Blue Moon Grooming Report:'.format(resort.name)
        },
        Tags=[
            {
                'Key': 'resort',
                'Value': '{}'.format(resort.name)
            },
        ]
    )
    resort.sns_arn = response['TopicArn']
    resort.save()


def delete_sns_topic(resort: Resort) -> None:
    """
    Remove the SNS topic associated with a resort

    :param resort: resort owning the sns topic
    """
    if resort.sns_arn is not None:
        client = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                              aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

        # Delete the subscriptions
        for user in resort.bmg_users.all():
            unsubscribe_user_to_topic(user, client, resort)

        # Delete the topic
        client.delete_topic(TopicArn=resort.sns_arn)


@receiver(post_save, sender=Resort)
def create_sns_topic(instance: Resort, created: bool, **kwargs) -> None:
    """
    Create a SNS topic corresponding to this resort when the resort is first created.

    :param instance: Resort object being created
    :param created: True if the object is first created
    """
    if created:
        publish_sns_topic(instance)


@receiver(post_delete, sender=Resort)
def remove_sns_topic(instance: Resort, **kwargs) -> None:
    """
    Upon resort object deletion, delete the sns topic

    :param instance: Resort object being deleted
    """
    delete_sns_topic(instance)


@receiver(post_save, sender=Report)
def create_update_bmreport(instance: Report, created: bool, **kwargs) -> None:
    """
    Create or update the corresponding BMReport object when the Report object is updated

    :param sender: Report class sending signal
    :param instance: Report object being saved
    :param created: True if new object being created; False for update
    """
    bmreport_runs = get_bm_runs(instance)
    if created:
        bm_report = BMReport.objects.create(date=instance.date, resort=instance.resort,
                                            full_report=instance)
        bm_report.runs.set(bmreport_runs)
    else:
        bm_report = instance.bm_report
        bm_report.date = instance.date
        bm_report.resort = instance.resort
        bm_report.runs.set(bmreport_runs)
        bm_report.save()


@receiver(m2m_changed, sender=Report.runs.through)
def update_bmreport(instance: Union[Report, Run], action: str, reverse: bool, **kwargs) -> None:
    """
    Update the bmreport runs field if Report field updated

    :param instance: report object being modified
    :param action: type of update on relation
    :param reverse: True if the Report object is being modified; false if the Run object is being modified
    """
    # If the Report object is being modified (i.e. runs added to report)
    # Instance -> Report
    if action == 'post_add' and reverse:
        bmreport_runs = get_bm_runs(instance)
        instance.bm_report.runs.set(bmreport_runs)
    # If the Run object is being modified (i.e. run created and assigned to report)
    # Instance -> Run
    elif action == 'post_add' and not reverse:
        for report in instance.reports.all():
            bmreport_runs = get_bm_runs(report)
            report.bm_report.runs.set(bmreport_runs)


@receiver(post_save, sender=User)
def create_update_bmguser(instance: User, created: bool, **kwargs) -> None:
    """
    Create or update a corresponding BMGUser object when a User is created

    :param instance: actual instance being created
    :param created: True if instance is actually being created
    """
    if created:
        BMGUser.objects.create(user=instance)
    else:
        instance.bmg_user.save()


@receiver(post_save, sender=User)
def create_user_token(instance: User, created: bool, **kwargs) -> None:
    """
    Create a token for a user when it is created

    :param instance: user instance being saved
    :param created: True if instance is actually being saved
    """
    if created:
        Token.objects.create(user=instance)


@receiver(pre_delete, sender=BMGUser)
def unsubscribe_all(instance: BMGUser, **kwargs) -> None:
    """
    After deleting, remove all subscriptions associated with this user

    :param instance: User or BMGUser being deleted
    """
    client = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                          aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    sub_arns = unpack_json_field(instance.sub_arn)

    for sub_arn in sub_arns:
        unsubscribe_arn(client, sub_arn)


def apply_attr_update(instance: BMGUser) -> None:
    """
    The Contact Days field on the BMGUser object was changed so it needs to be updated in AWS

    :param instance: user holding subscriptions to update
    """
    sub_arns = unpack_json_field(instance.sub_arn)
    contact_days = unpack_json_field(instance.contact_days)

    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    for indx, sub_arn in enumerate(sub_arns):
        response = sns.get_subscription_attributes(SubscriptionArn=sub_arn)
        try:
            filter_policy = json.loads(response['Attributes']['FilterPolicy'])
        except KeyError:
            filter_policy = {'day_of_week': []}
        contact_method = response['Attributes']['Protocol']
        topic_arn = response['Attributes']['TopicArn']
        filter_policy_update = False

        # If the filter policy doesn't match, update it
        if filter_policy['day_of_week'] != contact_days and len(contact_days) > 0:
            filter_policy['day_of_week'] = contact_days
            filter_policy_update = True

        # If the contact_method doesn't match, update it
        if contact_method != instance.contact_method:
            # Delete the old subscription
            unsubscribe_arn(sns, sub_arn)
            # Create a new subscription
            if instance.contact_method == BMGUser.PHONE:
                endpt = instance.phone
            else:
                endpt = instance.user.email

            params = {'TopicArn': topic_arn, 'Protocol': instance.contact_method,
                      'ReturnSubscriptionArn': True, 'Endpoint': endpt}
            params['Attributes'] = {'FilterPolicy': json.dumps(filter_policy)}

            response = sns.subscribe(**params)
            logging.info(response)
            sub_arns[indx] = response['SubscriptionArn']
            continue

        elif filter_policy_update:
            # Update the filter policy
            sns.set_subscription_attributes(
                SubscriptionArn=sub_arns[indx],
                AttributeName='FilterPolicy',
                AttributeValue=json.dumps(filter_policy)
            )

    # Update sub_arn field
    if instance.sub_arn != json.dumps(sub_arns):
        instance.sub_arn = json.dumps(sub_arns)
        instance.save(update_fields=['sub_arn'])


@receiver(post_save, sender=BMGUser)
def update_subscription_attrs(instance: BMGUser, created: bool, update_fields: Union[None, FrozenSet[str]], **kwargs) \
        -> None:
    """
    For model updates -- Check if contact_days was updated; if so,
    update the subscription attributes on SNS. Also check if contact_method was changed.

    :param instance: BMGUser instance being saved
    :param created: True if a new record was created
    :param update_fields: Set of update field names passed to save or None if update_fields not given
    """
    if not created and (update_fields is None or list(update_fields) != ['sub_arn']):
        apply_attr_update(instance)


def update_resort_user_subs(instance: Union[BMGUser, Resort], action: str, reverse: bool, pk_set: Set[int]) -> None:
    """
    After changes to the m2m field between a resort and a user, update the links in AWS SNS

    :param instance: user or resort being changed
    :param action: type of update
    :param reverse: True if resort is being modified directly, else the BMGUser is being modified
    :param pk_set: set of primary keys being added or removed to the m2m field
    """
    # Instance -> BMGUser
    client = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                          aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
    logger = logging.getLogger(__name__)
    if action == 'post_add' and not reverse:
        sub_arns = subscribe_user_to_topic(instance, client)
        logger.debug('Updated sub_arn field for user {} with {}'.format(instance, json.dumps(sub_arns)))
        instance.sub_arn = json.dumps(sub_arns)
        instance.save()

    # Instance -> BMGUser
    elif action == 'pre_remove' and not reverse:
        for id in pk_set:
            resort = Resort.objects.get(pk=id)
            sub_arns = unsubscribe_user_to_topic(instance, client, resort)

            logger.debug('Updated sub_arn field for user {} with {}'.format(instance, json.dumps(sub_arns)))
            instance.sub_arn = json.dumps(sub_arns)
            instance.save()

    # Instance -> Resort
    elif action == 'post_add' and reverse:
        users = BMGUser.objects.filter(pk__in=pk_set)

        for user in users:
            sub_arns = subscribe_user_to_topic(user, client)
            logger.debug('Updated sub_arn field for user {} with {}'.format(instance, json.dumps(sub_arns)))
            user.sub_arn = json.dumps(sub_arns)
            user.save()

    # Instance -> Resort
    elif action == 'pre_remove' and reverse:
        users = BMGUser.objects.filter(pk__in=pk_set)

        for user in users:
            sub_arns = unsubscribe_user_to_topic(user, client, instance)
            logger.debug('Updated sub_arn field for user {} with {}'.format(instance, json.dumps(sub_arns)))
            user.sub_arn = json.dumps(sub_arns)
            user.save()


@receiver(m2m_changed, sender=BMGUser.resorts.through)
def subscribe_sns_topic(instance: Union[BMGUser, Resort], action: str, reverse: bool, pk_set: Set[int],
                        **kwargs) -> None:
    """
    Subscribe or unsubscribe the user to the relevant resort SNS topic, if resort added to their obj

    :param instance: BMGUser or Resort object being updated
    :param action: type of update on relation
    :param reverse: True if BMGUser is being modified directly; false if Resort object is being modified
    :param pk_set: set of primary keys being added or removed to the m2m field
    """
    update_resort_user_subs(instance, action, reverse, pk_set)

############################
### Supporting Functions ###
############################


def get_bm_runs(report: Report) -> List[Run]:
    """
    Extract the blue moon runs from the current report data, based on past data. Return the runs that were
    groomed today that have been groomed less than 90% of the past 7 days.

    :param report: Report object bm_runs are pulled from
    :return: list of blue moon run objects
    """
    # Get logger
    logger = logging.getLogger(__name__)

    # Get past reports for the last 7 days
    date = report.date
    resort = report.resort
    past_reports = Report.objects.filter(date__lt=date, date__gt=(date - dt.timedelta(days=8)),
                                         resort=resort)

    # If enough past reports, compare runs between reports and create BMReport
    bmreport_runs = []
    if len(past_reports) > 0:
        # Look at each run in today's report
        for run in report.runs.all():
            num_shared_reports = len(list(set(run.reports.all()).intersection(past_reports)))
            ratio = float(num_shared_reports) / float(len(past_reports))

            logger.debug('Run {} groomed {:.2%} over the last week'.format(run.name, ratio))
            if ratio < 0.2:
                bmreport_runs.append(run)

    return bmreport_runs


def subscribe_user_to_topic(instance: BMGUser, client: boto3.client) -> List[str]:
    """
    Subscribe a BMGUser to a topic

    :param instance: BMGUser instance
    :param client: boto3 sns client
    :return: list of subscription arns
    """
    if instance.contact_method == 'sms':
        endpt = instance.phone
    else:
        endpt = instance.user.email

    dow_arry = unpack_json_field(instance.contact_days)

    sub_arns = []
    logging.info(endpt)
    logging.info(instance.resorts.all())
    if endpt != '':
        for resort in instance.resorts.all():
            # Include attributes here to create filter policy
            params = {'TopicArn': resort.sns_arn, 'Protocol': instance.contact_method,
                      'ReturnSubscriptionArn': True, 'Endpoint': endpt}
            if len(dow_arry) > 0:
                params['Attributes'] = {'FilterPolicy': json.dumps({'day_of_week': dow_arry})}

            response = client.subscribe(**params)
            sub_arns.append(response['SubscriptionArn'])

    return sub_arns


def unsubscribe_arn(client: boto3.client, sub_arn: str) -> None:
    """
    Unsubscribe the specific arn

    :param client: boto3 sns client instance
    :param sub_arn: arn string
    """
    logger = logging.getLogger(__name__)
    try:
        resp = client.unsubscribe(SubscriptionArn=sub_arn)
        logger.info('Successfully unsubscribed, with status code {}'.format(resp['ResponseMetadata']
                                                                            ['HTTPStatusCode']))
    except Exception as e:
        logger.warning('Unable to unsubscribe user:\n {}'.format(e))


def unpack_json_field(json_str: str) -> List[str]:
    """
    Unpack a JSON string representation into an array

    :param json_str: raw string representation
    :return: Python array representation of string
    """
    try:
        list_obj = json.loads(json_str)
    except (TypeError, JSONDecodeError):
        list_obj = []

    return list_obj


def unsubscribe_user_to_topic(instance: BMGUser, client: boto3.client, resort: Resort) -> List[str]:
    """
    Unsubscribe a BMGUser to a topic

    :param instance: BMGUser instance
    :param client: boto3 sns client
    :param resort: resort instance that is being unsubscribed from
    :return: list of subscription arns with arn for removed resort removed
    """
    # Loop through subscription arns for user and delete the one that corresponds to this resort
    sub_arns = unpack_json_field(instance.sub_arn)

    resort_sub_arn = None
    for sub_arn in sub_arns:
        response = client.get_subscription_attributes(SubscriptionArn=sub_arn)
        if response['Attributes']['TopicArn'] == resort.sns_arn:
            resort_sub_arn = sub_arn
            unsubscribe_arn(client, sub_arn)
            break

    if resort_sub_arn is not None:
        sub_arns.remove(resort_sub_arn)

    return sub_arns
