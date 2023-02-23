from odoo import api, fields, models, _
import traceback

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _cron_noti_pos_not_closed(self):
        cron = self.env.ref('forlife_point_of_sale.noti_pos_not_closed')
        domain = []
        self.send_noti_pos_not_closed()

    def send_noti_pos_not_closed(self):
        try:
            query = '''SELECT ps.id FROM pos_session ps WHERE ps.state = 'opened' '''
            self.env.cr.execute(query, ())
            data = self.env.cr.fetchall()
            template = self.env.ref('forlife_point_of_sale.mail_template_warning_opened_pos')
            for ps in data:
                template.send_mail(
                    ps[0],
                    force_send=True,
                    raise_exception=False,
                )
        except Exception as e:
            error = traceback.format_exc()
            self.env['ir.logging'].sudo().create({
                'type': 'server',
                'name': 'send_noti_pos_not_closed',
                'path': 'path',
                'line': 'line',
                'func': 'send_noti_pos_not_closed',
                'message': str(error)
            })