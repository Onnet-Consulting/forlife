from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_warehouse_code(self, location):
        code = ''
        if location.code:
            code = location.code
        if location.warehouse_id and location.warehouse_id.code:
            code = location.warehouse_id.code
        return code

    @api.model_create_multi
    def create(self, vals):
        result = super(StockPicking, self).create(vals)
        sequence = 0
        for res in result:
            location_code = self._get_warehouse_code(res.location_id)
            location_des_code = self._get_warehouse_code(res.location_dest_id)
            if res.picking_type_id.code == 'incoming':
                declare_code = '015' # Nhap kho
            elif res.picking_type_id.code == 'outgoing':
                declare_code = '017' # Xuat kho
            else:
                declare_code = '020' # DC noi bo
            declare_code_id = self.env['declare.code']._get_declare_code(declare_code,res.company_id.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code(res.company_id.id,'stock.picking','name',sequence,location_code,location_des_code)
                sequence += 1
        return result

