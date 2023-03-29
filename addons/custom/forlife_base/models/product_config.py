from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    description_color = fields.Char('Mô tả màu')
    material_composition = fields.Char('Thành phần chất liệu')
    cloth_code = fields.Char('Mã vải')
    collection = fields.Char('Bộ sưu tập')
    user_manual = fields.Char('Hướng dẫn sử dụng')
    note = fields.Text('Ghi chú')
    daisai = fields.Char('Dải sai')
    unit_priority_id = fields.Many2one('unit.priority', string='Đơn vị ưu tiên')
    uses_id = fields.Many2one('uses.product',string='Mục đích sử dụng')
    object_id = fields.Many2one('object.product',string='Đối tượng')
    branch_id = fields.Many2one('branch.product',string='Nhãn hiệu')
    fabric_id = fields.Many2one('main.fabric.material','Chất liệu vải chính')
    material_id = fields.Many2one('material.product',string='Thành phần chất liệu')
    designer_id = fields.Many2one('designer.product', 'Nhà thiết kế')
    origin_id = fields.Many2one('origin.product', 'Nguồn hàng')
    source_id = fields.Many2one('source.product', 'Xuất xứ')
    year_id = fields.Many2one('year.product','Năm sản xuất')
    season_id = fields.Many2one('season.product', 'Mùa vụ')
    type_id = fields.Many2one('type.product','Loại hàng hóa')


class FabricMaterial(models.Model):
    _name = 'main.fabric.material'
    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]




class UnitPriority(models.Model):
    _name = 'unit.priority'
    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]

class Uses(models.Model):
    _name = 'uses.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]

class ObjectProduct(models.Model):
    _name = 'object.product'


    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class BrandProduct(models.Model):
    _name = 'branch.product'
    _description = 'Nhãn hiệu'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class MaterialProduct(models.Model):
    _name = 'material.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]



class DesignerPro(models.Model):
    _name = 'designer.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class OriginProduct(models.Model):
    _name = 'origin.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SourceProduct(models.Model):
    _name = 'source.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class YearProduct(models.Model):
    _name = 'year.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SeasonProduct(models.Model):
    _name = 'season.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class TypeProduct(models.Model):
    _name = 'type.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]
