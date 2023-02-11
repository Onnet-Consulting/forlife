# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command

from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby
from odoo.addons.stock.models.stock_move_line import StockMoveLine as InheritStockMoveLine


def _action_done(self):
    """ This method is called during a move's `action_done`. It'll actually move a quant from
    the source location to the destination location, and unreserve if needed in the source
    location.

    This method is intended to be called on all the move lines of a move. This method is not
    intended to be called when editing a `done` move (that's what the override of `write` here
    is done.
    """
    Quant = self.env['stock.quant']

    # First, we loop over all the move lines to do a preliminary check: `qty_done` should not
    # be negative and, according to the presence of a picking type or a linked inventory
    # adjustment, enforce some rules on the `lot_id` field. If `qty_done` is null, we unlink
    # the line. It is mandatory in order to free the reservation and correctly apply
    # `action_done` on the next move lines.
    ml_ids_tracked_without_lot = OrderedSet()
    ml_ids_to_delete = OrderedSet()
    ml_ids_to_create_lot = OrderedSet()
    for ml in self:
        # Check here if `ml.qty_done` respects the rounding of `ml.product_uom_id`.
        uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')
        if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
            raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision '
                              'defined on the unit of measure "%s". Please change the quantity done or the '
                              'rounding precision of your unit of measure.') % (
                            ml.product_id.display_name, ml.product_uom_id.name))

        qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
        if qty_done_float_compared > 0:
            if ml.product_id.tracking != 'none':
                picking_type_id = ml.move_id.picking_type_id
                if picking_type_id:
                    if picking_type_id.use_create_lots:
                        # If a picking type is linked, we may have to create a production lot on
                        # the fly before assigning it to the move line if the user checked both
                        # `use_create_lots` and `use_existing_lots`.
                        if ml.lot_name and not ml.lot_id:
                            lot = self.env['stock.lot'].search([
                                ('company_id', '=', ml.company_id.id),
                                ('product_id', '=', ml.product_id.id),
                                ('name', '=', ml.lot_name),
                            ], limit=1)
                            if lot:
                                ml.lot_id = lot.id
                            else:
                                ml_ids_to_create_lot.add(ml.id)
                    elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
                        # If the user disabled both `use_create_lots` and `use_existing_lots`
                        # checkboxes on the picking type, he's allowed to enter tracked
                        # products without a `lot_id`.
                        continue
                elif ml.is_inventory:
                    # If an inventory adjustment is linked, the user is allowed to enter
                    # tracked products without a `lot_id`.
                    continue

                if not ml.lot_id and ml.id not in ml_ids_to_create_lot:
                    ml_ids_tracked_without_lot.add(ml.id)
        elif qty_done_float_compared < 0:
            raise UserError(_('No negative quantities allowed'))
        elif not ml.is_inventory:
            ml_ids_to_delete.add(ml.id)

    if ml_ids_tracked_without_lot:
        mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
        raise UserError(_('You need to supply a Lot/Serial Number for product: \n - ') +
                        '\n - '.join(mls_tracked_without_lot.mapped('product_id.display_name')))
    ml_to_create_lot = self.env['stock.move.line'].browse(ml_ids_to_create_lot)
    ml_to_create_lot.with_context(do_not_unreserve=True)._create_and_assign_production_lot()

    mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
    mls_to_delete.unlink()

    mls_todo = (self - mls_to_delete)
    mls_todo._check_company()

    # Now, we can actually move the quant.
    ml_ids_to_ignore = OrderedSet()
    for ml in mls_todo:
        if ml.product_id.type == 'product':
            rounding = ml.product_uom_id.rounding

            # if this move line is force assigned, unreserve elsewhere if needed
            if not ml.move_id._should_bypass_reservation(ml.location_id) and float_compare(ml.qty_done,
                                                                                           ml.reserved_uom_qty,
                                                                                           precision_rounding=rounding) > 0:
                qty_done_product_uom = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id,
                                                                           rounding_method='HALF-UP')
                extra_qty = qty_done_product_uom - ml.reserved_qty
                ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id,
                                     package_id=ml.package_id, owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
            # unreserve what's been reserved
            if not ml.move_id._should_bypass_reservation(
                    ml.location_id) and ml.product_id.type == 'product' and ml.reserved_qty:
                Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.reserved_qty, lot_id=ml.lot_id,
                                                package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

            # move what's been actually done
            quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id,
                                                           rounding_method='HALF-UP')
            available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity,
                                                                      lot_id=ml.lot_id, package_id=ml.package_id,
                                                                      owner_id=ml.owner_id)
            if available_qty < 0 and ml.lot_id:
                # see if we can compensate the negative quants with some untracked quants
                untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False,
                                                              package_id=ml.package_id, owner_id=ml.owner_id,
                                                              strict=True)
                if untracked_qty:
                    taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                    Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty,
                                                     lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                    Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty,
                                                     lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
            Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id,
                                             package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)
        ml_ids_to_ignore.add(ml.id)
    # Reset the reserved quantity as we just moved it to the destination location.
    mls_todo.with_context(bypass_reservation_update=True).write({
        'reserved_uom_qty': 0.00,
    })


InheritStockMoveLine._action_done = _action_done
