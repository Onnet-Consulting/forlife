from odoo import fields, models

class DeclareCategory(models.Model):
    _name = 'declare.category'
    _description = 'Declare Documents code category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Tên', required=True,tracking=True)
    code = fields.Char('Mã', required=True,tracking=True)
    description = fields.Text('Mô tả',tracking=True)