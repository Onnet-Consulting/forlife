# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = 'product combo'

    name = fields.Char('Combo code', readonly=True, copy=False, default='New')
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
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('product.combo') or 'New'
        return super(ProductCombo, self).create(vals)

    def write(self, vals):
        return super(ProductCombo, self).write(vals)

    @api.constrains('combo_product_ids', 'from_date', 'to_date')
    def constrains_combo(self):
        for rec in self:
            from_date = rec.from_date
            to_date = rec.to_date
            sql = f"SELECT ptl.id, pc.id FROM product_combo pc " \
                  f" JOIN product_combo_line pcl on pcl.combo_id = pc.id " \
                  f" JOIN product_template ptl on ptl.id = pcl.product_id" \
                  f" WHERE (pc.from_date < '{from_date}' and pc.to_date > '{from_date}' and pc.to_date < '{to_date}')" \
                  f" OR (pc.from_date <= '{from_date}' and pc.to_date >= '{to_date}')" \
                  f" OR (pc.from_date < '{to_date}' and pc.to_date > '{to_date}' and pc.from_date > '{from_date}') " \
                  f" AND pc.state = 'in_progress'"
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
        self.ensure_one()
        self.state = 'in_progress'

    def action_finished(self):
        self.ensure_one()
        self.to_date = datetime.now()
        self.state = 'finished'

    @api.model
    def get_combo(self, vals):
        now = datetime.now()
        list_ids = []
        for rec in vals:
            list_ids.append(rec['product_tmpl_id'])
        if list_ids:
            if len(list_ids) == 1:
                list_ids = str(tuple(list_ids)).replace(',', '')
            else:
                list_ids = tuple(list_ids)
            sql_get_combo_from_product_pos = f"SELECT pc.id FROM product_combo pc " \
                                       f" JOIN product_combo_line pcl on pcl.combo_id = pc.id " \
                                       f" JOIN product_template ptl on ptl.id = pcl.product_id" \
                                       f" WHERE pc.from_date < '{now}' and pc.to_date > '{now}' " \
                                       f" and ptl.id in {list_ids} and pc.state = 'in_progress' "
            self._cr.execute(sql_get_combo_from_product_pos)
            datafetch = set(self._cr.fetchall())
            if datafetch:
                combo_ids = [x[0] for x in datafetch]
                if combo_ids:
                    if len(combo_ids) == 1:
                        combo_ids = str(tuple(combo_ids)).replace(',', '')
                    else:
                        combo_ids = tuple(combo_ids)
                sql_get_all_product_in_combo = f"SELECT pc.id as combo_id, pcl.product_id as product_tmpl_id, pcl.quantity  FROM product_combo pc " \
                                               f" JOIN product_combo_line pcl on pcl.combo_id = pc.id " \
                                               f" WHERE pc.id in {combo_ids}"
                self._cr.execute(sql_get_all_product_in_combo)
                product_ids_fetch = self._cr.dictfetchall()
                return product_ids_fetch
        return False
