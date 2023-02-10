# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class ResGeneralInfo(models.AbstractModel):
    _name = 'res.general.info'
    _description = 'General Info'

    name = fields.Char('Name', required=True)
    value = fields.Char('Value', required=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Name must be unique"),
        ("value_uniq", "unique(value)", "Value must be unique")
    ]


class TelegramBot(models.Model):
    _name = 'telegram.bot'
    _inherit = 'res.general.info'
    _description = 'Telegram Bot'

    value = fields.Char('Token', required=True)


class TelegramGroup(models.Model):
    _name = 'telegram.group'
    _inherit = 'res.general.info'
    _description = 'Telegram Group'

    value = fields.Char('Group Id', required=True)


class IntegrationTelegram(models.Model):
    _name = 'integration.telegram'
    _description = 'Integration with Telegram'

    key = fields.Char('Key', required=True)
    bot_token_id = fields.Many2one('telegram.bot', string='Telegram Bot Token', required=True)
    group_chat_id = fields.Many2one('telegram.group', string='Telegram Group ID', required=True)

    _sql_constraints = [
        ("key_uniq", "unique(key)", "Key must be unique")
    ]

    def _get_telegram_info_by_key(self, key):
        return self.search([('key', '=', key)])


class ActionSendMessageTelegram(models.AbstractModel):
    _name = 'action.send.message.telegram'
    _description = 'Action Send Message Telegram'

    def action_send_message(self, key, message):
        telegram = self.env['integration.telegram']._get_telegram_info_by_key(key)
        if not telegram:
            raise ValueError(_("Can't find Telegram Info with key '%s'") % key)
        telegram = telegram[0]
        try:
            url = "https://api.telegram.org/bot{0}/sendMessage?chat_id={1}&text={2}".format(telegram.bot_token_id.value, telegram.group_chat_id.value, message)
            result = requests.get(url)
            _logger.error('========= Send message to Telegram =========')
            _logger.error(json.loads(result.content))
        except Exception as e:
            raise ValueError('========= Cannot send message to Telegram =========\n%s' % e)
