# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class GeneralInfoMasterData(models.AbstractModel):
    _name = 'general.info.master.data'
    _description = 'General Info Master Data'

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Integer('Code', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Name already exists !'),
        ('code_uniq', 'unique (code)', 'Code already exists !'),
    ]


class MonthData(models.Model):
    _name = 'month.data'
    _inherit = 'general.info.master.data'
    _description = 'Month'


class DayOfMonthData(models.Model):
    _name = 'dayofmonth.data'
    _inherit = 'general.info.master.data'
    _description = 'DayOfMonth'


class DayOfWeekData(models.Model):
    _name = 'dayofweek.data'
    _inherit = 'general.info.master.data'
    _description = 'DayOfWeek'


class HourData(models.Model):
    _name = 'hour.data'
    _inherit = 'general.info.master.data'
    _description = 'Hour'
