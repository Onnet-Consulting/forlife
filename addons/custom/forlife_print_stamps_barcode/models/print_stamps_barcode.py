# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PrintStampsBarcode(models.Model):
    _name = 'print.stamps.barcode'
    _rec_name = 'create_date'
    _description = 'Print Stamps Barcode'

    create_uid = fields.Many2one(comodel_name="res.users", string="Create By", default=lambda s: s.env.user)
    approve_uid = fields.Many2one(comodel_name="res.users", string="Approve By")
    create_date = fields.Datetime(string="Create Date", default=fields.Datetime.now)
    start_print = fields.Integer(string="Start Print", required=True, default=1)
    state = fields.Selection(string="State", selection=[('draft', _('Draft')), ('approved', _('Approved'))], default='draft')
    view = fields.Html('View', compute='compute_view')
    line_ids = fields.One2many(comodel_name="print.stamps.barcode.line", inverse_name="print_barcode_id", string="Lines")

    _sql_constraints = [
        ('check_start_print', 'CHECK(start_print >= 1 and start_print <= 40)', _('Start Print must be between 1 and 40'))
    ]

    @api.onchange('start_print')
    def onchange_start_print(self):
        if self.start_print > 40 or self.start_print < 1:
            self.start_print = min(40, max(1, self.start_print))

    @api.depends('line_ids', 'start_print')
    def compute_view(self):
        for line in self:
            totals = sum(line.line_ids.mapped('qty')) + line.start_print - 1
            result = []
            page = 1
            while totals > 0:
                res = ''
                total = min(40, totals)
                totals = totals - total
                ind = 1
                for row in range(10):
                    rows = ''
                    for col in range(4):
                        rows += ('<th style="background-color: #03009b; color: #ffffff;">' if ((ind >= line.start_print or page > 1) and ind < total + 1) else '<th>') + str(ind) + '</th>'
                        ind += 1
                    res += '<tr>' + rows + '</tr>'
                result.append(f'<div class="col-3"><table class="table table-bordered text-center"><th colspan="4">Trang {page}</th>' + res + '</table></div>')
                page += 1
            line.view = '<div class="row">' + ''.join(result) + '</div>'

    def btn_approve(self):
        self.ensure_one()
        if self.state == 'approved':
            return True
        if self.approve_uid:
            if self.env.user.id == self.approve_uid.id:
                self.write({
                    'state': 'approved',
                })
            else:
                raise UserError(_('You do not have permission to make approvals.'))
        else:
            self.write({
                'state': 'approved',
                'approve_uid': self.env.user.id,
            })

    def get_product_list(self):
        product_list = [(0, 0)] * (self.start_print - 1) if self.start_print > 1 else []
        for line in self.line_ids:
            product_list += [(line.product_id, 0)] * line.qty
        total = sum(self.line_ids.mapped('qty')) + self.start_print - 1
        product_list += [(0, 0)] * (40 - (int((total/40 - int(total/40)) * 40)))
        res = [product_list[0:min(40, len(product_list)):]]
        while product_list:
            product_list = product_list[min(40, len(product_list)):]
            if product_list:
                res.append(product_list[0:min(40, len(product_list)):])
        return res


class PrintStampsBarcodeLine(models.Model):
    _name = 'print.stamps.barcode.line'
    _description = 'Print Stamps Barcode Line'
    _order = 'print_barcode_id, product_id'

    print_barcode_id = fields.Many2one("print.stamps.barcode", string="Print Stamps Barcode", ondelete='cascade')
    product_id = fields.Many2one("product.product", string="Product", required=True, domain="[('barcode', 'not in', ('', False))]")
    barcode = fields.Char("Barcode", related='product_id.barcode', store=True)
    qty = fields.Integer("Qty", required=True, default=1)

    _sql_constraints = [
        ('check_qty', 'CHECK (qty >= 1)', 'Quantity must be greater than 1.')
    ]

    @api.onchange('qty')
    def onchange_qty(self):
        if self.qty < 1:
            self.qty = 1
