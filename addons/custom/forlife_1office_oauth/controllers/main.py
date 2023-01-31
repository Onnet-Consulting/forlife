# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.web.controllers.home import ensure_db, Home, SIGN_UP_REQUEST_PARAMS
from odoo import http
from odoo.exceptions import AccessDenied, MissingError
from odoo.http import request


class Oauth1Office(Home):

    @http.route('/web/login/1office', type='http', auth="none")
    def web_login_1office(self, redirect=None, **kw):
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
        except AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            username = values.get('login')
            password = values.get('password')
            try:
                db, login, key = request.env['res.users'].sudo().auth_1office(username, password)
                uid = request.session.authenticate(db, login, key)
                request.params['login_success'] = True
                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except AccessDenied as access_denied_message:
                values['error'] = str(access_denied_message)
            except MissingError as missing_message:
                values['error'] = str(missing_message)

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        response = request.render('forlife_1office_oauth.login_1office_layout', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
