from odoo import api, fields, models, _
from datetime import date, datetime, timedelta, time
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
    self.write({'priority': '0', 'done_picking_uid': self._uid})

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

    is_picking_return = fields.Boolean(string='Phiếu trả hàng', compute='compute_is_picking_return')
    total_purchase_qty = fields.Float(string='Tổng số lượng mua hoàn thành', compute='_compute_total_qty')
    total_qty_done = fields.Float(string='Tổng số lượng hoàn thành', compute='_compute_total_qty')
    create_from_po_inter_company = fields.Boolean(string='Tạo từ PO liên công ty', default=False, readonly=True)
    check_inter_company = fields.Boolean(string='Ẩn button liên công ty', compute='compute_check_inter_company')

    def compute_check_inter_company(self):
        for rec in self:
            location_inter_company = rec.location_dest_id.virtual_location_ch
            company_dest_id = self.env['res.company'].search([('code', '=', '1400')], limit=1)
            po_inter_company = self.env['purchase.order'].with_company(company_dest_id).search([('create_from_picking', '=', rec.id)], limit=1)
            if location_inter_company and not po_inter_company and rec.state == 'done':
                rec.check_inter_company = True
            else:
                rec.check_inter_company = False

    def prepare_po_values(self):
        company_id = self.env['res.company'].search([('code', '=', '1300')], limit=1)
        company_dest_id = self.env['res.company'].search([('code', '=', '1400')], limit=1)
        occasion_code_id = self.move_line_ids.mapped('occasion_code_id')
        location_mapping = self.env['stock.location.mapping'].search([('location_id', '=', self.location_dest_id.id)], limit=1)
        po = {
            'partner_id': company_id.partner_id.id,
            'occasion_code_id': occasion_code_id[0].id if len(occasion_code_id) >= 1 else False,
            'receive_date': datetime.now(),
            'date_planned': datetime.now(),
            'source_location_id': self.location_dest_id.id,
            'location_id': location_mapping.location_map_id.id,
            'is_inter_company': True,
            'is_return': False,
            'company_id': company_dest_id.id,
            'create_from_picking': self.id
        }
        po_line = []
        for line in self.move_ids:
            data = self.env['product.supplierinfo'].with_company(company_dest_id).search(
                [
                    '|',
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                    ('product_id', '=', line.product_id.id if line.product_id else False),
                    ('partner_id', '=', company_id.partner_id.id),
                    ('currency_id', '=', line.purchase_line_id.currency_id.id),
                    ('product_uom', '=', line.product_uom.id),
                    ('min_qty', '<=', line.quantity_done),
                    ('date_start', '<=', datetime.now()),
                    ('date_end', '>=', datetime.now())
                ])
            data = data.sorted(lambda s: (s.sequence, -s.min_qty, s.price, s.id)).filtered(lambda x: x.min_qty <= line.quantity_done)
            if not data:
                raise ValidationError(_('Chưa cấu hình giá nhà cung cấp. Không thể tạo đơn mua liên công ty'))
            po_line.append((0, 0, {
                'product_id': line.product_id.id,
                'purchase_quantity': line.quantity_done,
                'product_qty': line.quantity_done * (data[0].amount_conversion or line.quantity_change),
                'taxes_id': [(6, 0, self.env['account.tax'].with_company(company_dest_id).search([
                    ('code', 'in', line.purchase_line_id.taxes_id.mapped('code')), ('company_id', '=', company_dest_id.id)]).ids)],
                'vendor_price': data[0].price,
                'exchange_quantity': data[0].amount_conversion,
                'location_id': location_mapping.location_map_id.id,
            }))
        po['order_line'] = po_line
        return po

    def create_order_inter_company(self):
        company_dest_id = self.env['res.company'].search([('code', '=', '1400')], limit=1)
        purchase_model = self.env['purchase.order']
        po_inter_company = purchase_model.with_company(company_dest_id).search(
            [('create_from_picking', '=', self.id)], limit=1)
        if po_inter_company:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Đã tạo tồn tại đơn liên công ty',
                    'type': 'danger',
                    'sticky': False,
                }
            }
        purchase_model = purchase_model.with_company(company_dest_id).create(self.prepare_po_values())
        if purchase_model:
            purchase_model.with_company(company_dest_id).action_confirm()
            purchase_model.with_company(company_dest_id).action_approved()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đã tạo thành công đơn liên công ty',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.depends('move_ids.quantity_purchase_done', 'move_ids.quantity_done')
    def _compute_total_qty(self):
        for rec in self:
            self._cr.execute("""
                select
                    sum(quantity_purchase_done) as quantity_purchase_done,
                    sum(quantity_done) as quantity_done
                from
                    stock_move sm
                where
                    picking_id = %s;
            """ % rec.id)
            data = self._cr.dictfetchone()
            rec.total_purchase_qty = data.get('quantity_purchase_done', 0)
            rec.total_qty_done = data.get('quantity_done', 0)

    def compute_is_picking_return(self):
        for rec in self:
            if self.move_ids.filtered(lambda x: x.origin_returned_move_id):
                rec.is_picking_return = True
            elif rec.x_hide_return:
                rec.is_picking_return = True
            elif (rec.other_export or (not rec.other_export and rec.state != 'done')):
                rec.is_picking_return = True
            else:
                rec.is_picking_return = False

    def open_scan_barcode(self):
        self.ensure_one()
        stock_picking_scan_line_ids = [(0, 0, {
            'move_line_id': sml.id,
            'max_qty': round((sml.move_id.product_uom_qty * (sml.product_id.tolerance + 100) / 100), 0),
            'product_qty_done': sml.qty_done
        }) for sml in self.move_line_ids_without_package if sml.product_id.is_need_scan_barcode]

        if stock_picking_scan_line_ids:
            scan_id = self.env['stock.picking.scan'].create({
                'picking_id': self.id,
                'stock_picking_scan_line_ids': stock_picking_scan_line_ids
            })
            return {
                'name': self.name,
                'view_mode': 'form',
                'res_model': 'stock.picking.scan',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': scan_id.id
            }

    def button_forlife_validate(self):
        self.ensure_one()
        if self.is_pk_purchase:
            view_over = self.env.ref('forlife_stock.stock_picking_over_popup_view_form')
            if any(pk.qty_done > pk_od.product_uom_qty for pk, pk_od in
                   zip(self.move_line_ids_without_package, self.move_ids_without_package)):
                return {
                    'name': 'Tạo phần dở dang thừa?',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'stock.picking.over.popup.confirm',
                    'views': [(view_over.id, 'form')],
                    'view_id': view_over.id,
                    'target': 'new',
                    'context': dict(self.env.context, default_picking_id=self.id),
                }
        return self.button_validate()

    def action_confirm(self):
        for picking in self:
            for line in picking.move_ids_without_package:
                if picking.other_import and line.reason_id.is_price_unit and line.amount_total <= 0:
                    raise ValidationError('Bạn chưa nhập tổng tiền cho sản phẩm %s' % line.product_id.name)
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
            pk_type = self.env['stock.picking.type'].sudo().search([('company_id', '=', company), ('code', '=', 'outgoing')], limit=1)
            if not pk_type:
                pk_type = self.env['stock.picking.type'].sudo().create({
                    'name': 'Giao hàng',
                    'code': 'outgoing',
                    'company_id': company,
                    'sequence_code': 'sequence_code1'
                })
            ## Tạo mới phiếu nhập hàng và xác nhận phiếu xuất
            res.update({'picking_type_id': pk_type})
        if self.env.context.get('default_other_import'):
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)], limit=1)
            if picking_type_id:
                res.update({'picking_type_id': picking_type_id.id})
        if self.env.context.get('default_other_export'):
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)], limit=1)
            if picking_type_id:
                res.update({'picking_type_id': picking_type_id.id})
        return res

    transfer_id = fields.Many2one('stock.transfer')
    reason_type_id = fields.Many2one('forlife.reason.type')
    other_export = fields.Boolean(default=False)
    other_import = fields.Boolean(default=False)
    transfer_stock_inventory_id = fields.Many2one('transfer.stock.inventory')
    other_import_export_request_id = fields.Many2one('forlife.other.in.out.request', string="Other Import Export Request")
    stock_custom_location_ids = fields.One2many('stock.location', 'stock_custom_picking_id')
    leftovers_id = fields.Many2one('stock.picking', 'Phần thừa của', copy=False, readonly=True, check_company=True)

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
        # domain=_domain_location_id,
        states={'done': [('readonly', True)]})

    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=False,
        # domain=_domain_location_dest_id,
        states={'done': [('readonly', True)]})

    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False, default=fields.Datetime.now,
                                help="Date at which the transfer has been processed or cancelled.")
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', required=False, readonly=False, index=True, states={'draft': [('readonly', False)]})
    display_asset = fields.Char(string='Display', compute="compute_display_asset")
    is_from_request = fields.Boolean('', default=False)
    stock_name = fields.Char(string='Mã phiếu')

    # Lệnh sản xuất, xử lý khi tạo điều chuyển cho LSX A sang LSX B
    work_from = fields.Many2one('forlife.production', string="LSX From", ondelete='restrict')
    work_to = fields.Many2one('forlife.production', string="LSX To", ondelete='restrict')
    is_last_transfer = fields.Boolean(string="Lần nhập kho cuối")

    @api.onchange('reason_type_id')
    def _onchange_reason_location(self):
        if self.reason_type_id:
            if self._context.get('default_other_import'):
                return {
                    'domain': {
                        'location_id': [('reason_type_id', '=', self.reason_type_id.id)]
                    }
            }
            if self._context.get('default_other_export'):
                return {
                    'domain': {
                        'location_dest_id': [('reason_type_id', '=', self.reason_type_id.id)]
                    }
                }

    @api.depends('location_id', 'location_dest_id')
    def compute_display_asset(self):
        for r in self:
            if (r.location_id and r.location_id.is_assets and r.other_import) or (r.location_dest_id and r.location_dest_id.is_assets and r.other_export):
                r.display_asset = 'show'
            else:
                r.display_asset = 'hide'

    @api.depends('picking_type_id', 'partner_id')
    def _compute_location_id(self):
        """
            K update lại location với các phiếu nhập xuất khác
        """
        for picking in self:
            picking = picking.with_company(picking.company_id)
            if not picking.other_import and not picking.other_export:
                if picking.picking_type_id and picking.state == 'draft':
                    if picking.picking_type_id.default_location_src_id:
                        location_id = picking.picking_type_id.default_location_src_id.id
                    elif picking.partner_id:
                        location_id = picking.partner_id.property_stock_supplier.id
                    else:
                        _customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

                    if picking.picking_type_id.default_location_dest_id:
                        location_dest_id = picking.picking_type_id.default_location_dest_id.id
                    elif picking.partner_id:
                        location_dest_id = picking.partner_id.property_stock_customer.id
                    else:
                        location_dest_id, _supplierloc = self.env['stock.warehouse']._get_partner_locations()

                    picking.location_id = location_id
                    picking.location_dest_id = location_dest_id

    def _action_done(self):
        old_date_done = {
            item.id: item.date_done for item in self
        }
        res = super(StockPicking, self)._action_done()
        for record in self:
            if old_date_done.get(record.id) == record.date_done:
                continue
            record.date_done = old_date_done.get(record.id)
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'date_done' in vals:
            for item in self:
                item.move_ids.write({'date': item.date_done})
                item.move_line_ids.write({'date': item.date_done})

        if "import_file" in self.env.context:
            for line in self.move_line_ids_without_package.filtered(lambda x: x.picking_id.is_pk_purchase):
                if line.qty_done != line.quantity_purchase_done * line.quantity_change:
                    line.qty_done = line.quantity_purchase_done * line.quantity_change

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
                for layer in layers:
                    if layer.account_move_id:
                        reversal_data = {
                            "move_ids": [
                                [6, 0, [layer.account_move_id.id]]
                            ],
                            "reason": False,
                            "date_mode": "custom",
                            "journal_id": layer.account_move_id.journal_id.id,
                            "date": date.today().strftime("%Y-%m-%d")
                        }
                        action = self.env['account.move.reversal'].sudo().create(reversal_data).reverse_moves()
                        new_mov = self.env['account.move'].browse(action['res_id'])
                        new_mov.write({
                            'stock_move_id': layer.stock_move_id.id
                        })
                        new_mov.action_post()
            else:
                rec.move_ids._action_cancel()
                rec.write({'is_locked': True})
        return True

    @api.model_create_multi
    def create(self, vals):
        line = super(StockPicking, self).create(vals)
        if self.env.context.get('default_other_import') or self.env.context.get('default_other_export'):
            for rec in line.move_ids_without_package:
                rec._onchange_product_id()
                #todo: handle above source, raise exception when import picking (business unknown)
                location_values = {}
                if rec.location_id != line.location_id:
                    location_values['location_id'] = line.location_id.id
                if rec.location_dest_id != line.location_dest_id:
                    location_values['location_dest_id'] = line.location_dest_id.id
                if location_values:
                    rec.update(location_values)
        return line

    def button_validate(self):
        if self._context.get('check_date_done'):
            record_valid_date = self.filtered(lambda s: s.state == 'assigned' and s.date_done.date() != fields.Date.today())
            if record_valid_date:
                action = self.env["ir.actions.actions"]._for_xml_id("forlife_stock.confirm_continue_validate_picking_action")
                message = f"Kiểm tra lại ngày hoàn thành trên phiếu {', '.join(record_valid_date.mapped('name'))} trước khi xác nhận phiếu"
                ctx = dict(self._context, picking_ids=self.ids, default_message=message)
                action['context'] = ctx
                return action
        res = super(StockPicking, self).button_validate()
        for record in self:

            # Nhâp/ xuất khác
            if record.other_export or record.other_import:
                self.update_quantity_production_order_in_other_picking(record)

            # Nhập thành phẩm SX
            if record.picking_type_id.exchange_code == 'incoming' and record.state == 'done' and record.location_id.code != 'N0103':
                self.validate_quantity_remain_finished_picking(record)

            # Điều chuyển từ stock.transfer có gắn lệnh sản xuất
            if record.transfer_id and (record.work_from or record.work_to):
                self.update_quantity_production_order_from_stock_transfer(record)

        return res

    # Nhập/ xuất khác
    def update_quantity_production_order_in_other_picking(self, picking_id):
        """
            Update lại số lượng tồn kho theo LSX ở phiếu nhập xuất khác
        """

        for rec in picking_id.move_ids_without_package.filtered(lambda r: r.work_production):
            if rec.product_id.categ_id.category_type_id.code not in ('2','3','4'):
                continue
            # Nhập khác
            if picking_id.other_import:
                domain = [('product_id', '=', rec.product_id.id), ('location_id', '=', rec.picking_id.location_dest_id.id), ('production_id.code', '=', rec.work_production.code)]
                quantity = self.env['quantity.production.order'].search(domain)
                if quantity:
                    quantity.write({
                        'quantity': quantity.quantity + rec.quantity_done
                    })
                else:
                    self.env['quantity.production.order'].create({
                        'product_id': rec.product_id.id,
                        'location_id': rec.picking_id.location_dest_id.id,
                        'production_id': rec.work_production.id,
                        'quantity': rec.quantity_done
                    })

            # Xuất khác
            if picking_id.other_export:
                domain = [('product_id', '=', rec.product_id.id), ('location_id', '=', rec.picking_id.location_id.id), ('production_id.code', '=', rec.work_production.code)]
                quantity_prodution = self.env['quantity.production.order'].search(domain)
                if quantity_prodution:
                    if rec.quantity_done > quantity_prodution.quantity:
                        raise ValidationError(
                            '[01] - Số lượng tồn kho sản phẩm [%s] %s trong lệnh sản xuất %s không đủ để điều chuyển!' % (rec.product_id.code, rec.product_id.name, rec.work_production.code))
                    else:
                        quantity_prodution.update({
                            'quantity': quantity_prodution.quantity - rec.quantity_done
                        })
                else:
                    raise ValidationError('Sản phẩm [%s] %s không có trong lệnh sản xuất %s!' % (rec.product_id.code, rec.product_id.name, rec.work_production.code))

    # Check tồn thành phẩm
    def validate_quantity_remain_finished_picking(self, picking_id):
        for rec in picking_id.move_ids_without_package:
            remaining_qty = rec.work_production.forlife_production_finished_product_ids.filtered(lambda r: r.product_id.id == rec.product_id.id).remaining_qty or 0
            if rec.work_production and rec.quantity_done > remaining_qty:
                raise ValidationError('Số lượng sản phẩm [%s] %s lớn hơn số lượng còn lại (%s) trong lệnh sản xuất!' % (rec.product_id.code, rec.product_id.name, str(remaining_qty)))

    # Điều chuyển từ stock.transfer k qua HO
    def update_quantity_production_order_from_stock_transfer(self, picking_id):
        """
            Update lại số lượng tồn kho theo LSX ở phiếu điều chuyển, trường hợp điều chuyển có LSX
            1. Trừ tồn ở LSX work_from
            2. Update tồn ở LSX work_to
        """

        for rec in picking_id.move_ids_without_package.filtered(lambda r: r.work_production):
            if rec.product_id.categ_id.category_type_id.code not in ('2','3','4'):
                continue
            if picking_id.location_id.id == picking_id.transfer_id.location_id.id and picking_id.work_from:
                # Trừ tồn ở lệnh work_from
                domain = [('product_id', '=', rec.product_id.id), ('location_id', '=', picking_id.location_id.id), ('production_id.code', '=', rec.work_production.code)]
                quantity_prodution = self.env['quantity.production.order'].search(domain)
                if quantity_prodution:
                    if rec.quantity_done > quantity_prodution.quantity:
                        raise ValidationError(
                            '[03] - Số lượng tồn kho sản phẩm [%s] %s trong lệnh sản xuất %s không đủ để điều chuyển!' % (
                                rec.product_id.code, rec.product_id.name, rec.work_production.code))
                    else:
                        quantity_prodution.update({
                            'quantity': quantity_prodution.quantity - rec.quantity_done
                        })
                else:
                    raise ValidationError('Sản phẩm [%s] %s không có trong lệnh sản xuất %s!' % (rec.product_id.code, rec.product_id.name, rec.work_production.code))

            if picking_id.location_dest_id.id == picking_id.transfer_id.location_dest_id.id and picking_id.work_to:
                # Thêm tồn ở lệnh work_to
                domain = [('product_id', '=', rec.product_id.id), ('location_id', '=', picking_id.location_dest_id.id), ('production_id.code', '=', rec.work_production.code)]
                quantity = self.env['quantity.production.order'].search(domain)
                if quantity:
                    quantity.write({
                        'quantity': quantity.quantity + rec.quantity_done
                    })
                else:
                    self.env['quantity.production.order'].create({
                        'product_id': rec.product_id.id,
                        'location_id': rec.picking_id.location_dest_id.id,
                        'production_id': rec.work_production.id,
                        'quantity': rec.quantity_done
                    })

    @api.model
    def get_import_templates(self):
        if self.env.context.get('default_other_import'):
            return [{
                'label': _('Tải xuống mẫu phiếu nhập khác'),
                'template': '/forlife_stock/static/src/xlsx/nhap_khac.xlsx?download=true'
            }, {
                'label': _('Tải xuống mẫu phiếu import update'),
                'template': '/forlife_stock/static/src/xlsx/template_update_nk.xlsx?download=true'
            }]
        elif self.env.context.get('default_other_export'):
            return [{
                'label': _('Tải xuống mẫu phiếu xuất khác'),
                'template': '/forlife_stock/static/src/xlsx/xuat_khac.xlsx?download=true'
            }, {
                'label': _('Tải xuống mẫu phiếu import update'),
                'template': '/forlife_stock/static/src/xlsx/template_update_xk.xlsx?download=true'
            }]
        else:
            return [{
                'label': _('Tải xuống mẫu phiếu import update'),
                'template': '/forlife_stock/static/src/xlsx/template_update_nhap_kho.xlsx?download=true'
            }]

    @api.model
    def load(self, fields, data):
        if "import_file" in self.env.context:
            if 'stock_name' in fields and 'move_line_ids_without_package/sequence' in fields:
                for record in data:
                    if 'move_line_ids_without_package/sequence' in fields and not record[fields.index('move_line_ids_without_package/sequence')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường stt dòng"))
                    if 'move_line_ids_without_package/product_id' in fields and not record[fields.index('move_line_ids_without_package/product_id')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường sản phẩm"))
                    if 'move_line_ids_without_package/qty_done' in fields and not record[fields.index('move_line_ids_without_package/qty_done')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường hoàn thành"))
                    if 'move_line_ids_without_package/quantity_purchase_done' in fields and not record[fields.index('move_line_ids_without_package/quantity_purchase_done')]:
                        raise ValidationError(_("Thiếu giá trị bắt buộc cho trường số lượng mua hoàn thành"))
                fields[fields.index('stock_name')] = 'id'
                fields[fields.index('move_line_ids_without_package/sequence')] = 'move_line_ids_without_package/id'
                id = fields.index('id')
                line_id = fields.index('move_line_ids_without_package/id')
                product = fields.index('move_line_ids_without_package/product_id')
                reference = None
                for rec in data:
                    if rec[id]:
                        reference = rec[id]
                    picking = self.env['stock.picking'].search([('name', '=', reference)], limit=1)
                    if not picking:
                        raise ValidationError(_("Không tồn tại mã phiếu %s" % (reference)))
                    if picking.state != 'assigned':
                        raise ValidationError(_("Phiếu %s chỉ có thể update ở trạng thái sẵn sàng" % (reference)))
                    if rec[id]:
                        rec[id] = picking.export_data(['id']).get('datas')[0][0]
                    if int(rec[line_id]) > len(picking.move_line_ids_without_package):
                        raise ValidationError(_("Phiếu %s không có dòng %s" % (picking.name, rec[line_id])))
                    elif rec[product] != picking.move_line_ids_without_package[int(rec[line_id]) - 1].product_id.barcode:
                        raise ValidationError(_("Mã sản phẩm của phiếu %s không khớp ở dòng %s" % (picking.name, rec[line_id])))
                    else:
                        rec[line_id] = picking.move_line_ids_without_package[int(rec[line_id]) - 1].export_data(['id']).get('datas')[0][0]
        return super().load(fields, data)

