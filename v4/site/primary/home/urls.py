from trim.urls import paths_named
from . import views

app_name = 'home'

urlpatterns = [] + paths_named(views,
    index=('IndexView', '',),
)
