from trim.urls import paths_named
from . import views

app_name = 'userprofile'

urlpatterns = [] + paths_named(views,
    login=('LoginView', 'login/',),
    logout=('LogoutView', 'logout/',),
    account=('AccountView', 'account/',),
    index=('IndexRedirectView', '',),
)
