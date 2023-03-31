from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    other_export_id = fields.Many2one('stock.picking.type', 'Other Export', check_company=True)
    other_import_id = fields.Many2one('stock.picking.type', 'Other Import', check_company=True)

    def _get_picking_type_update_values(self):
        input_loc, output_loc = self._get_input_output_locations(self.reception_steps, self.delivery_steps)
        res = super()._get_picking_type_update_values()
        res.update({
            'other_export_id': {
                'default_location_src_id': input_loc.id,
                'barcode': self.code.replace(" ", "").upper() + "-OTHER EXPORT",
            },
            'other_import_id': {
                'default_location_dest_id': input_loc.id,
                'barcode': self.code.replace(" ", "").upper() + "-OTHER IMPORT",
            }
        })
        return res

    def _get_picking_type_create_values(self, max_sequence):
        """ When a warehouse is created this method return the values needed in
        order to create the new picking types for this warehouse. Every picking
        type are created at the same time than the warehouse howver they are
        activated or archived depending the delivery_steps or reception_steps.
        """
        input_loc, output_loc = self._get_input_output_locations(self.reception_steps, self.delivery_steps)
        res = super(Warehouse, self)._get_picking_type_create_values(max_sequence)
        res[0].update(
            {
                'other_export_id': {
                    'name': _('Other Export'),
                    'code': 'outgoing',
                    'use_create_lots': True,
                    'use_existing_lots': False,
                    'default_location_dest_id': False,
                    'sequence': max_sequence + 7,
                    'show_reserved': False,
                    'show_operations': False,
                    'sequence_code': 'EX_OTHER',
                    'company_id': self.company_id.id,
                },
                'other_import_id': {
                    'name': _('Other Import'),
                    'code': 'incoming',
                    'use_create_lots': True,
                    'use_existing_lots': False,
                    'default_location_src_id': False,
                    'sequence': max_sequence + 8,
                    'show_reserved': False,
                    'show_operations': False,
                    'sequence_code': 'IN_OTHER',
                    'company_id': self.company_id.id,
                }
            }
        )
        return res

    def _get_sequence_values(self, name=False, code=False):
        name = name if name else self.name
        code = code if code else self.code
        res = super()._get_sequence_values()
        res.update({
            'other_export_id': {
                'name': name + ' ' + _('Sequence Other Export'),
                'prefix': code + '/OTH EX/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'other_import_id': {
                'name': name + ' ' + _('Sequence Other Import'),
                'prefix': code + '/OTH IM/', 'padding': 5,
                'company_id': self.company_id.id,
            }
        })
        return res