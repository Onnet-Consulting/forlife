# -*- coding:utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _get_default_attr_code_config(self):
        return '''{
    "doi_tuong": "AT001",
    "nhan_hieu": "AT002",
    "don_vi_tinh": "AT003",
    "don_vi_tinh2": "AT004",
    "mau_sac": "AT005",
    "anh_mau": "AT006",
    "size": "AT007",
    "tai_san_xuat": "AT008",
    "chat_luong": "AT009",
    "chat_lieu": "AT010",
    "subclass1": "AT011",
    "subclass2": "AT012",
    "subclass3": "AT013",
    "subclass4": "AT014",
    "subclass5": "AT015",
    "subclass6": "AT016",
    "subclass7": "AT017",
    "subclass8": "AT018",
    "subclass9": "AT019",
    "subclass10": "AT020",
    "thuoc_tinh1": "AT021",
    "thuoc_tinh2": "AT022",
    "muc_dich_su_dung": "AT023",
    "nha_thiet_ke": "AT024",
    "xuat_xu": "AT025",
    "nam_san_xuat": "AT026",
    "mua_vu": "AT027",
    "loai_hang_hoa": "AT028",
    "nguon_hang": "AT029",
    "mau_co_ban": "AT030",
    "mau_phoi": "AT031",
    "vung_ban_hang": "AT032",
    "kich_thuoc": "AT033",
    "san_pham_tach_ma": "AT034",
    "nganh_vai": "AT035",
    "mau_cu": "AT036",
    "kenh_ban_hang": "AT037",
    "menh_gia": "AT038",
    "tem_nhan": "AT039",
}'''

    @api.model
    def _get_default_attr_sequence_config(self):
        return ("['doi_tuong', 'nhan_hieu', 'mau_co_ban', 'mau_sac', 'anh_mau', 'mau_phoi', 'size', 'chat_luong', 'nam_san_xuat', 'nganh_vai', 'chat_lieu', "
                "'subclass1', 'subclass2', 'subclass3', 'subclass4', 'subclass5', 'subclass6', 'subclass7', 'subclass8', 'subclass9', 'subclass10', "
                "'thuoc_tinh1', 'thuoc_tinh2', 'muc_dich_su_dung', 'nha_thiet_ke', 'xuat_xu', 'mua_vu', 'loai_hang_hoa', 'nguon_hang', 'kenh_ban_hang', 'vung_ban_hang']")

    attr_code_config = fields.Char(string='Attribute code config', config_parameter="attr_code_config", default=_get_default_attr_code_config)
    attr_sequence_config = fields.Char(string='Attribute sequence config', config_parameter="attr_sequence_config", default=_get_default_attr_sequence_config)
