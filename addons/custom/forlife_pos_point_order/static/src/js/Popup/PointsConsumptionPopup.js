odoo.define('forlife_pos_point_order.PointsConsumptionPopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');


    class PointsConsumptionPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({
                startingValue: this.props.startingValue,
                program_promotion: this.props.program_promotion,
                points_of_customer: this.props.points_of_customer,
                product_valid:this.props.product_valid,
                orderlines: this.props.orderlines,
            })
        }

        cancel() {
            this.delete_value()
            console.log($('.o_input'))
            $('.o_input').val('')
            this.env.posbus.trigger('', {
                popupId: this.props.id,
                response: {confirmed: false, payload: null},
            });
        }

        division() {
            return this.push_value()
        }

        push_value(){
            var promotion = this.props.program_promotion;
            var product_valid = this.props.product_valid;
            var points_of_customer = this.props.points_of_customer;
            var val_division_apply_all = Math.floor(points_of_customer/this.env.pos.selectedOrder.orderlines.length);
            var val_division_product_valid = Math.floor(points_of_customer/product_valid.length);
            if (promotion.approve_consumption_point){
                if(promotion.apply_all){
                    for(let i=0; i< this.env.pos.selectedOrder.orderlines.length-1;i++){
                        this.env.pos.selectedOrder.orderlines[i].point=val_division_apply_all;
                    }
                    this.env.pos.selectedOrder.orderlines[this.env.pos.selectedOrder.orderlines.length-1].point= val_division_apply_all+(points_of_customer % this.env.pos.selectedOrder.orderlines.length);
                }else{
                    for (let index = 0; index < product_valid.length-1; index++) {
                        product_valid[index].point= val_division_product_valid;
                    }
                    product_valid[product_valid.length-1].point = val_division_product_valid + (points_of_customer % product_valid.length);
                }
            }
            this.state.product_valid = product_valid
            this.state.orderlines = this.env.pos.selectedOrder.orderlines
        }

        delete_value(){
            var product_valid = this.props.product_valid;
            for(let i=0; i< this.env.pos.selectedOrder.orderlines.length;i++){
                this.env.pos.selectedOrder.orderlines[i].point='';
            }
            for (let index = 0; index < product_valid.length-1; index++) {
                product_valid[index].point= '';
            }
            this.state.product_valid = product_valid
            this.state.orderlines = this.env.pos.selectedOrder.orderlines
        }

        confirm() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: true, payload: {key: 3}},
            });
        }

    }

    PointsConsumptionPopup.template = "PointsConsumptionPopup";
    PointsConsumptionPopup.defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Employee")
    };
    Registries.Component.add(PointsConsumptionPopup);

    return PointsConsumptionPopup;
})