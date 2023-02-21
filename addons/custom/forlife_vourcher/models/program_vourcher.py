from odoo import api, fields, models

Character = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


class ProgramVourcher(models.Model):
    _name = 'program.vourcher'
    _description = 'Program Vourcher for Forlife'

    name = fields.Char('Program Vourcher Name', required=True)

    program_vourcher_code = fields.Char('Vourcher Program Code', compute='_compute_code_vourcher', store=True)

    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Type', required=True)

    purpose_id = fields.Many2one('setup.vourcher', 'Purpose', required=True)

    derpartment_id = fields.Many2one('hr.department', 'Department Code', required=True)

    apply_many_times = fields.Boolean('Apply many times', default=False)

    apply_contemp_time = fields.Boolean('Áp dụng đồng thời')

    brand_id = fields.Many2one('res.brand','Brand', required=True)

    start_date = fields.Datetime('Start date', required=True)
    end_date = fields.Datetime('End date', required=True)

    store_id = fields.Many2one('store','Apply for store', required=True)

    product_id = fields.Many2one('product.template', 'Product Vourcher', required=True)

    program_vourcher_line_ids = fields.One2many('program.vourcher.line', 'program_vourcher_id', string='Vourcher')
    vourcher_ids = fields.One2many('vourcher.vourcher', 'program_vourcher_id')

    def create_vourcher(self):
        for rec in Character:
            print(rec)
        return True

    def _compute_code_vourcher(self):
        pass
