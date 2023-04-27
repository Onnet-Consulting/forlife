# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResCountryState(models.Model):
    _name = 'res.country.state'
    _inherit = ['res.country.state', 'sync.address.info.rabbitmq']
    _create_action = 'create_city'
    _update_action = 'update_city'
    _delete_action = 'delete_city'


class ResStateDistrict(models.Model):
    _name = 'res.state.district'
    _inherit = ['res.state.district', 'sync.address.info.rabbitmq']
    _create_action = 'create_district'
    _update_action = 'update_district'
    _delete_action = 'delete_district'


class ResWard(models.Model):
    _name = 'res.ward'
    _inherit = ['res.ward', 'sync.address.info.rabbitmq']
    _create_action = 'create_ward'
    _update_action = 'update_ward'
    _delete_action = 'delete_ward'
