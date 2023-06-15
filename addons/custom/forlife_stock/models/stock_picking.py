from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.stock.models.stock_picking import Picking as InheritPicking
from odoo.exceptions import ValidationError


def _action_done(self):
    """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
    This method makes sure every `stock.move.line` is linked to a `stock.move` by either
    linking them to an existing one or a newly created one.

    If the context key `cancel_backorder` is present, backorders won't be created.

    :return: True
    :rtype: bool
    """
    self._check_company()

    todo_moves = self.move_ids.filtered(
        lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
    for picking in self:
        if picking.owner_id:
            picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
            picking.move_line_ids.write({'owner_id': picking.owner_id.id})
    todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
    # edit here: remove update date_done
    # self.write({'date_done': fields.Datetime.now(), 'priority': '0'})
    self.write({'priority': '0'})

    # if incoming/internal moves make other confirmed/partially_available moves available, assign them
    done_incoming_moves = self.filtered(lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(
        lambda m: m.state == 'done')
    done_incoming_moves._trigger_assign()

    self._send_confirmation_email()
    return True


InheritPicking._action_done = _action_done


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _order = 'create_date desc'

    def action_confirm(self):
        for picking in self:
            if (not picking.other_import and not picking.other_export):
                continue
            if (picking.other_import and not picking.location_id.is_assets) or (picking.other_export and not picking.location_dest_id.is_assets):
                continue
            for line in picking.move_ids:
                account = line.ref_asset.asset_account.id
                if (picking.other_export and account != picking.location_dest_id.with_company(picking.company_id).x_property_valuation_in_account_id.id) or (
                        picking.other_import and account != picking.location_id.with_company(picking.company_id).x_property_valuation_out_account_id.id):
                    raise ValidationError(
                        _('Tài khoản cấu hình trong thẻ tài sản không khớp với tài khoản trong lý do xuất khác'))
        res = super().action_confirm()
        return res


    def _domain_location_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    def _domain_location_dest_id(self):
        if self.env.context.get('default_other_export'):
            return "[('reason_type_id', '=', reason_type_id)]"

    @api.model
    def default_get(self, fields):
        res = super(StockPicking, self).default_get(fields)
        company_id = self.env.company.id
        if self.env.context.get('from_inter_company'):
            company = self.env.context.get('company_po')
            pk_type = self.env['stock.picking.type'].sudo().search(
                [('company_id', '=', company), ('code', '=', 'outgoing')], limit=1)
            if not pk_type:
                pk_type = self.env['stock.picking.type'].sudo().create(
                    {'name': 'Giao hàng', 'code': 'outgoing', 'company_id': company,
                     'sequence_code': 'sequence_code1'})
            ## Tạo mới phiếu nhập hàng và xác nhận phiếu xuất
            res.update({'picking_type_id': pk_type})
        if self.env.context.get('default_other_import'):
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', company_id)], limit=1)
            if picking_type_id:
                res.update({'picking_type_id': picking_type_id.id})
        if self.env.context.get('default_other_export'):
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', '=', company_id)], limit=1)
            if picking_type_id:
                res.update({'picking_type_id': picking_type_id.id})
        return res

    ware_check = fields.Boolean('', default=False)
    transfer_id = fields.Many2one('stock.transfer')
    reason_type_id = fields.Many2one('forlife.reason.type')
    other_export = fields.Boolean(default=False)
    other_import = fields.Boolean(default=False)
    transfer_stock_inventory_id = fields.Many2one('transfer.stock.inventory')
    other_import_export_request_id = fields.Many2one('forlife.other.in.out.request', string="Other Import Export Request")
    stock_custom_location_ids = fields.One2many('stock.location', 'stock_custom_picking_id')

    #field check phiếu trả hàng:
    x_is_check_return = fields.Boolean('', default=False)
    x_hide_return = fields.Boolean('', default=False)

    relation_return = fields.Char(string='Phiếu trả lại liên quan')
    move_ids_without_package = fields.One2many(
        'stock.move', 'picking_id', string="Hoạt động", compute='_compute_move_without_package',
        inverse='_set_move_without_package', compute_sudo=True)

    location_id = fields.Many2one(
        'stock.location', "Source Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=False,
        domain=_domain_location_id,
        states={'done': [('readonly', True)]})

    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=False,
        domain=_domain_location_dest_id,
        states={'done': [('readonly', True)]})

    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False, default=fields.Datetime.now,
                                help="Date at which the transfer has been processed or cancelled.")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=False, readonly=False, index=True,
        states={'draft': [('readonly', False)]})
    display_asset = fields.Char(string='Display', compute="compute_display_asset")

    @api.depends('location_id', 'location_dest_id')
    def compute_display_asset(self):
        for r in self:
            if (r.location_id and r.location_id.is_assets and r.other_import) or (r.location_dest_id and r.location_dest_id.is_assets and r.other_export):
                r.display_asset = 'show'
            else:
                r.display_asset = 'hide'

    def _action_done(self):
        old_date_done = {
            item.id: item.date_done for item in self
        }
        # old_date_done = self.date_done
        res = super(StockPicking, self)._action_done()
        for record in self:
            if old_date_done.get(record.id) == record.date_done:
                continue
            record.date_done = old_date_done.get(record.id)
        # if old_date_done != self.date_done:
        #     self.date_done = old_date_done
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'date_done' in vals:
            for item in self:
                item.move_ids.write({'date': item.date_done})
                item.move_line_ids.write({'date': item.date_done})
        # if 'date_done' in vals:
        #     self.move_ids.write({'date': self.date_done})
        #     self.move_line_ids.write({'date': self.date_done})
        return res

    def action_back_to_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        for rec in self:
            if rec.other_import or rec.other_export:
                rec.state = 'cancel'
                for line in rec.move_line_ids_without_package:
                    line.qty_done = 0
                    line.reserved_uom_qty = 0
                    line.qty_done = 0
                for line in rec.move_ids_without_package:
                    line.forecast_availability = 0
                    line.quantity_done = 0
                layers = rec.env['stock.valuation.layer'].search([('stock_move_id.picking_id', '=', rec.id)])
                for layer in layers:
                    layer.quantity = 0
                    layer.unit_cost = 0
                    layer.value = 0
                    layer.account_move_id.button_draft()
                    layer.account_move_id.button_cancel()
            else:
                rec.move_ids._action_cancel()
                rec.write({'is_locked': True})
        return True

    @api.model
    def create(self, vals):
        line = super(StockPicking, self).create(vals)
        if self.env.context.get('default_other_import') or self.env.context.get('default_other_export'):
            for rec in line.move_ids_without_package:
                rec._onchange_product_id()
                '''
                rec.location_id = vals['location_id']
                rec.location_dest_id = vals['location_dest_id']
                '''
                #todo: handle above source, raise exception when import picking (business unknown)
                location_values = {}
                if rec.location_id != line.location_id:
                    location_values['location_id'] = line.location_id.id
                if rec.location_dest_id != line.location_dest_id.id:
                    location_values['location_dest_id'] = line.location_dest_id.id
                rec.update(location_values)
        return line

    @api.model
    def get_import_templates(self):
        if self.env.context.get('default_other_import'):
            return [{
                'label': _('Tải xuống mẫu phiếu nhập khác'),
                'template': '/forlife_stock/static/src/xlsx/nhap_khac.xlsx?download=true'
            }]
        else:
            return [{
                'label': _('Tải xuống mẫu phiếu xuất khác'),
                'template': '/forlife_stock/static/src/xlsx/xuat_khac.xlsx?download=true'
            }]


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, merge=True, merge_into=False):
        moves = super(StockMove, self)._action_confirm(merge=False, merge_into=merge_into)
        moves._create_quality_checks()
        return moves

    def _domain_reason_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    po_l_id = fields.Char('Dùng để so sánh hoạt động và hoạt động chi tiết')
    name = fields.Char('Description', required=False)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, required=False)
    product_uom_qty = fields.Float(
        'Demand',
        digits='Product Unit of Measure',
        default=1.0, required=False, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")
    product_uom = fields.Many2one(
        'uom.uom', "UoM", required=False, domain="[('category_id', '=', product_uom_category_id)]",
        compute="_compute_product_uom", store=True, readonly=False, precompute=True,
    )
    procure_method = fields.Selection([
        ('make_to_stock', 'Default: Take From Stock'),
        ('make_to_order', 'Advanced: Apply Procurement Rules')], string='Supply Method',
        default='make_to_stock', required=False, copy=False,
        help="By default, the system will take from the stock in the source location and passively wait for availability. "
             "The other possibility allows you to directly create a procurement on the source location (and thus ignore "
             "its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, "
             "this second option should be chosen.")
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=False,
        states={'done': [('readonly', True)]})
    uom_id = fields.Many2one(related="product_id.uom_id", string='Đơn vị')
    amount_total = fields.Float(string='Thành tiền')
    reason_type_id = fields.Many2one('forlife.reason.type', string='Loại lý do')
    reason_id = fields.Many2one('stock.location', domain=_domain_reason_id)
    occasion_code_id = fields.Many2one('occasion.code', 'Occasion Code')
    work_production = fields.Many2one('forlife.production', string='Lệnh sản xuất')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")
    is_production_order = fields.Boolean(default=False, compute='compute_production_order')
    is_amount_total = fields.Boolean(default=False, compute='compute_production_order')
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        auto_join=True, index=True, required=False,
        check_company=True,
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        auto_join=True, index=True, required=False,
        check_company=True,
        help="Location where the system will stock the finished products.")
    date = fields.Datetime(
        'Date Scheduled', default=fields.Datetime.now, index=True, required=False,
        help="Scheduled date until move is done, then date of actual move processing")
    product_other_id = fields.Many2one('forlife.other.in.out.request.line')
    previous_qty = fields.Float(compute='compute_previous_qty', store=1)

    @api.depends('reason_id')
    def compute_production_order(self):
        for rec in self:
            rec.is_production_order = rec.reason_id.is_work_order
            rec.is_amount_total = rec.reason_id.is_price_unit

    @api.depends('product_id')
    def compute_product_id(self):
        for rec in self:
            if not rec.reason_id.is_price_unit:
                rec.amount_total = rec.product_id.standard_price
            rec.name = rec.product_id.name

    @api.depends('product_uom_qty', 'picking_id.state')
    def compute_previous_qty(self):
        for rec in self:
            if rec.picking_id.backorder_id:
                back_order = self.env['stock.picking'].search([('id', '=',  rec.picking_id.backorder_id.id)])
                if back_order:
                    for r in back_order.move_ids_without_package:
                        if r.product_id == rec.product_id and r.amount_total == rec.amount_total:
                            rec.write({'previous_qty': r.previous_qty})
            else:
                if rec.picking_id.state != 'done':
                    rec.previous_qty = rec.product_uom_qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.name = self.product_id.name
        self.amount_total = self.product_id.standard_price * self.product_uom_qty if not self.reason_id.is_price_unit else 0
        if not self.reason_id:
            self.reason_id = self.picking_id.location_id.id \
                if self.picking_id.other_import else self.picking_id.location_dest_id.id
        if not self.reason_type_id:
            self.reason_type_id = self.picking_id.reason_type_id.id


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    po_id = fields.Char('')
    ref_asset = fields.Many2one('assets.assets', 'Thẻ tài sản')

    @api.constrains('qty_done', 'picking_id.move_ids_without_package')
    def constrains_qty_done(self):
        for rec in self:
            for line in rec.picking_id.move_ids_without_package:
                if rec.move_id.id == line.id:
                    if str(rec.po_id) == str(line.po_l_id):
                        if rec.qty_done > line.product_uom_qty:
                            raise ValidationError(_("Số lượng hoàn thành không được lớn hơn số lượng nhu cầu"))

class StockBackorderConfirmationInherit(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        res = super().process()
        for item in self:
            for rec in item.pick_ids:
                data_pk = self.env['stock.picking'].search([('backorder_id', '=', rec.id)])
                for pk, pk_od in zip(data_pk.move_line_ids_without_package, rec.move_line_ids_without_package):
                    pk.write({
                        'po_id': pk_od.po_id,
                        'qty_done': pk.reserved_qty,
                        'quantity_change': pk_od.quantity_change,
                        'quantity_purchase_done': pk.reserved_qty
                    })
                for pk, pk_od in zip(data_pk.move_ids_without_package, rec.move_ids_without_package):
                    pk.write({
                        'po_l_id': pk_od.po_l_id,
                    })
                for pk, pk_od in zip(rec.move_line_ids_without_package, rec.move_ids_without_package):
                    pk_od.write({
                        'quantity_purchase_done': pk.quantity_purchase_done,
                    })
                for pk, pk_od in zip(data_pk.move_line_ids_without_package, data_pk.move_ids_without_package):
                    pk_od.write({
                        'quantity_purchase_done': pk.quantity_purchase_done,
                    })
        return res
