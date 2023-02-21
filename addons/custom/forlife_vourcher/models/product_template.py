from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    vourcher = fields.Boolean('Vourcher')
    program_vourcher_id = fields.Many2one('program.vourcher')