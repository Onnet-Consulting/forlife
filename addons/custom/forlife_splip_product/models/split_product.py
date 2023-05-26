from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class Purchase(models.Model):
    _name = 'split.product'
    _description = 'Nghiệp vụ phân tách mã'

    user_create_id = fields.Many2one('res.users', 'Người tạo', default=lambda self: self.env.user, readonly=True)
    date_create = fields.Datetime('Ngày tạo', readonly=True, default=lambda self: fields.datetime.now())
    user_approve_id = fields.Many2one('res.users', 'Người xác nhận', readonly=True)
    date_approved = fields.Datetime('Ngày xác nhận', readonly=True)
    state = fields.Selection([('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done'),('canceled','Canceled')],
                             default='new',
                             string='Trạng thái')
    split_product_line_ids = fields.One2many('split.product.line','split_product_id', string='Sản phẩm chính')
    split_product_line_sub_ids = fields.One2many('split.product.line.sub','split_product_id', string='Sản phẩm phân rã')
    note = fields.Text()
    account_intermediary_id = fields.Many2one('account.account', 'Tài khoản trung gian')

    @api.model
    def create(self, vals_list):
        if 'split_product_line_ids' in vals_list and not vals_list['split_product_line_ids']:
            raise ValidationError(_('Vui lòng thêm một dòng sản phẩm chính!'))
        return super(Purchase, self).create(vals_list)

    def action_generate(self):
        vals_list = []
        for rec in self.split_product_line_ids:
            for r in range(rec.product_quantity_split):
                vals_list.append({
                    'split_product_id': self.id,
                    'product_id': rec.product_id.id,
                    'warehouse_in_id':rec.warehouse_in_id.id,
                    'quantity': 1,
                    'product_uom_split': rec.product_uom_split.id,
                })
        self.env['split.product.line.sub'].create(vals_list)
        self.state = 'in_progress'

    def action_approve(self):
        print(2)

    def action_cancel(self):
        print(3)

    def action_draft(self):
        print(4)



class SpilitProductLine(models.Model):
    _name = 'split.product.line'
    _description = 'Dòng sản phẩm chính'

    split_product_id = fields.Many2one('split.product')
    product_id = fields.Many2one('product.product','Sản phẩm chính', required=True)
    product_uom = fields.Many2one('uom.uom', 'Đơn vị tính', required=True)
    warehouse_out_id = fields.Many2one('stock.warehouse', 'Kho xuất',required=True)
    product_quantity_out = fields.Integer('Số lượng xuất', readonly=True)
    product_quantity_split = fields.Integer('Số lượng phân tách', required=True)
    product_uom_split = fields.Many2one('uom.uom', 'DVT SL phân tách', required=True)
    warehouse_in_id = fields.Many2one('stock.warehouse', 'Kho nhập', required=True)
    unit_price = fields.Float('Đơn giá', readonly=True)
    value = fields.Float('Giá trị', compute='_compute_value_price', readonly=True, store=True)

    @api.depends('unit_price')
    def _compute_value_price(self):
        for rec in self:
            rec.value = 9


class SpilitProductLineSub(models.Model):
    _name = 'split.product.line.sub'
    _description = 'Dòng sản phẩm phân rã'



    @api.model
    def create(self, vals_list):
        res = super(SpilitProductLineSub, self).create(vals_list)
        if res.product_split == 'New':
            sequence = self.env['ir.sequence'].next_by_code('split.product.line.sub')
            res.product_split = f"{res.product_id.name_get()[0][1]} {sequence}"
        return res

    split_product_id = fields.Many2one('split.product')
    product_id = fields.Many2one('product.product', 'Sản phẩm chính', readonly=True,required=True)
    product_split = fields.Char('Sản phẩm phân tách', default="New", readonly=True,required=True)
    warehouse_in_id = fields.Many2one('stock.warehouse', 'Kho nhập', readonly=True,required=True)
    quantity = fields.Integer('Số lượng', required=True)
    product_uom_split = fields.Many2one('uom.uom', 'DVT SL phân tách', readonly=True)
    unit_price = fields.Float('Đơn giá', readonly=True)
    value = fields.Float('Giá trị', readonly=True)

    @api.constrains('quantity')
    def constrains_quantity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_('Không được phép nhập giá trị âm!'))

# class AccountIntermediary

