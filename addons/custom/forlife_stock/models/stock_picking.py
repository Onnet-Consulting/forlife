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

    def _domain_location_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    def _domain_location_dest_id(self):
        if self.env.context.get('default_other_export'):
            return "[('reason_type_id', '=', reason_type_id)]"

    @api.model
    def default_get(self, fields):
        res = super(StockPicking, self).default_get(fields)
        company_id = self.env.context.get('allowed_company_ids')
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
                ('warehouse_id.company_id', 'in', company_id)], limit=1)
            if picking_type_id:
                res.update({'picking_type_id': picking_type_id.id})
        if self.env.context.get('default_other_export'):
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', 'in', company_id)], limit=1)
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
                rec.location_id = vals['location_id']
                rec.location_dest_id = vals['location_dest_id']
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

    @api.depends('move_line_ids_without_package', 'move_line_ids_without_package.ware_check_line')
    def compute_ware_check(self):
        for rec in self:
            rec.is_no_more_quantity = all(rec.order_lines.mapped('ware_check_line'))


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, merge=True, merge_into=False):
        moves = super(StockMove, self)._action_confirm(merge=False, merge_into=merge_into)
        moves._create_quality_checks()
        return moves

    def _domain_reason_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

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
                if rec.picking_id.state not in ('assigned', 'done'):
                    rec.previous_qty = rec.product_uom_qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.reason_id = r.picking_id.location_id.id \
                    if r.picking_id.other_import else r.picking_id.location_dest_id.id
                r.reason_type_id = r.picking_id.reason_type_id.id
                r.name = r.product_id.name
                r.amount_total = r.product_id.standard_price if not r.reason_id.is_price_unit else 0


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    po_id = fields.Char('')
    ware_check_line = fields.Boolean('')

    @api.constrains('qty_done', 'picking_id.move_ids_without_package')
    def constrains_qty_done(self):
        for rec in self:
            for line in rec.picking_id.move_ids_without_package:
                if rec.product_id == line.product_id:
                    if rec.qty_done > line.product_uom_qty:
                        raise ValidationError(_("Số lượng hoàn thành không được lớn hơn số lượng nhu cầu"))

