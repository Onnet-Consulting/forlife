from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
    line_ids = fields.One2many('product.defective.scan.line', 'wizard_id')

    @api.onchange('barcode')
    def onchange_barcode(self):
        if self.barcode:
            line = self.line_ids.filtered(
                lambda r: r.barcode == self.barcode and r.defective_type_id.id == self.defective_type_id.id)
            if line:
                line.quantity = line.quantity + 1
                self.warning_msg = ''
            else:
                product = self.env['product.product'].search([('barcode', '=', self.barcode)], limit=1)
                if not product:
                    self.warning_msg = 'Barcode "%s" không hợp lệ!' % self.barcode
                else:
                    self.line_ids.create({
                        'wizard_id': self.id,
                        'product_id': product.id,
                        'barcode': product.barcode,
                        'quantity': 1,
                        'defective_type_id': self.defective_type_id.id
                    })
                    self.warning_msg = ''
            self.barcode = ''

    def confirm_scan(self):
        if not self.line_ids:
            return
        if any(not line.defective_type_id for line in self.line_ids):
            raise ValidationError('Trường "Loại lỗi" bắt buộc !')

        line_values = [{
            'pack_id': self.pack_id.id,
            'store_id': self.pack_id.store_id.id,
            'product_id': line.product_id.id,
            'quantity_require': line.quantity,
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
    quantity = fields.Float()
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    department_id = fields.Many2one('hr.department', related='wizard_id.department_id')
    defective_type_id = fields.Many2one(
        'defective.type', 'Defective Type', domain="[('department_id', 'in', [False, department_id])]")
    detail_defective = fields.Char('Chi tiết lỗi')

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
