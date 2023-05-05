# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

no_data = '<h1 style="text-align: center; color: red;">Khách hàng chưa có thông tin hạng thẻ</h1>'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    card_rank_ids = fields.One2many('partner.card.rank', inverse_name='customer_id', string='Card Rank')
    card_rank_format = fields.Html('Card Rank Format', compute='_compute_card_rank')
    card_rank_tokyolife = fields.Html('Card Rank TokyoLife', compute='_compute_card_rank')
    card_rank_by_brand = fields.Json('Card Rank By Brand', compute='_compute_card_rank')
    card_rank_status_format = fields.Boolean('Card Rank Status Format', compute='_compute_card_rank')
    card_rank_status_tokyolife = fields.Boolean('Card Rank Status Tokyolife', compute='_compute_card_rank')

    def _compute_card_rank(self):
        for line in self:
            data = line.card_rank_ids.generate_card_rank_data()
            line.card_rank_format = data.get(f'{self.env.ref("forlife_point_of_sale.brand_format").code}-{str(line.id)}', no_data)
            line.card_rank_tokyolife = data.get(f'{self.env.ref("forlife_point_of_sale.brand_tokyolife").code}-{str(line.id)}', no_data)
            line.card_rank_by_brand = {r.brand_id.id: [r.card_rank_id.id, r.card_rank_id.name] for r in line.card_rank_ids}
            card_rank_format = line.card_rank_ids.filtered(lambda x: x.brand_id == self.env.ref("forlife_point_of_sale.brand_format"))
            card_rank_tokyolife = line.card_rank_ids.filtered(lambda x: x.brand_id == self.env.ref("forlife_point_of_sale.brand_tokyolife"))
            line.card_rank_status_format = True if (card_rank_format and any(x.status for x in card_rank_format)) else False
            line.card_rank_status_tokyolife = True if (card_rank_tokyolife and any(x.status for x in card_rank_tokyolife)) else False

    def btn_change_card_rank(self):
        partner_card_rank = self.validate_brand_info()
        ctx = dict(self._context)
        ctx.update({
            'default_partner_card_rank_id': partner_card_rank.id,
            'default_old_card_rank_id': partner_card_rank.card_rank_id.id,
            'brand_id': partner_card_rank.brand_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Card Rank'),
            'res_model': 'partner.card.rank.line',
            'target': 'new',
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_customer_card_rank.partner_card_rank_line_view_form_update_manual').id, 'form']],
            'context': ctx,
        }

    def btn_view_detail_card_rank(self):
        partner_card_rank = self.validate_brand_info()
        ctx = dict(self._context)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner Card Rank'),
            'res_model': 'partner.card.rank',
            'target': 'current',
            'res_id': partner_card_rank.id,
            'view_mode': 'form',
            'views': [[self.env.ref('forlife_customer_card_rank.partner_card_rank_view_form').id, 'form']],
            'context': ctx,
        }

    def validate_brand_info(self):
        self.ensure_one()
        brand_xml_id = self._context.get('brand_xml_id')
        if not brand_xml_id:
            raise ValidationError(_("Brand XML ID not found"))
        brand = self.env.ref(brand_xml_id)
        if not brand:
            raise ValidationError(_("Brand by XML ID '%s' not found") % brand_xml_id)
        partner_card_rank = self.card_rank_ids.filtered(lambda f: f.brand_id == brand)
        if not partner_card_rank:
            raise ValidationError(_("Card Rank for '%s' brand not found") % brand.name)
        return partner_card_rank[0]
