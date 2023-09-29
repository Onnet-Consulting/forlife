from odoo import api, fields, models, _

class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model_create_multi
    def create(self, vals):
        result = super(PosOrder, self).create(vals)
        sequence = 0
        for res in result:
            location_code = res.store_id.warehouse_id.code or ''
            location_des_code = res.store_id.warehouse_id.code or ''
            if not res.is_refund_order and not res.is_change_order:
                declare_code = '006' # DH ban
            else:
                declare_code = '011' # DH doi tra
            declare_code_id = self.env['declare.code']._get_declare_code(declare_code, self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code('pos_order','name',sequence,location_code,location_des_code)
                sequence += 1
        return result

