from functools import wraps
from odoo.http import request


def with_server_lang(default='fr_FR'):
    def set_lang(func):
        @wraps(func)
        def lang_wrapper(*args, **kwargs):
            user = request.env.user
            user_lang = user.lang or default

            request.update_context(lang=user_lang)

            return func(*args, **kwargs)
        return lang_wrapper
    return set_lang
