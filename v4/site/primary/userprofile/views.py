from trim import views
from django.views.generic.base import RedirectView


class LoginView(views.LoginView):
    pass

class LogoutView(views.LogoutView):
    pass


class AccountView(views.DetailView):
    # template_name = 'userprofile/user_detail.html'

    def get_object(self, queryset=None):
        return self.request.user


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = "userprofile:account"

    def get_redirect_url(self, *args, **kwargs):
        # article = get_object_or_404(Article, pk=kwargs["pk"])
        # article.update_counter()
        # return super().get_redirect_url(*args, **kwargs)
        if self.request.user.is_anonymous:
            url = views.reverse('userprofile:login', args=args, kwargs=kwargs)
            return url
        return super().get_redirect_url(*args, **kwargs)
