from odoo import fields, api, models


class ForlifeProduction(models.Model):
    _inherit = 'forlife.production'

    material_import_ids = fields.One2many('production.material.import', 'production_id', copy=True)
    expense_import_ids = fields.One2many('production.expense.import', 'production_id', copy=True)

    def update_bom(self):
        product_fish = self.forlife_production_finished_product_ids
        material_import_ids = self.material_import_ids
        expense_import_ids = self.expense_import_ids
        for product in product_fish:
            product.update({
                'forlife_bom_material_ids': [(5, 0, 0)],
                'forlife_bom_service_cost_ids': [(5, 0, 0)]
            })
            material_vals = []
            for material in material_import_ids:
                bom_material_values = {}
                if (material.product_finish_id.id in product.mapped('product_id.id') or not material.product_finish_id) and (not material.size and not material.color):
                    bom_material_values.update({
                        'product_id': material.product_id.id,
                        'product_finish_id': material.product_finish_id.id,
                        'product_backup_id': material.product_backup_id.id,
                        'production_uom_id': material.production_uom_id.id,
                        'conversion_coefficient': material.conversion_coefficient,
                        'rated_level': material.rated_level,
                        'loss': material.loss,
                    })
                elif (material.size == product.size.name or material.color == product.color.name or (not material.size and not material.color)) and not material.product_finish_id:
                    bom_material_values.update({
                        'product_id': material.product_id.id,
                        'product_finish_id': material.product_finish_id.id,
                        'product_backup_id': material.product_backup_id.id,
                        'production_uom_id': material.production_uom_id.id,
                        'conversion_coefficient': material.conversion_coefficient,
                        'rated_level': material.rated_level,
                        'loss': material.loss,
                    })

                if bom_material_values:
                    material_vals.append((0, 0, bom_material_values))
            create_list_expense = []
            for expense in expense_import_ids:
                if expense.product_finish_id in product.mapped('product_id') or not expense.product_finish_id:
                    create_list_expense.append((0, 0, {
                        'product_id': expense.product_id.id,
                        'rated_level': expense.cost_norms
                    }))
            product.update({
                'forlife_bom_material_ids': material_vals,
                'forlife_bom_service_cost_ids': create_list_expense
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Cập nhật BOM thành công!.',
                'type': 'success',
                'sticky': False,
            }
        }


class ProductionMaterialImport(models.Model):
    _name = 'production.material.import'
    _description = "Production material import"

    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Mã NPL')
    product_backup_id = fields.Many2one('product.product', string='Mã NPL thay thế')
    product_finish_id = fields.Many2one('product.product', string='Thành phẩm')
    size = fields.Char(string='Size')
    color = fields.Char(string='Màu')
    uom_id = fields.Many2one('uom.uom', related="product_id.uom_id", string='ĐVT Lưu kho')
    production_uom_id = fields.Many2one('uom.uom', string='ĐVT Lệnh sản xuất')
    conversion_coefficient = fields.Float(string='HSQĐ')
    rated_level = fields.Float(string='Định mức')
    loss = fields.Float(string='Hao hụt')
    qty = fields.Float(string='Số lượng sản xuất')
    total = fields.Float(string='Tổng nhu cầu')

    @api.onchange('conversion_coefficient', 'rated_level', 'loss', 'qty')
    def _onchange_update_total(self):
        self.total = self.conversion_coefficient * self.rated_level * self.loss * self.qty


class ProductionExpenseImport(models.Model):
    _name = 'production.expense.import'
    _description = "Production expense import"

    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Chi phí')
    product_finish_id = fields.Many2one('product.product', string='Mã thành phẩm')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    quantity = fields.Float(string='Số lượng')
    cost_norms = fields.Float(string='Định mức')
    total_cost_norms = fields.Float(string='Tổng định mức')

    @api.onchange('quantity', 'total_cost_norms')
    def _onchange_update_cost_norms(self):
        if self.quantity > 0:
            self.cost_norms = self.total_cost_norms / self.quantity

    @api.onchange('quantity', 'cost_norms')
    def _onchange_update_total_cost_norms(self):
        self.total_cost_norms = self.quantity * self.cost_norms
