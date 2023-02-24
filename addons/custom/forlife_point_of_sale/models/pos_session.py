from odoo import api, fields, models, _
import traceback

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _cron_noti_pos_not_closed(self):
        cron = self.env.ref('forlife_point_of_sale.noti_pos_not_closed')
        self.send_noti_pos_not_closed(cron.mail_template_id)

    def send_noti_pos_not_closed(self, template):
        try:
            query = '''SELECT ps.id FROM pos_session ps WHERE ps.state = 'opened' '''
            self.env.cr.execute(query, ())
            data = self.env.cr.fetchall()
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