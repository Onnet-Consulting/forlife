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
    "don_vi_uu_tien": "AT004",
    "mau_sac": "AT005",
    "anh_mau": "AT006",
    "size": "AT007",
    "tai_san_xuat": "AT008",
    "chat_luong": "AT009",
    "chat_lieu_vai_chinh": "AT010",
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
    "kenh_vung_ban": "AT032",
    "kich_thuoc": "AT033",
    "kho_vai": "AT034",
}'''

    attr_code_config = fields.Char(string='Attribute code config', config_parameter="attr_code_config", default=_get_default_attr_code_config)
