from odoo import api, fields, models


class OdooAppLogging(models.AbstractModel):
    _name = 'odoo.app.logging'
    _description = 'Odoo App Logging'

    def open_logging_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('base.ir_logging_all_act')
        action['domain'] = [('name', '=', self._name), ('line', 'in', [str(x.id) for x in self])]
        return action

