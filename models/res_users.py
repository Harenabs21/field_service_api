from odoo import models, fields
import datetime
import secrets


class ResUsers(models.Model):

    _inherit = 'res.users'
    access_token = fields.Char(string="Access token", readonly=True)
    token_expiry = fields.Datetime(string="Token Expiry", readonly=True)
    
    def generate_access_token(self):
        token = secrets.token_urlsafe(32)
        expiry = datetime.datetime.now() + datetime.timedelta(hours=24)
        
        self.sudo().write({
            'access_token': token,
            'token_expiry': expiry
        })
        
        return token
    
    def check_token_validity(self, token):
        if not token or not self.access_token:
            return False
      
        if (
            self.access_token == token and
            self.token_expiry and
            self.token_expiry > datetime.datetime.now()
        ):
            return True
        
        return False

    def reset_token(self):
        self.sudo().write({
            'access_token': False,
            'token_expiry': False
        })
