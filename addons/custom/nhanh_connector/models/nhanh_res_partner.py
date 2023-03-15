from odoo.addons.nhanh_connector.models import constant
from odoo import _, models, fields, api
from odoo.exceptions import ValidationError
import datetime, logging
import requests


class CustomerNhanh(models.Model):
    _inherit = 'res.partner'

    customer_nhanh_id = fields.Integer(string="Id khách hàng bên Nhanh.vn")
    source_record = fields.Boolean(string="From nhanh", default=False)