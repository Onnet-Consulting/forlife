import base64
import urllib
from odoo.addons.nhanh_connector.models import constant
from odoo import _, models, fields, api
from odoo.exceptions import ValidationError
import datetime, logging
import requests

_logger = logging.getLogger(__name__)


class ProductCategoryNhanh(models.Model):
    _inherit = 'product.category'

    nhanh_product_category_id = fields.Integer(string="Id Category From Nhanh.Vn")
    code_category = fields.Char(string="Code Category")
    content_category = fields.Text(string="Content Category")
    nhanh_parent_id = fields.Integer('Parent Category')

