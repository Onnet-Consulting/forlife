from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    price = fields.Float(string='Price', digits='Product Price')
    notification_id = fields.Char('Notification ID', help='Id của thông báo trên trang quản trị app, được thiết lập trước khi bán voucher trên POS,'
                                                          ' dùng cho nghiệp vụ đẩy thông báo thông tin voucher cho khách hàng.')
