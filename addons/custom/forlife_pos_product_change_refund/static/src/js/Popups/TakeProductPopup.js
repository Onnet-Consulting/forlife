odoo.define('forlife_pos_product_change_refund.TakePriceProductPopup', function (require) {
    "use strict";

    const { _t } = require('web.core');
    const { Orderline } = require('point_of_sale.models');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');
    var field_utils = require('web.field_utils');
    class TakePriceProductPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
        }

        cancel(){
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: false},
            });
        }

        onclickCheckbox(ev){
            $('.o_check').each(function(index) {
              if($(this).attr('value') != ev.currentTarget.value){
                   $(this).prop("checked", false);
              }
            });
        }

        confirm(){
            var product_defective_id;
            var products_defective = this.props.response
            var orderlines = this.env.pos.selectedOrder.orderlines
            var OrderCurrent = this.env.pos.get_order()
            $('.o_check').each(function(index) {
                if($(this).is(":checked")){
                   product_defective_id = parseInt($(this).attr('value'))
                }
            });
            if(product_defective_id){
                for(let i =0; i< products_defective.length; i++){
                    if(product_defective_id == products_defective[i].product_defective_id){
                        for(const line of orderlines) {
                            if(line.product.id == products_defective[i].product_id && line.quantity == 1){
                               line.money_reduce_from_product_defective = parseInt(products_defective[i].total_reduce)
                               line.is_product_defective = true
                               line.product_defective_id = products_defective[i].product_defective_id
                            }else if(line.product.id == products_defective[i].product_id && line.quantity > 1){
                                let line_new = Orderline.create({}, {pos: this.env.pos, order: OrderCurrent, product: line.product});
                                OrderCurrent.fix_tax_included_price(line_new);
                                let options_line_new = {
                                    pricelist_item : line.pricelist_item
                                }
                                OrderCurrent.set_orderline_options(line_new, options_line_new);
                                line_new.money_reduce_from_product_defective = parseInt(products_defective[i].total_reduce);
                                line_new.is_product_defective = true;
                                line_new.product_defective_id = products_defective[i].product_defective_id;
                                let quant = line.quantity -1;
                                line.quantity = quant;
                                line.quantityStr = field_utils.format.float(quant, { digits: [true, this.env.pos.dp['Product Unit of Measure']] });
                                OrderCurrent.add_orderline(line_new);
                            }
                        }
                    }
                }
            }
            this.env.pos.selectedOrder.product_defective_id = product_defective_id
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: false},
            });
        }

    }

    TakePriceProductPopup.template = "TakePriceProductPopup";
    TakePriceProductPopup.defaultProps = {
        cancelText: _t("Hủy"),
        confirmText: _t("Đồng ý")
    };
    Registries.Component.add(TakePriceProductPopup);

    return TakePriceProductPopup;
})