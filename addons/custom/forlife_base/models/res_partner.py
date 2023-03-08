# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResSupplierGroup(models.Model):
    _name = 'res.supplier.group'
    _inherit = "forlife.model.mixin"
    _description = "Supplier Group"


class SupplierProductType(models.Model):
    _name = 'supplier.product.type'
    _inherit = "forlife.model.mixin"
    _description = "Type of Supplier Product"


class ResPartner(models.Model):
    _inherit = 'res.partner'

    supplier_code = fields.Char(string="Supplier Code", copy=False)
    internal_code = fields.Char(string="Internal Code", copy=False)

    supplier_group_id = fields.Many2one('res.supplier.group', string="Supplier Group", copy=False)
    sup_product_type_id = fields.Many2one('supplier.product.type', string="Type of Supplier Product", copy=False)

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    # @api.constrains('supplier_code')
    # def _check_unique_supplier_code(self):
    #     suppliers = self.filtered(lambda sup: sup.supplier_rank > 0)
    #     if not suppliers:
    #         return

    #     self.flush_model(['supplier_code'])

    #     # /!\ Computed stored fields are not yet inside the database.
    #     self._cr.execute('''
    #         SELECT supplier2.id, supplier2.supplier_code
    #         FROM res_partner supplier
    #         INNER JOIN res_partner supplier2 ON
    #             supplier2.supplier_code = supplier.supplier_code
    #             AND supplier2.supplier_rank > 0
    #             AND supplier2.id != supplier.id
    #         WHERE supplier.id IN %s
    #     ''', [tuple(suppliers.ids)])
    #     res = self._cr.fetchall()
    #     if res:
    #         raise ValidationError(_('Supplier Code must be unique!.\n'
    #                                 'Problematic numbers: %s\n') % ', '.join(r[1] for r in res))
