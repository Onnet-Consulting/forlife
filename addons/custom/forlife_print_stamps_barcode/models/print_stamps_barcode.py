# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PrintStampsBarcode(models.Model):
    _name = 'print.stamps.barcode'
    _rec_name = 'create_date'
    _description = 'Print Stamps Barcode'

    create_uid = fields.Many2one(comodel_name="res.users", string="Create By", default=lambda s: s.env.user)
    approve_uid = fields.Many2one(comodel_name="res.users", string="Approve By")
    create_date = fields.Datetime(string="Create Date", default=fields.Datetime.now())
    start_print = fields.Integer(string="Start Print", required=True, default=1)
    state = fields.Selection(string="State", selection=[('draft', _('Draft')), ('approved', _('Approved'))], default='draft')
    view = fields.Html('View', compute='compute_view')
    line_ids = fields.One2many(comodel_name="print.stamps.barcode.line", inverse_name="print_barcode_id", string="Lines")

    _sql_constraints = [
        ('check_start_print', 'CHECK(start_print >= 1 and start_print <= 40)', _('Start Print must be between 1 and 40'))
    ]

    @api.depends('line_ids', 'start_print')
    def compute_view(self):
        for line in self:
            total = sum(line.line_ids.mapped('qty')) + line.start_print
            res = ''
            ind = 1
            for row in range(10):
                rows = ''
                for col in range(4):
                    rows += ('<th style="background-color: #8d9cfc;">' if (ind >= line.start_print and ind < total) else '<th>') + str(ind) + '</th>'
                    ind += 1
                res += '<tr>' + rows + '</tr>'
            line.view = '<table class="table table-bordered text-center">' + res + '</table>'

    def btn_approve(self):
        self.ensure_one()
        if self.state == 'approved':
            return True
        quantity = sum(self.line_ids.mapped('qty')) + self.start_print - 1
        if quantity > 40:
            raise ValidationError(_("Only %s codes can be printed if starting from %s position") % (40 - self.start_print + 1, self.start_print))
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
        product_list += [(0, 0)] * (40 - (sum(self.line_ids.mapped('qty')) + self.start_print - 1))
        return product_list


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
