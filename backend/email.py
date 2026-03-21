from djoser.email import PasswordResetEmail

class MobilePasswordResetEmail(PasswordResetEmail):
    template_name = "email/password_reset.html"

    def get_context_data(self):
        context = super().get_context_data()
        user = context.get("user")
        context["uid"] = context.get("uid")
        context["token"] = context.get("token")
        context["reset_link"] = f"seraprime://reset-password-confirm/{context['uid']}/{context['token']}"
        context["user"] = user
        return context