from odoo import api, fields, models

class DefectiveType(models.Model):
    _inherit = 'defective.type'

    def _get_team_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.team_default_id

    team_id = fields.Many2one('hr.team', string='Team', default=_get_team_default)