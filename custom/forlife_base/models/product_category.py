# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductCategoryType(models.Model):
    _name = "product.category.type"
    _inherit = "forlife.model.mixin"
    _description = "Type of Product Category"


class ProductCategoryCode(models.Model):
    _name = "product.category.code"
    _inherit = "forlife.model.mixin"
    _description = "Code of Product Category"


class ProductCategorySequence(models.Model):
    _name = "product.category.sequece.level"
    _description = "Sequece of Product Category"

    level = fields.Integer()
    sequence = fields.Integer()

    _sql_constraints = [
        ('unique_level', 'UNIQUE(level)', 'Level must be unique!')
    ]


class ProductCategory(models.Model):
    _inherit = "product.category"

    category_code_id = fields.Many2one('product.category.code', string="Code of Product Category", copy=False)
    category_code = fields.Char(string="Code")
    category_type_id = fields.Many2one('product.category.type', string="Type of Product Category", copy=False)
    level = fields.Integer()
    current_code = fields.Char()
    default_account_manufacture = fields.Many2one('account.account', 'Tài khoản dịch vụ theo lệnh sản xuất')

    def write(self, vals):
        res = super(ProductCategory, self).write(vals)
        if 'level' not in vals:
            for category in self:
                category.write({'level': category._get_level()})
        if 'parent_id' in vals:
            self._compute_category_code()
        if 'category_type_id' in vals:
            self.filtered(lambda cag: not cag.parent_id)._compute_category_code()

        return res

    def _compute_level(self):
        for category in self:
            category.level = category._get_level()

    def _get_level(self):
        if not self.parent_id:
            return 1
        return self.parent_id._get_level() + 1

    def _get_parent_code(self):
        code = ''
        category = self
        while category.parent_id:
            category = category.parent_id
            if not category.parent_id:
                code = (category.category_code or '') + code
            else:
                code = (category.current_code or '') + code
        return code

    def _get_sequence_level(self, level):
        sequence_id = self.env['product.category.sequece.level'].search([('level', '=', level)], limit=1)
        if sequence_id:
            current_sequence = sequence_id.sequence + 1
            sequence_id.sudo().write({'sequence': current_sequence})
        else:
            current_sequence = 1
            self.env['product.category.sequece.level'].sudo().create({'level': level, 'sequence': 1})
        return current_sequence

    def _compute_category_code(self):
        for category in self:
            level = category._get_level()
            current_sequence = category._get_sequence_level(level)
            sequence_code = '{:03d}'.format(current_sequence)
            if not category.parent_id:
                category_code = sequence_code
                if category.category_type_id:
                    category_code = category.category_type_id.code + category_code
                else:
                    category_code = '0' + category_code
            else:
                category_code = category._get_parent_code() + sequence_code
            category.category_code = category_code
            category.current_code = sequence_code
            category.level = level
            # compute child
            if category.child_id:
                category.child_id._compute_category_code()
