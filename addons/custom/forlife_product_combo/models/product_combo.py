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
        return super(ProductCombo, self).create(vals)

    def write(self, vals):
        return super(ProductCombo, self).write(vals)

    @api.constrains('combo_product_ids','from_date','to_date')
    def constrains_combo(self):
        for rec in self:
            from_date = rec.from_date
            to_date = rec.to_date
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
                product_template_ids = [x[0] if x[1] != rec.id else False for x in data]
            for r in rec.combo_product_ids:
                if r.product_id.id in product_template_ids:
                    raise ValidationError(_(f'Khoảng thời gian và sản phẩm {r.product_id.name_get()[0][1]} đã được khai báo trong bản ghi khác !'))
            return product_template_ids

    def action_approve(self):
        pass

    def action_finished(self):
        pass
