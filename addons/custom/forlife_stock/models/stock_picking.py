from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.stock.models.stock_picking import Picking as InheritPicking


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
    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['picking_type_id'] = self.env.ref('stock.picking_type_in').id
        return res

    def _domain_location_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    def _domain_location_dest_id(self):
        if self.env.context.get('default_other_export'):
            return "[('reason_type_id', '=', reason_type_id)]"

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
        check_company=True,
        domain=_domain_location_id,
        states={'done': [('readonly', True)]})

    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=True,
        domain=_domain_location_dest_id,
        states={'done': [('readonly', True)]})

    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False, default=fields.Datetime.now,
                                help="Date at which the transfer has been processed or cancelled.")



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
            self.move_ids.write({'date': self.date_done})
            self.move_line_ids.write({'date': self.date_done})
        return res

    def action_back_to_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        if self.other_import or self.other_export:
            self.state = 'cancel'
            for line in self.move_line_ids_without_package:
                line.qty_done = 0
                line.reserved_uom_qty = 0
                line.qty_done = 0
            for line in self.move_ids_without_package:
                line.forecast_availability = 0
                line.quantity_done = 0
            layers = self.env['stock.valuation.layer'].search([('stock_move_id.picking_id', '=', self.id)])
            for layer in layers:
                layer.quantity = 0
                layer.unit_cost = 0
                layer.value = 0
                layer.account_move_id.button_draft()
                layer.account_move_id.button_cancel()
        else:
            self.move_ids._action_cancel()
            self.write({'is_locked': True})
        return True

    @api.model
    def load(self, fields, data):
        list_fields = ['move_ids_without_package/product_id', 'move_ids_without_package/location_id', 'move_ids_without_package/location_dest_id']
        fields.extend(list_fields)
        for rec in data:
            rec.extend([rec[7], rec[14], rec[14]])
            rec[8] = ''
        return super().load(fields, data)

    @api.model
    def get_import_templates(self):
        if self.env.context.get('default_other_import'):
            return [{
                'label': _('Tải xuống mẫu phiếu nhập khác'),
                'template': '/forlife_stock/static/src/xlsx/mau_nhap_khac.xlsx?download=true'
            }]
        else:
            return [{
                'label': _('Tải xuống mẫu phiếu xuất khác'),
                'template': '/forlife_stock/static/src/xlsx/mau_xuat_khac.xlsx?download=true'
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

    name = fields.Char(required=False)
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True,
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
        'stock.location', "Địa điểm nguồn",
        auto_join=True, index=True,
        check_company=True,
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")

    location_dest_id = fields.Many2one(
        'stock.location', 'Địa điểm đích',
        auto_join=True, index=True,
        check_company=True,
        help="Location where the system will stock the finished products.")

    @api.depends('reason_id')
    def compute_production_order(self):
        for rec in self:
            rec.is_production_order = rec.reason_id.is_work_order
            rec.is_amount_total = rec.reason_id.is_price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.reason_id = r.picking_id.location_id.id \
                    if r.picking_id.other_import else r.picking_id.location_dest_id.id
                r.reason_type_id = r.picking_id.reason_type_id.id
                r.name = r.product_id.name

