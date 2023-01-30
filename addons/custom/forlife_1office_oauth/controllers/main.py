# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security
from odoo.tools import ustr
from odoo.tools.translate import _
from odoo.addons.web.controllers.utils import ensure_db
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.addons.web.controllers.home import ensure_db, Home, SIGN_UP_REQUEST_PARAMS, LOGIN_SUCCESSFUL_PARAMS

import base64
import functools
import json
import logging
import os
import re
import requests

import werkzeug.urls
import werkzeug.utils
from werkzeug.exceptions import BadRequest

from odoo import api, http, SUPERUSER_ID, _
from odoo.exceptions import AccessDenied
from odoo.http import request, Response
from odoo import registry as registry_get

_logger = logging.getLogger(__name__)


class Oauth1Office(Home):

    def authenticate_1office_user(self, username, password):
        payload = dict(username=username, userpwd=password)
        login_1office_url = 'https://forlife.1office.vn/login'
        response = requests.request("POST", login_1office_url, data=payload)
        response_text = response.text
        search_regex = re.compile(f"(?=username[\"\'\s:]+{username})")
        if not re.search(search_regex, response_text):
            raise odoo.exceptions.AccessDenied

    @http.route('/web/1office/login', type='http', auth="none")
    def web_1office_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        # simulate hybrid auth=user/auth=public, despite using auth=none to be able
        # to redirect users when no db is selected - cfr ensure_db()
        if request.env.uid is None:
            if request.session.uid is None:
                # no user -> auth=public with specific website public user
                request.env["ir.http"]._auth_method_public()
            else:
                # auth=user
                request.update_env(user=request.session.uid)

        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            username = values.get('login')
            password = values.get('password')
            try:
                self.authenticate_1office_user(username, password)
                user = request.env['res.users'].sudo().search([("login", "=", username)])
                if user:
                    # user with 'username' must be existed in Odoo before login by 1Office
                    uid = user.id
                    request.params['login_success'] = True
                    return request.redirect(self._login_redirect(uid, redirect=redirect))
                values['error'] = _("User %s not exist in Odoo") % username
            except odoo.exceptions.AccessDenied as e:
                values['error'] = _("Wrong login/password")

        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        response = request.render('forlife_1office_oauth.login_1office_layout', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
