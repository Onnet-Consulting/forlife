from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.models import NewId
import json


class ProductDefectiveScan(models.TransientModel):
    _name = 'product.defective.scan'
    _description = "Product Defective Scan"

    pack_id = fields.Many2one('product.defective.pack',
                              default=lambda self: self.env.context.get('active_id'))
    department_id = fields.Many2one('hr.department', related='pack_id.department_id')
    defective_type_id = fields.Many2one(
        'defective.type', 'Defective Type', domain="[('department_id', 'in', [False, department_id])]")
    barcode = fields.Char('Barcode')
    warning_msg = fields.Text('Message Warning')
    on_value = fields.Text(default="{}")
    line_ids = fields.One2many('product.defective.scan.line', 'wizard_id')

    @api.onchange('barcode')
    def onchange_barcode(self):
        if self.barcode:
            line = self.line_ids.filtered(
                lambda r: r.barcode == self.barcode and r.defective_type_id.id == self.defective_type_id.id)
            if line:
                line_id = str(line.id if not isinstance(line.id, NewId) else line.id.origin)
                scan_val = json.loads(self.on_value or "{}")
                scan_val[line_id] += 1
                self.on_value = json.dumps(scan_val)
                # self.env.context = dict(**self.env.context, on_scan_value=[(k, v) for k, v in scan_val.items()])
                # line.quantity = scan_val[line_id]
                self.warning_msg = ''
            else:
                product = self.env['product.product'].search([('barcode', '=', self.barcode)], limit=1)
                if not product:
                    self.warning_msg = 'Barcode "%s" không hợp lệ!' % self.barcode
                else:

                    line = self.line_ids.create({
                        'wizard_id': self.id,
                        'product_id': product.id,
                        'barcode': product.barcode,
                        'quantity': 1,
                        'defective_type_id': self.defective_type_id.id
                    })
                    line_id = str(line.id if not isinstance(line.id, NewId) else line.id.origin)
                    if not self.on_value:
                        self.on_value = "{}"
                    scan_val = {**json.loads(self.on_value), line_id: 1}
                    self.on_value = json.dumps(scan_val)
                    # self.env.context = dict(**self.env.context, on_scan_value=[(k, v) for k, v in scan_val.items()])

                    self.warning_msg = ''
            self.barcode = ''

    def confirm_scan(self):
        if not self.line_ids:
            return
        if any(not line.defective_type_id for line in self.line_ids):
            raise ValidationError('Trường "Loại lỗi" bắt buộc !')
        scan_value = json.loads(self.on_value or {})
        line_values = [{
            'pack_id': self.pack_id.id,
            'store_id': self.pack_id.store_id.id,
            'product_id': line.product_id.id,
            'quantity_require': scan_value.get(str(line.id), 1),
            'defective_type_id': line.defective_type_id.id or False,
            'detail_defective': line.detail_defective
        } for line in self.line_ids]

        self.pack_id.write({
            'line_ids': [(0, 0, line) for line in line_values]
        })
        for line in self.pack_id.line_ids:
            line.change_product()


class ProductDefectiveScanLine(models.TransientModel):
    _name = 'product.defective.scan.line'

    wizard_id = fields.Many2one('product.defective.scan', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    barcode = fields.Char(required=True)
    quantity = fields.Float(compute='_compute_scan_quantity', inverse='_inverse_scan_quantity')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    department_id = fields.Many2one('hr.department', related='wizard_id.department_id')
    defective_type_id = fields.Many2one(
        'defective.type', 'Defective Type', domain="[('department_id', 'in', [False, department_id])]")
    detail_defective = fields.Char('Chi tiết lỗi')

    @api.depends('wizard_id.on_value', 'wizard_id')
    def _compute_scan_quantity(self):
        values = json.loads(self.wizard_id.on_value or "{}")
        for line in self:
            if str(line.id if not isinstance(line.id, NewId) else line.id.origin) in values:
                line.quantity = values[str(line.id if not isinstance(line.id, NewId) else line.id.origin)]
            else:
                line.quantity += 1

    def _inverse_scan_quantity(self):
        on_value = json.loads(self.wizard_id.on_value or "{}")
        for line in self:
            if on_value:
                if str(line.id if not isinstance(line.id, NewId) else line.id.origin) in on_value:
                    on_value[str(line.id if not isinstance(line.id, NewId) else line.id.origin)] += 1
                else:
                    on_value[str(line.id if not isinstance(line.id, NewId) else line.id.origin)] = 1
                self.wizard_id.on_value = json.dumps(on_value)
            line.quantity = line.quantity

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.barcode = self.product_id.barcode
        if self.wizard_id.defective_type_id:
            self.defective_type_id = self.wizard_id.defective_type_id

    @api.constrains('quantity')
    def check_required(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Số lượng sản phẩm phải lớn hơn 0 !')
