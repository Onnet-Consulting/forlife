from odoo import fields, api, models, _


class ContractType(models.Model):
    _name = 'contract.type'
    _description = 'Loại hợp đồng'

    type = fields.Char(string='Loại hợp đồng')
    description = fields.Text(string='Mô tả')