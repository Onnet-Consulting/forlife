# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bkav_add_einvoice_stock = fields.Char(string='Mã tạo phiếu xuất kho', config_parameter='bkav.add_einvoice_stock')
