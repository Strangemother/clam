from django.shortcuts import render

from trim import views

from . import models


class IndexView(views.TemplateView):
    template_name = 'prompts/index.html'


class SystemPromptListView(views.ListView):
    model = models.SystemPrompt


class SystemPromptDetailView(views.DetailView):
    model = models.SystemPrompt