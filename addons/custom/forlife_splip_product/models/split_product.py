from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class SplitProduct(models.Model):
    _name = 'split.product'
    _description = 'Nghiệp vụ phân tách mã'

    name = fields.Char(default='New')

    user_create_id = fields.Many2one('res.users', 'Người tạo', default=lambda self: self.env.user, readonly=True)
    date_create = fields.Datetime('Ngày tạo', readonly=True, default=lambda self: fields.datetime.now())
    user_approve_id = fields.Many2one('res.users', 'Người xác nhận', readonly=True)
    date_approved = fields.Datetime('Ngày xác nhận', readonly=True)
    state = fields.Selection([('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done'), ('canceled', 'Canceled')],
                             default='new',
                             string='Trạng thái')
    split_product_line_ids = fields.One2many('split.product.line', 'split_product_id', string='Sản phẩm chính', copy=True)
    split_product_line_sub_ids = fields.One2many('split.product.line.sub', 'split_product_id', string='Sản phẩm phân rã')
    note = fields.Text()
    count_picking = fields.Integer(compute='compute_count_picking', string='Các phiếu nhập xuất')

    def compute_count_picking(self):
        for rec in self:
            pickings = self.env['stock.picking'].sudo().search_count([('split_product_id','=',rec.id)])
            rec.count_picking = pickings

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            vals_list['name'] = self.env['ir.sequence'].next_by_code('split.product.line.sub.name') or 'New'
        res = super(SplitProduct, self).create(vals_list)
        return res
    # @api.model
    # def create(self, vals_list):
    # if 'split_product_line_ids' in vals_list and not vals_list['split_product_line_ids']:
    #     raise ValidationError(_('Vui lòng thêm một dòng sản phẩm chính!'))
    # return super(SplitProduct, self).create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state == 'new':
                return super().unlink()
        raise ValidationError(_('Chỉ được xoá phiếu ở trạng thái Mới!'))

    def action_generate(self):
        self.ensure_one()
        vals_list = []
        if self.split_product_line_sub_ids:
            self.split_product_line_sub_ids = False
        for rec in self.split_product_line_ids:
            for r in range(rec.product_quantity_split):
                vals_list.append({
                    'split_product_id': self.id,
                    'product_id': rec.product_id.id,
                    'warehouse_in_id': rec.warehouse_in_id.id,
                    'quantity': 1,
                    # 'product_uom_split': rec.product_uom_split.id,
                    'parent_id': rec.id
                })
        self.env['split.product.line.sub'].create(vals_list)
        self.state = 'in_progress'



    def action_approve(self):
        self.ensure_one()
        Quant = self.env['stock.quant']
        list_line_invalid = []
        for rec in self.split_product_line_ids:
            product_qty_split = 0
            for r in self.split_product_line_sub_ids:
                if r.product_id == rec.product_id and r.parent_id.id == rec.id:
                    r.product_split_id.standard_price = rec.product_id.standard_price
                    product_qty_split += r.quantity
            rec.product_quantity_out = product_qty_split
            available_quantity = Quant._get_available_quantity(product_id=rec.product_id, location_id=rec.warehouse_out_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False)
            if rec.product_quantity_out > available_quantity:
                list_line_invalid.append(f"Sản phẩm chính {rec.product_id.name_get()[0][1]} có số lượng yêu cầu xuất lớn hơn số lượng tồn kho của kho {rec.warehouse_out_id.name_get()[0][1]}")
        if len(list_line_invalid) > 0:
            raise ValidationError(_('\n'.join(list_line_invalid)))
        company_id = self.env.company
        pk_type_in = self.env['stock.picking.type'].sudo().search([('company_id', '=', company_id.id), ('code', '=', 'incoming'),('sequence_code','=','IN_OTHER')], limit=1)
        pk_type_out = self.env['stock.picking.type'].sudo().search([('company_id', '=', company_id.id), ('code', '=', 'outgoing'),('sequence_code','=','EX_OTHER')], limit=1)
        # pk_type_import = self.env['stock.picking.type'].sudo().search([('company_id', '=', company_id.id), ('code', '=', 'incoming'), ('sequence_code','=','IN_OTHER')], limit=1)
        # pk_type_export = self.env['stock.picking.type'].sudo().search([('company_id', '=', company_id.id), ('code', '=', 'outgoing'),('sequence_code','=','EX_OTHER')], limit=1)
        # if not pk_type_import or pk_type_export:
        #     raise ValidationError(_('Không tìm thấy kiểu giao nhận Orther Ex'))
        self.create_orther_import(pk_type_in, company_id)
        self.create_orther_export(pk_type_out, company_id)
        self.user_approve_id = self.env.user
        self.date_approved = datetime.now()
        self.state = 'done'


    def action_view_picking(self):
        self.ensure_one()
        ctx = dict(self._context)
        ctx.update({
            'default_split_product_id': self.id,
        })
        return {
            'name': _('Phiếu nhập/xuất khác'),
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
        location_id = self.env['stock.location'].search([('code','=','N0301')], limit=1)
        if not location_id:
            raise ValidationError(_('Không tìm thấy địa điểm Nhập tách/gộp mã nguyên phụ liệu mã N0301'))
        for record in self.split_product_line_ids:
            data = []
            for rec in self.split_product_line_sub_ids:
                if rec.product_id.id == record.product_id.id and rec.parent_id.id == record.id:
                    data.append((0, 0, {
                        'product_id': rec.product_split_id.id,
                        'name': rec.product_split_id.name_get()[0][1],
                        'date': datetime.now(),
                        'product_uom': rec.product_uom_split.id,
                        'product_uom_qty': rec.quantity,
                        'quantity_done': rec.quantity,
                        'location_id':location_id.id,
                        'location_dest_id': rec.warehouse_in_id.id
                    }))
            pickings |= self.env['stock.picking'].with_company(company).create({
                'other_import': True,
                'state':'draft',
                'picking_type_id': pk_type.id,
                'split_product_id': self.id,
                'move_ids_without_package': data,
                'location_id': location_id.id,
                'location_dest_id': record.warehouse_in_id.id,
                'origin': self.name
            })
        for pick in pickings:
            pick.button_validate()
        return pickings

    def create_orther_export(self, pk_type, company):
        pickings = self.env['stock.picking']
        location_id = self.env['stock.location'].search([('code','=','X0301')], limit=1)
        if not location_id:
            raise ValidationError(_('Không tìm thấy địa điểm Xuất tách/gộp mã nguyên phụ liệu mã X0301'))
        for record in self.split_product_line_ids:
            data = [(0, 0, {
                'product_id': record.product_id.id,
                'name': record.product_id.name_get()[0][1],
                'date': datetime.now(),
                'product_uom': record.product_id.uom_id.id,
                'product_uom_qty': record.product_quantity_out,
                'quantity_done': record.product_quantity_out,
                'location_id': record.warehouse_out_id.id,
                'location_dest_id': location_id.id,
            })]
            pickings |= self.env['stock.picking'].with_company(company).create({
                'other_export': True,
                'state':'draft',
                'picking_type_id': pk_type.id,
                'split_product_id': self.id,
                'move_ids_without_package': data,
                'location_id': record.warehouse_out_id.id,
                'location_dest_id': location_id.id,
                'origin': self.name
            })
        for pick in pickings:
            pick.button_validate()
        return pickings


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
    warehouse_out_id = fields.Many2one('stock.location', 'Kho xuất', required=True)
    product_quantity_out = fields.Integer('Số lượng xuất', readonly=True)
    product_quantity_split = fields.Integer('Số lượng phân tách', required=True)
    product_uom_split = fields.Many2one('uom.uom', 'DVT SL phân tách', required=True, related='product_id.uom_id')
    warehouse_in_id = fields.Many2one('stock.location', 'Kho nhập', required=True)
    unit_price = fields.Float('Đơn giá', readonly=True, related='product_id.standard_price')
    value = fields.Float('Giá trị', readonly=True)

    @api.constrains('product_quantity_split')
    def constrains_quantity(self):
        for rec in self:
            if rec.product_quantity_split < 0:
                raise ValidationError(_('Không được phép nhập giá trị âm!'))


class SpilitProductLineSub(models.Model):
    _name = 'split.product.line.sub'
    _description = 'Dòng sản phẩm phân rã'

    state = fields.Selection(
        [('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done'), ('canceled', 'Canceled')],
        related='split_product_id.state',
        string='Trạng thái')
    split_product_id = fields.Many2one('split.product')
    product_id = fields.Many2one('product.product', 'Sản phẩm chính')
    product_split_id = fields.Many2one('product.product', string='Sản phẩm phân tách')
    warehouse_in_id = fields.Many2one('stock.location', 'Kho nhập')
    quantity = fields.Integer('Số lượng', required=True)
    product_uom_split = fields.Many2one('uom.uom', 'DVT SL phân tách', related='product_id.uom_id')
    unit_price = fields.Float('Đơn giá', readonly=True, related='product_split_id.standard_price')
    value = fields.Float('Giá trị', readonly=True)
    parent_id = fields.Many2one('split.product.line')

    @api.constrains('quantity')
    def constrains_quantity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_('Không được phép nhập giá trị âm!'))

# class AccountIntermediary
