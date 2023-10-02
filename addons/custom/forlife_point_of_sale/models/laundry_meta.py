from odoo import fields, api, models


class LaundryProductStatus(models.Model):
    _name = 'laundry.product.status'
    _description = 'Tình trạng sản phẩm'

    name = fields.Char(string='Tình trạng')


class LaundryService(models.Model):
    _name = 'laundry.service'
    _description = 'Dịch vụ sửa đồ'

    name = fields.Char(string='Dịch vụ sửa đồ')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', related='company_id.currency_id')
    amount = fields.Monetary(string='Chi phí', currency_field='currency_id')


class LaundryStatusRepair(models.Model):
    _name = 'laundry.repair.status'
    _description = 'Tình trạng sửa chữa'

    name = fields.Char(string='Tình trạng sửa chữa')
    rank = fields.Integer(string='Thứ hạng', compute='compute_rank', store=True)
    refund = fields.Boolean(string='Hoàn tiền')

    @api.depends('name')
    def compute_rank(self):
        for rec in self:
            last_rank = self.search([], limit=1, order='rank desc').rank
            rec.rank = last_rank and last_rank + 1 or 1

