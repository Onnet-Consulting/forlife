# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class ResCountryState(models.Model):
    _name = 'res.country.state'
    _inherit = ['res.country.state', 'sync.address.info.rabbitmq']
    _new_action = 'new_city'
    _update_action = 'update_city'
    _remove_action = 'remove_city'


class ResStateDistrict(models.Model):
    _name = 'res.state.district'
    _inherit = ['res.state.district', 'sync.address.info.rabbitmq']
    _new_action = 'new_district'
    _update_action = 'update_district'
    _remove_action = 'remove_district'


class ResWard(models.Model):
    _name = 'res.ward'
    _inherit = ['res.ward', 'sync.address.info.rabbitmq']
    _new_action = 'new_ward'
    _update_action = 'update_ward'
    _remove_action = 'remove_ward'
