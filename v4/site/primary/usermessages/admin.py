from django.contrib import admin

from django.contrib import admin
from trim import admin as tadmin

from . import models

tadmin.register_models(models)
