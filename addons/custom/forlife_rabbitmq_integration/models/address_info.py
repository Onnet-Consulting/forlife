# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResCountryState(models.Model):
    _name = 'res.country.state'
    _inherit = ['res.country.state', 'sync.address.info.rabbitmq']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    @api.model
    def domain_record_sync_info(self):
        return [('country_id.code', '=', 'VN')]


class ResStateDistrict(models.Model):
    _name = 'res.state.district'
    _inherit = ['res.state.district', 'sync.address.info.rabbitmq']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    @api.model
    def domain_record_sync_info(self):
        return [('state_id.country_id.code', '=', 'VN')]


class ResWard(models.Model):
    _name = 'res.ward'
    _inherit = ['res.ward', 'sync.address.info.rabbitmq']
    _create_action = 'create'
    _update_action = 'update'
    _delete_action = 'delete'

    @api.model
    def domain_record_sync_info(self):
        return [('district_id.state_id.country_id.code', '=', 'VN')]
