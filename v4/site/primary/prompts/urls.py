from trim.urls import paths_named
from . import views

app_name = 'prompts'

urlpatterns = [] + paths_named(views,
    list=('SystemPromptListView', '',),
    detail=('SystemPromptDetailView', 'p/<slug:slug>/',),
    index=('IndexView', '<path:path>/',),
)
