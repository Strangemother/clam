from django.db import models
from trim.models import fields


class UserProfile(models.Model):
    user = fields.user_o2o()
    system_name = fields.chars(help_text='Your name, given to the bot. e.g "Lotty."')