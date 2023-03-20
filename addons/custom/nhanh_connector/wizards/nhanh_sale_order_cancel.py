from odoo import _, api, fields, models
from odoo.addons.nhanh_connector.models import constant

class NhanhSaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'