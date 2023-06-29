# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = 'product combo'

    code = fields.Char('Combo code', readonly=True, copy=False, default='New')
    description_combo = fields.Text(string="Description combo")
    state = fields.Selection([
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('finished', _('Finished'))], string='State', default='new')
    from_date = fields.Datetime('From Date', required=True, default=fields.Datetime.now)
    to_date = fields.Datetime('To Date', required=True)
    combo_product_ids = fields.One2many('product.combo.line', 'combo_id', string='Combo Applied Products')
    size_attribute_id = fields.Many2one('product.attribute', string="Size Deviation Allowed",
                                        domain="[('create_variant', '=', 'always'), ('id', '!=', color_attribute_id)]")
    color_attribute_id = fields.Many2one('product.attribute', string="Color Deviation Allowed",
                                         domain="[('create_variant', '=', 'always'), ('id', '!=', size_attribute_id)]")

    _sql_constraints = [
        ('combo_check_date', 'CHECK(from_date <= to_date)', 'End date may not be before the starting date.')]

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('product.combo') or 'New'
        result = super(ProductCombo, self).create(vals)
        product_template_ids = self.constrains_combo({'from_date': result.from_date,
                                                      'to_date': result.to_date,
                                                      'id': result.id})
        if product_template_ids:
            for r in result.combo_product_ids:
                if r.product_id.id in product_template_ids:
                    raise ValidationError(_(f'Khoảng thời gian và sản phẩm {r.product_id.name_get()[0][1]} đã được khai báo trong bản ghi khác !'))
        return result

    def write(self, vals):
        rslt = super(ProductCombo, self).write(vals)
        product_template_ids = self.constrains_combo({'from_date': self.from_date,
                                                      'to_date': self.to_date,
                                                      'id': self.id})
        if product_template_ids:
            for r in self.combo_product_ids:
                if r.product_id.id in product_template_ids:
                    raise ValidationError(_(f'Khoảng thời gian và sản phẩm {r.product_id.name_get()[0][1]} đã được khai báo trong bản ghi khác !'))
        return rslt

    def constrains_combo(self, val):
        from_date = val['from_date']
        to_date = val['to_date']
        record_id = val['id']
        if from_date and to_date:
            sql = f"SELECT ptl.id, pc.id FROM product_combo pc " \
                  f" JOIN product_combo_line pcl on pcl.combo_id = pc.id " \
                  f" JOIN product_template ptl on ptl.id = pcl.product_id" \
                  f" WHERE (pc.from_date < '{from_date}' and pc.to_date > '{from_date}' and pc.to_date < '{to_date}')" \
                  f" OR (pc.from_date <= '{from_date}' and pc.to_date >= '{to_date}')" \
                  f" OR (pc.from_date < '{to_date}' and pc.to_date > '{to_date}' and pc.from_date > '{from_date}')"
            self._cr.execute(sql)
            data = self._cr.fetchall()
            product_template_ids = []
            if data:
                product_template_ids = [x[0] if x[1] != record_id else False for x in data]
            return product_template_ids
        return False

    def action_approve(self):
        pass

    def action_finished(self):
        pass
