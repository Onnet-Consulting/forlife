import os
import odoo.modules.registry
from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError
import logging
import odoo
import odoo.modules.registry
from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.web.controllers.home import ensure_db, Home
from odoo.http import FilesystemSessionStore
from odoo.http import Session

_logger = logging.getLogger(__name__)
SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}
LOGIN_SUCCESSFUL_PARAMS = set()


def clear_session_history(u_sid, f_uid=False):
    """ Clear all the user session histories for a particular user """
    path = odoo.tools.config.session_dir
    store = FilesystemSessionStore(
        path, session_class=Session, renew_missing=True)
    session_fname = store.get_session_filename(u_sid)
    try:
        os.unlink(session_fname)
        return True
    except OSError:
        pass
    return False


def super_clear_all():
    """ Clear all the user session histories """
    path = odoo.tools.config.session_dir
    store = FilesystemSessionStore(
        path, session_class=Session, renew_missing=True)
    for fname in os.listdir(store.path):
        path = os.path.join(store.path, fname)
        try:
            os.unlink(path)
        except OSError:
            pass
    return True


class RestrictLoginsSession(http.Controller):

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        user = request.env['res.users'].with_user(1).search(
            [('id', '=', request.session.uid)])
        # clear user session
        user._clear_session()
        request.session.logout(keep_db=True)
        return request.redirect(redirect, 303)

    @http.route('/clear_all_sessions', type='http', auth="none")
    def logout_all(self, redirect='/web', f_uid=False):
        """ Log out from all the sessions of the current user """
        if f_uid:
            user = request.env['res.users'].with_user(1).browse(int(f_uid))
            if user:
                # clear session file for the user
                clear_session_history(user.sid, f_uid)
                # clear user session
                user._clear_session()
        request.session.logout(keep_db=True)

        return request.redirect(redirect, 303)

    # @http.route('/super/logout_all', type='http', auth="none")
    # def super_logout_all(self, redirect='/web'):
    #     """ Log out from all the sessions of all the users """
    #     users = request.env['res.users'].with_user(1).search([])
    #     for user in users:
    #         # clear session file for all users
    #         session_cleared = super_clear_all()
    #         if session_cleared:
    #             # clear user session
    #             user._clear_session()
    #     request.session.logout(keep_db=True)
    #     return request.redirect(redirect, 303)


class RestrictLoginHome(Home):

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
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
            try:
                uid = request.session.authenticate(request.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                failed_uid = request.uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                elif e.args[0] == "already_logged_in":
                    values['error'] = "User already logged in. Log out from " \
                                      "other devices and try again."
                    values['logout_all'] = True
                    values['failed_uid'] = failed_uid if failed_uid != SUPERUSER_ID else False
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True
        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
