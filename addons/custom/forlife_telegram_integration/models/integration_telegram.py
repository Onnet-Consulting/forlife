# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class IntegrationTelegram(models.AbstractModel):
    _name = 'integration.telegram'
    _description = 'Integration with Telegram'

    # self.env['integration.telegram'].send_message(token='', chat_id='', message='')
    def send_message(self, token, chat_id, message):
        if not token:
            _logger.error('========= Telegram Bot Token not found =========')
            return False
        if not chat_id:
            _logger.error('========= Telegram Chat ID not found =========')
            return False
        if not message:
            _logger.error('========= Message text is empty =========')
            return False
        try:
            url = "https://api.telegram.org/bot{0}/sendMessage?chat_id={1}&text={2}".format(token, chat_id, message)
            result = requests.get(url)
            _logger.error('========= Send message to Telegram =========')
            _logger.error(json.loads(result.content))
        except Exception as e:
            _logger.error('========= Cannot send message to Telegram =========')
            _logger.error(e)
