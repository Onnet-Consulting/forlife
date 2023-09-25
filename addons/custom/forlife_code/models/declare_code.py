from datetime import datetime, timedelta
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class DeclareCode(models.Model):
    _name = 'declare.code'
    _description = 'Declare Documents code'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Tên', required=True, tracking=True)
    active = fields.Boolean(default=True,string='Trạng thái')
    category_id = fields.Many2one('declare.category', string='Nhóm mã CT', required=True, tracking=True)
    company_id = fields.Many2one('res.company',string='Công ty',tracking=True)

    is_journal = fields.Boolean('Sinh mã theo sổ nhật ký', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Sổ nhật ký', tracking=True)
    select_prefix = fields.Selection([('1', '1'),
                                    ('2', '2'),
                                    ('3', '3'),
                                    ('4', '4'),
                                    ('5', '5')],string='SL tiền tố', default='3', required=True, tracking=True)
    count_prefix = fields.Integer('SL tiền tố', compute='_compute_count_prefix')
    draft_prefix = fields.Char('Mã dự tính', readonly=True, tracking=True)
    #11111111111
    prefix_1 = fields.Char('(1) - Mã, Miền', required=True,tracking=True)
    #22222222222
    select_prefix_2 = fields.Selection([('domain', 'Miền'),
                                        ('sequence', 'Số tự tăng'),
                                        ('location_src', 'Mã kho nguồn'),
                                        ('location_des', 'Mã kho đích')],string='(2) - Lựa chọn tiền tố', default='sequence', tracking=True)
    prefix_2 = fields.Char('(2) - Mã, Miền',tracking=True)
    prefix_sequence_2 = fields.Integer('(2) - Độ dài',tracking=True)
    #33333333333
    select_prefix_3 = fields.Selection([('domain', 'Miền'),
                                        ('sequence', 'Số tự tăng'),
                                        ('location_src', 'Mã kho nguồn'),
                                        ('location_des', 'Mã kho đích')],string='(3) - Lựa chọn tiền tố', default='sequence', tracking=True)
    prefix_3 = fields.Char('(3) - Mã, Miền',tracking=True)
    prefix_sequence_3 = fields.Integer('(3) - Độ dài',tracking=True)
    #44444444444
    select_prefix_4 = fields.Selection([('domain', 'Miền'),
                                        ('sequence', 'Số tự tăng'),
                                        ('location_src', 'Mã kho nguồn'),
                                        ('location_des', 'Mã kho đích')],string='(4) - Lựa chọn tiền tố', default='sequence', tracking=True)
    prefix_4 = fields.Char('(4) - Mã, Miền',tracking=True)
    prefix_sequence_4 = fields.Integer('(4) - Độ dài',tracking=True)
    #55555555555
    select_prefix_5 = fields.Selection([('domain', 'Miền'),
                                        ('sequence', 'Số tự tăng'),
                                        ('location_src', 'Mã kho nguồn'),
                                        ('location_des', 'Mã kho đích')],string='(4) - Lựa chọn tiền tố', default='sequence', tracking=True)
    prefix_5 = fields.Char('(5) - Mã, Miền',tracking=True)
    prefix_sequence_5 = fields.Integer('(5) - Độ dài',tracking=True)


    @api.depends('select_prefix')
    def _compute_count_prefix(self):
        for item in self:
            item.count_prefix = int(item.select_prefix)

    @api.onchange('select_prefix','prefix_1','prefix_2','prefix_3','prefix_4','prefix_5',
                  'select_prefix_2','select_prefix_3','select_prefix_4','select_prefix_5',
                  'prefix_sequence_2','prefix_sequence_3','prefix_sequence_4','prefix_sequence_5')
    def _onchange_draft_prefix(self):
        for item in self:
            prefix, len_sequence = item._get_code('','3001','3001')
            item.draft_prefix = prefix + 'x'*len_sequence

    def _get_prefix(self, prefix, date=None, date_range=None):
        if '%' not in prefix:
            return prefix
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            now = range_date = effective_date = datetime.now(pytz.timezone(self._context.get('tz') or 'UTC'))
            if date or self._context.get('ir_sequence_date'):
                effective_date = fields.Datetime.from_string(date or self._context.get('ir_sequence_date'))
            if date_range or self._context.get('ir_sequence_date_range'):
                range_date = fields.Datetime.from_string(date_range or self._context.get('ir_sequence_date_range'))

            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'
            }
            res = {}
            for key, format in sequences.items():
                res[key] = effective_date.strftime(format)
                res['range_' + key] = range_date.strftime(format)
                res['current_' + key] = now.strftime(format)

            return res

        self.ensure_one()
        d = _interpolation_dict()
        try:
            interpolated_prefix = _interpolate(prefix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for domain \'%s\'') % prefix)
        return interpolated_prefix
    
    def _get_code_by_select_prefix(self, select_prefix, code,prefix_sequence, location_code, location_des_code):
        prefix = ''
        len_sequence = 0
        if select_prefix == 'domain':
            if code:
                prefix += self._get_prefix(code)
        elif select_prefix == 'sequence':
            len_sequence = prefix_sequence
        elif select_prefix == 'location_src':
            if location_code:
                prefix += location_code
        elif select_prefix == 'location_des':
            if location_des_code:
                prefix += location_des_code
        return prefix, len_sequence

    def _get_code(self, code='', location_code='', location_des_code=''):
        try:
            count_prefix = int(self.select_prefix)
            prefix = ''
            len_sequence = 0
            if count_prefix >= 1:
                if self.prefix_1:
                    prefix += self._get_prefix(self.prefix_1)
            if count_prefix >= 2:
                sub_prefix_2, len_sequence = self._get_code_by_select_prefix(self.select_prefix_2, self.prefix_2, self.prefix_sequence_2, location_code, location_des_code)
                prefix += sub_prefix_2
            if count_prefix >= 3:
                sub_prefix_3, new_len_sequence = self._get_code_by_select_prefix(self.select_prefix_3, self.prefix_3, self.prefix_sequence_3, location_code, location_des_code)
                if len_sequence != 0:
                    raise UserError('Tiền tố 2 đã là dãy số tự tăng!')
                len_sequence = new_len_sequence
                prefix += sub_prefix_3
            if count_prefix >= 4:
                sub_prefix_4, new_len_sequence = self._get_code_by_select_prefix(self.select_prefix_4, self.prefix_4, self.prefix_sequence_4, location_code, location_des_code)
                if len_sequence != 0:
                    raise UserError('Tiền tố 3 đã là dãy số tự tăng!')
                len_sequence = new_len_sequence
                prefix += sub_prefix_4
            if count_prefix >= 5:
                sub_prefix_5, new_len_sequence = self._get_code_by_select_prefix(self.select_prefix_5, self.prefix_5, self.prefix_sequence_5, location_code, location_des_code)
                if len_sequence != 0:
                    raise UserError('Tiền tố 4 đã là dãy số tự tăng!')
                len_sequence = new_len_sequence
                prefix += sub_prefix_5
            return prefix, len_sequence
        except ValueError:
            raise UserError('Có vấn đề trong quá trình tính toán mã phiếu. Vui lòng liên hệ quản trị viên')
    
    def genarate_code(self, model_code, field_code, location_code='', location_des_code=''):
        code, len_sequence = self._get_code(field_code, location_code, location_des_code)
        try:
            param_code = code+'%'
            start_code = '0'*len_sequence
            query = f""" 
                SELECT code
                FROM (
                    (SELECT '{start_code}' as code)
                    UNION ALL
                    (SELECT RIGHT({field_code},{len_sequence}) as code
                    FROM {model_code}
                    WHERE {field_code} like '{param_code}'
                    ORDER BY {field_code} desc
                    LIMIT 1)) as c
                ORDER BY code desc LIMIT 1
            """
            self._cr.execute(query)
            result = self._cr.fetchall()
            for list_code in result:
                if list_code[0] == start_code:
                    code+='0'*(len_sequence - 1)+'1'
                else:
                    code_int = int(list_code[0])+1
                    code+='0'*(len_sequence-len(str(code_int)))+str(code_int)
            return code
        except ValueError:
            raise UserError('Có vấn đề trong quá trình tính toán mã phiếu. Vui lòng liên hệ quản trị viên')
    
    def _get_declare_code(self, code, company_id=False, journal_id=False):
        declare_code_id = False
        domain = []
        if code:
            domain = [('active','=', True),('category_id.code','=',code)]
            if company_id:
                domain.append(('company_id','=',company_id))
        if journal_id:
            domain = [('active','=', True),('journal_id','=',journal_id)]
        if domain:
            declare_code_id = self.search(domain,order='id desc',limit=1)
        return declare_code_id