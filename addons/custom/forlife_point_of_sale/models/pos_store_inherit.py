from odoo import api, fields, models, _
import traceback

class PosStoreInherit(models.Model):
    _inherit = 'store'

    def _cron_noti_pos_not_closed(self):
        cron = self.env.ref('forlife_point_of_sale.noti_pos_not_closed')
        self.send_noti_pos_not_closed(cron.mail_template_id)

    def get_pos_opened(self):
        pos_sessions = self.env['pos.session'].sudo().search([('state', '!=', 'closed'), ('config_id.store_id', '=', self.id)])
        return pos_sessions

    def send_noti_pos_not_closed(self, template):
        try:
            query = ''' SELECT s.id as sid FROM store s LEFT JOIN pos_config pc ON pc.store_id = s.id LEFT JOIN pos_session ps ON ps.config_id = pc.id WHERE ps.state != 'closed' group by sid '''
            self.env.cr.execute(query, ())
            data = self.env.cr.fetchall()
            for s in data:
                template.send_mail(
                    s[0],
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
