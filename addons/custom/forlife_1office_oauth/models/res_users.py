# -*- coding:utf-8 -*-

import re
import requests
from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, MissingError
from odoo.http import request


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _auth_signin_1office_user(self, username):
        user = self
        auth_1office_provider = False
        try:
            user = self.sudo().search([("login", "=", username)])
            auth_1office_provider = self.env.ref('forlife_1office_oauth.provider_1office', raise_if_not_found=False)
            if not user:
                raise MissingError(_("User %s does not exist in Odoo") % username)
            if not auth_1office_provider:
                raise MissingError(_("Missing 1Office Auth provider, please contact to Administrator!"))
            if user.oauth_provider_id != auth_1office_provider and user.oauth_uid != username:
                raise AccessDenied()
        except AccessDenied:
            pass
        # if created user don't related to 1office yet => update 1office info to user
        if not user.oauth_provider_id and auth_1office_provider:
            user.write({'oauth_provider_id': auth_1office_provider.id, 'oauth_uid': username})

    @api.model
    def _auth_validate_1office_user(self, username, password):
        payload = dict(username=username, userpwd=password)
        login_1office_url = 'https://forlife.1office.vn/login'
        response = requests.request("POST", login_1office_url, data=payload)
        response_text = response.text
        search_regex = re.compile(f"(?=username[\"\'\s:]+{username})")
        if not re.search(search_regex, response_text):
            return False
        return username

    @api.model
    def auth_1office(self, username, password):
        valid_1office_user = self._auth_validate_1office_user(username, password)
        if not valid_1office_user:
            raise AccessDenied(_("Wrong login/password"))
        self._auth_signin_1office_user(username)
        return self.env.cr.dbname, username, 'dummy-password'  # don't need a valid password here

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        try:
            if '/web/login/1office' in request.httprequest.full_path:
                user_agent_env.update({'auth_1office': True})
        except Exception:
            pass
        return super(ResUsers, cls)._login(db, login, password, user_agent_env=user_agent_env)

    def _check_credentials(self, password, env):
        try:
            return super(ResUsers, self)._check_credentials(password, env)
        except AccessDenied:
            user = self.env.user
            auth_1office_provider = self.env.ref('forlife_1office_oauth.provider_1office')
            auth_1office = env.pop('auth_1office', False)
            if auth_1office and user.active and \
                    user.oauth_uid == user.login and user.oauth_provider_id == auth_1office_provider:
                return
            raise
