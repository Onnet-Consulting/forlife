from odoo import models, fields, api, _


class WarningPopup(models.TransientModel):
    _name = 'warning.popup'
    _description = 'Warning Popup'

    message = fields.Text()

