from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_sku = fields.Char('SKU')
    date_off = fields.Date('Ngày hết hạn')
    warning_message = fields.Integer('Cảnh báo trước')
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
    sub_class_one_id = fields.Many2many('sub.class.one',string='Subclass1')
    sub_class_two_id = fields.Many2many('sub.class.two',string='Subclass2')
    sub_class_three_id = fields.Many2many('sub.class.three',string='Subclass3')
    sub_class_four_id = fields.Many2many('sub.class.four',string='Subclass4')
    sub_class_five_id = fields.Many2many('sub.class.five',string='Subclass5')
    sub_class_six_id = fields.Many2many('sub.class.six',string='Subclass6')
    sub_class_seven_id = fields.Many2many('sub.class.seven',string='Subclass7')
    sub_class_eight_id = fields.Many2many('sub.class.eight',string='Subclass8')
    sub_class_nine_id = fields.Many2many('sub.class.nine',string='Subclass9')
    sub_class_ten_id = fields.Many2many('sub.class.ten',string='Subclass10')
    properties_one_id = fields.Many2many('properties.one.product',string='Thuộc tính 1')
    properties_two_id = fields.Many2many('properties.two.product',string='Thuộc tính 2')
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


class SubClassOne(models.Model):
    _name = 'sub.class.one'


    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassTwo(models.Model):
    _name = 'sub.class.two'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassThree(models.Model):
    _name = 'sub.class.three'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassFour(models.Model):
    _name = 'sub.class.four'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassFive(models.Model):
    _name = 'sub.class.five'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassSix(models.Model):
    _name = 'sub.class.six'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassSeven(models.Model):
    _name = 'sub.class.seven'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassEight(models.Model):
    _name = 'sub.class.eight'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassNine(models.Model):
    _name = 'sub.class.nine'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class SubClassTen(models.Model):
    _name = 'sub.class.ten'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class PropertiesOneProduct(models.Model):
    _name = 'properties.one.product'

    code = fields.Char(string='Code', required=True)
    value = fields.Char('Giá trị')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Code must be unique!')
    ]

    def name_get(self):
        return [(rec.id, '%s' % rec.value) for rec in self]


class PropertiesTwoProduct(models.Model):
    _name = 'properties.two.product'

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
