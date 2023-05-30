from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class SplitProduct(models.Model):
    _name = 'split.product'
    _description = 'Nghiệp vụ phân tách mã'

    user_create_id = fields.Many2one('res.users', 'Người tạo', default=lambda self: self.env.user, readonly=True)
    date_create = fields.Datetime('Ngày tạo', readonly=True, default=lambda self: fields.datetime.now())
    user_approve_id = fields.Many2one('res.users', 'Người xác nhận', readonly=True)
    date_approved = fields.Datetime('Ngày xác nhận', readonly=True)
    state = fields.Selection([('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done'), ('canceled', 'Canceled')],
                             default='new',
                             string='Trạng thái')
    split_product_line_ids = fields.One2many('split.product.line', 'split_product_id', string='Sản phẩm chính')
    split_product_line_sub_ids = fields.One2many('split.product.line.sub', 'split_product_id', string='Sản phẩm phân rã')
    note = fields.Text()
    account_intermediary_id = fields.Many2one('account.account', 'Tài khoản trung gian')

    # @api.model
    # def create(self, vals_list):
    # if 'split_product_line_ids' in vals_list and not vals_list['split_product_line_ids']:
    #     raise ValidationError(_('Vui lòng thêm một dòng sản phẩm chính!'))
    # return super(SplitProduct, self).create(vals_list)

    def action_generate(self):
        self.ensure_one()
        vals_list = []
        for rec in self.split_product_line_ids:
            if rec.product_id.id not in self.split_product_line_sub_ids.product_id.ids:
                for r in range(rec.product_quantity_split):
                    vals_list.append({
                        'split_product_id': self.id,
                        'product_id': rec.product_id.id,
                        'warehouse_in_id': rec.warehouse_in_id.id,
                        'quantity': 1,
                        'product_uom_split': rec.product_uom_split.id,
                    })
        self.env['split.product.line.sub'].create(vals_list)
        self.state = 'in_progress'

    def _create_product(self, rec):
        vals = {
            'name': rec.product_split,
            'detailed_type': rec.product_id.detailed_type,
            'product_type': rec.product_id.product_type,
            'invoice_policy': rec.product_id.invoice_policy,
            'uom_id': rec.product_id.uom_id.id,
            'uom_po_id': rec.product_id.uom_po_id.id,
            'taxes_id': [(6, 0, rec.product_id.taxes_id.ids)],
            'categ_id': rec.product_id.categ_id.id,
            'split_product_id': self.id
        }

        product = self.env['product.product'].create(vals)
        return product


    def action_approve(self):
        self.ensure_one()
        for rec in self.split_product_line_ids:
            for r in self.split_product_line_sub_ids:
                if r.product_id == rec.product_id:
                    rec.product_quantity_out += r.quantity
                product = self._create_product(r)
                r.product_new_id = product.id
        company_id = self.env.company
        pk_type = self.env['stock.picking.type'].sudo().search(
            [('company_id', '=', company_id.id), ('code', '=', 'internal')], limit=1)
        self.create_orther_import(pk_type, company_id)
        # self.create_orther_export(pk_type)
        self.state = 'done'


    def action_view_picking(self):
        self.ensure_one()
        ctx = dict(self._context)
        ctx.update({
            'default_split_product_id': self.id,
        })
        return {
            'name': _('Phiếp nhập'),
            'domain': [('split_product_id', '=', self.id)],
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': ctx,
        }

    def action_cancel(self):
        self.ensure_one()
        self.state = 'canceled'

    def action_draft(self):
        self.ensure_one()
        self.state = 'new'

    def create_orther_import(self, pk_type, company):
        pickings = self.env['stock.picking']
        for record in self.split_product_line_ids:
            data = []
            for rec in self.split_product_line_sub_ids:
                if rec.product_id.id == record.product_id.id:
                    data.append((0, 0, {
                        'product_id': rec.product_new_id.id,
                        'name': rec.product_split,
                        'date': datetime.now(),
                        'product_uom': rec.product_uom_split.id,
                        'product_uom_qty': rec.quantity,
                        'quantity_done': rec.quantity,
                        'location_id': self.env.ref('forlife_splip_product.import_product_division').id,
                        'location_dest_id': rec.warehouse_in_id.lot_stock_id.id
                    }))
            pickings |= self.env['stock.picking'].with_company(company).create({
                'other_import': True,
                'picking_type_id': pk_type.id,
                'location_id': self.env.ref('forlife_splip_product.import_product_division').id,
                'location_dest_id': record.warehouse_in_id.lot_stock_id.id,
                'split_product_id': self.id,
                'move_ids_without_package': data
            })
        for pick in pickings:
            pick.button_validate()
        # picking.button_validate()
        # return picking


    def create_orther_export(self, pk_type):
        # data = []
        # for rec in self.split_product_line_ids:
        #     data.append((0, 0, {
        #         'product_id': rec.product_id.id,
        #         'name': rec.product_id.name_get()[0][1],
        #         'date': datetime.now(),
        #         'product_uom': rec.product_uom.id,
        #         'product_uom_qty': rec.product_quantity_out,
        #         'quantity_done': rec.product_quantity_out,
        #         'location_id': self.split_product_line_ids[0].warehouse_out_id.lot_stock_id.id,
        #         'location_dest_id': self.env.ref('forlife_splip_product.export_product_division').id,
        #     }))
        # picking = self.env['stock.picking'].create({
        #     'other_export': True,
        #     'picking_type_id': pk_type.id,
        #     'location_id': self.split_product_line_ids[0].warehouse_out_id.lot_stock_id.id,
        #     'location_dest_id': self.env.ref('forlife_splip_product.export_product_division').id,
        #     'split_product_id': self.id,
        #     'move_ids_without_package': data
        # })
        # picking.button_validate()
        # return picking


class SpilitProductLine(models.Model):
    _name = 'split.product.line'
    _description = 'Dòng sản phẩm chính'

    split_product_id = fields.Many2one('split.product')
    state = fields.Selection(
        [('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done'), ('canceled', 'Canceled')],
        related='split_product_id.state',
        string='Trạng thái')
    product_id = fields.Many2one('product.product', 'Sản phẩm chính', required=True)
    product_uom = fields.Many2one('uom.uom', 'Đơn vị tính', related='product_id.uom_id')
    warehouse_out_id = fields.Many2one('stock.warehouse', 'Kho xuất', required=True)
    product_quantity_out = fields.Integer('Số lượng xuất', readonly=True)
    product_quantity_split = fields.Integer('Số lượng phân tách', required=True)
    product_uom_split = fields.Many2one('uom.uom', 'DVT SL phân tách', required=True, related='product_id.uom_id')
    warehouse_in_id = fields.Many2one('stock.warehouse', 'Kho nhập', required=True)
    unit_price = fields.Float('Đơn giá', readonly=True)
    value = fields.Float('Giá trị', readonly=True)


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

    state = fields.Selection(
        [('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done'), ('canceled', 'Canceled')],
        related='split_product_id.state',
        string='Trạng thái')
    split_product_id = fields.Many2one('split.product')
    product_id = fields.Many2one('product.product', 'Sản phẩm chính', readonly=True, required=True)
    product_new_id = fields.Many2one('product.product', readonly=True)
    product_split = fields.Char('Sản phẩm phân tách', default="New", readonly=True, required=True)
    warehouse_in_id = fields.Many2one('stock.warehouse', 'Kho nhập', readonly=True, required=True)
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
