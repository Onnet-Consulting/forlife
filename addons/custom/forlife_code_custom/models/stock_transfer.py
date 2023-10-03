from odoo import api, fields, models, _


class StockTransfer(models.Model):
    _inherit = 'stock.transfer'

    def _get_warehouse_code(self, location):
        code = ''
        if location.code:
            code = location.code
        if location.warehouse_id and location.warehouse_id.code:
            code = location.warehouse_id.code
        return code

    @api.model_create_multi
    def create(self, vals):
        result = super(StockTransfer, self).create(vals)
        sequence = 0
        for res in result:
            location_code = self._get_warehouse_code(res.location_id)
            location_des_code = self._get_warehouse_code(res.location_dest_id)
            declare_code_id = self.env['declare.code']._get_declare_code('019', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'stock_transfer','name',sequence,location_code,location_des_code)
                sequence += 1
        return result

