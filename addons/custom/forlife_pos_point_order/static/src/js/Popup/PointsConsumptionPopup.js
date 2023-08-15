odoo.define('forlife_pos_point_order.PointsConsumptionPopup', function (require) {
    "use strict";

    const { _t } = require('web.core');

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
                product_valid: this.props.product_valid,
                product_valid_apply_all: this.props.product_valid_apply_all,
                val_division_apply_all: this.props.val_division_apply_all,
                point_last_remainder_apply_all: this.props.point_last_remainder_apply_all,
                error_popup_flag: false,
                order: this.props.order,
            })
        }

        delete_val() {
            $('.o_input').val('')
        }

        cancel() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: null},
            });
        }

        division() {
            return this.push_value()
        }

        _is_applied_promotion(id) {
            let line = this.env.pos.get_order().get_orderlines().find(l => l.id == id);
            if (!line) {return false};
            return line.is_applied_promotion() || line.discount > 0;
        }

        push_value(){
            var promotion = this.props.program_promotion;
            var product_valid = this.props.product_valid;
            var product_valid_apply_all = this.props.product_valid_apply_all;
            var points_of_customer = this.props.points_of_customer;
            var quantity_product_apply_all = 0;
            var quantity_product_valid = 0;
            for (let index = 0; index < product_valid_apply_all.length; index++) {
                if(!product_valid_apply_all[index].is_product_defective){
                    quantity_product_apply_all += product_valid_apply_all[index].quantity
                }

            }
            for (let index = 0; index < product_valid.length; index++) {
                if(!product_valid[index].is_product_defective){
                    quantity_product_valid += product_valid[index].quantity
                }
            }
            var value = $('.o_input')
            if (promotion.approve_consumption_point){
                if(promotion.apply_all){
                    //  apply all
                    var val_division_apply_all = 0
                    val_division_apply_all = Math.floor(points_of_customer/quantity_product_apply_all);
                    var point_last_remainder_apply_all = 0
                    point_last_remainder_apply_all = val_division_apply_all+(points_of_customer % quantity_product_apply_all);
                    value.each(function( index ) {
                      if(index!==(value.length-1)){
                          $(this).val(val_division_apply_all)
                      }
                      if(index === (value.length-1)){
                          $(this).val(point_last_remainder_apply_all)
                      }
                    });
                }else {
                    //  apply product valid
                    var val_division_product_valid = 0
                    val_division_product_valid = Math.floor(points_of_customer/quantity_product_valid);
                    var point_last_remainder_product_valid = 0
                    point_last_remainder_product_valid = val_division_product_valid+(points_of_customer % quantity_product_valid);
                    value.each(function( index ) {
                      if(index!==(value.length-1)){
                          $(this).val(val_division_product_valid)
                      }
                      if(index === (value.length-1)){
                          $(this).val(point_last_remainder_product_valid)
                      }
                    });
                }
            }

    }

        confirm() {
            var total_points = parseInt($('#total').text())
            var values = $('.o_input');
            var obj=[];
            var self = this;
            self.state.error_popup_flag = false;
            self.error = self.env._t('')
            values.each(function( index ) {
               $(this).css('color', 'black')
            });
            values.each(function( index ) {
              if(parseInt($(this).attr('data-value_id'))/1000 < parseInt($(this).val())){
                    self.state.error_popup_flag = true;
                    self.error = self.env._t('Điểm sử dụng không được lớn hơn số điểm quy đổi của sản phẩm!')
                    $(this).css('color', 'red')
              };
            });
            var total = 0;
            values.each(function( index ) {
               if ($(this).val()){
                  total += parseInt($(this).val());
               }
            });
            if (this.env.pos.pos_branch[0].name == "Format"){
               if (total > this.props.order.partner.total_points_available_format){
                    self.state.error_popup_flag = true;
                    self.error = self.env._t('Tổng điểm sử dụng lớn hơn điểm đang có!')
               }
            }
            if (this.env.pos.pos_branch[0].name == "TokyoLife"){
               if (total > this.props.order.partner.total_points_available_forlife){
                    self.state.error_popup_flag = true;
                    self.error = self.env._t('Tổng điểm sử dụng lớn hơn điểm đang có!')
               }
            }
            values.each(function( index ) {
              obj.push({
                  id: parseInt($(this).attr('id')),
                  point: parseInt($(this).val())
              })
            });
            for(let i=0; i< obj.length; i++){
                    if(!obj[i].point){
                        obj[i].point=0
                    }
            }
            if(self.state.error_popup_flag) return;
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: true, payload: obj},
            });
        }

    }

    PointsConsumptionPopup.template = "PointsConsumptionPopup";
    PointsConsumptionPopup.defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Point")
    };
    Registries.Component.add(PointsConsumptionPopup);

    return PointsConsumptionPopup;
})