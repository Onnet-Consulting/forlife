from odoo import api, fields, models
import logging
from datetime import datetime, timedelta

from odoo import SUPERUSER_ID
from odoo import fields, api
from odoo import models
from odoo.exceptions import AccessDenied
from odoo.http import request
from ..controllers.main import clear_session_history
import pytz

_logger = logging.getLogger(__name__)
# The duration of a user session before it is considered expired,
# three months. (hours)
SESSION_LIFETIME = 24 * 90


class ResUsers(models.Model):
    _inherit = "res.users"

    restrict_login_only_1_browser = fields.Boolean(string="Restrict login only for 1 browser", default=True, help="If you want restrict this user login multiple browser")
    session_life_time = fields.Integer(string="Session life time (hours)", default=SESSION_LIFETIME, help="Time every session expired, Default 3 months")
    sid = fields.Char('Session ID')
    exp_date = fields.Datetime('Expiry Date')
    last_update = fields.Datetime(string="Last Connection Updated")

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth(user=login):
                    user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._check_credentials(password, user_agent_env)
                    # check sid and exp date
                    if user.restrict_login_only_1_browser:
                        if user.exp_date and user.sid and (user.sid != request.session.sid):
                            _logger.warning("User %s is already logged in "
                                            "into the system!. Multiple "
                                            "sessions are not allowed for "
                                            "security reasons!" % user.name)
                            request.update_env(user=user.id)
                            raise AccessDenied("already_logged_in")
                            # save user session detail if login success
                        user._save_session()
                    tz = request.httprequest.cookies.get('tz') if request else None
                    if tz in pytz.all_timezones and (not user.tz or not user.login_date):
                        # first login or missing tz -> set tz to browser tz
                        user.tz = tz
                    user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s from %s", db, login, ip)
            raise

        _logger.info("Login successful for db:%s login:%s from %s", db, login, ip)

        return user.id

    def _save_session(self):
        """
            Function for saving session details to corresponding user
        """
        exp_date = datetime.now() + timedelta(hours=self.session_life_time if self.session_life_time else SESSION_LIFETIME)
        sid = request.session.sid
        self.with_user(SUPERUSER_ID).write({'sid': sid, 'exp_date': exp_date, 'last_update': datetime.now()})

    def _clear_session(self):
        """
            Function for clearing the session details for user
        """
        self.write({'sid': False, 'exp_date': False, 'last_update': datetime.now()})

    def _validate_sessions(self):
        """
            Function for validating user sessions
        """
        users = self.search([('exp_date', '!=', False)])
        for user in users:
            if user.exp_date < datetime.now():
                # clear session file for the user
                session_cleared = clear_session_history(user.sid)
                if session_cleared:
                    # clear user session
                    user._clear_session()
                    _logger.info("Cron _validate_session: "
                                 "cleared session user: %s" % (user.name))
                else:
                    _logger.info("Cron _validate_session: failed to "
                                 "clear session user: %s" % (user.name))
