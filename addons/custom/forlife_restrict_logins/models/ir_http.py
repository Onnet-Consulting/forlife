import logging
from datetime import datetime, timedelta
from odoo.service import security
from odoo import models, http, SUPERUSER_ID
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo import api, models
import werkzeug
import werkzeug.exceptions

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        auth = 'none' if http.is_cors_preflight(request, endpoint) else endpoint.routing['auth']
        try:
            if request.session.uid:
                uid = request.session.uid
                user_pool = request.env['res.users'].with_user(
                    SUPERUSER_ID).browse(uid)
                if user_pool.restrict_login_only_1_browser:
                    sid = request.session.sid
                    if user_pool and user_pool.sid != request.session.sid:
                        def _update_user(u_sid, u_now, u_exp_date, u_uid):
                            """ Function for updating session details for the
                                corresponding user
                            """
                            if u_uid and u_exp_date and u_sid and u_now:
                                query = """update res_users set sid = '%s',
                                               last_update = '%s',exp_date = '%s' where id = %s
                                               """ % (u_sid, u_now, u_exp_date, u_uid)
                                request.env.cr.execute(query)

                        # last_update = user_pool.last_update
                        now = datetime.now()
                        exp_date = datetime.now() + timedelta(hours=user_pool.session_life_time if user_pool.session_life_time else 2160)
                        # update session for user when have change session or mismatch with current session
                        if not user_pool.sid or (user_pool.sid != sid):
                            _update_user(sid, now, exp_date, uid)
        except Exception as e:
            _logger.info("Exception during updating user session...%s", e)
            pass

        try:
            if request.session.uid is not None:
                if not security.check_session(request.session, request.env):
                    request.session.logout(keep_db=True)
                    request.env = api.Environment(request.env.cr, None, request.session.context)
            getattr(cls, f'_auth_method_{auth}')()
        except (AccessDenied, http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise AccessDenied()
