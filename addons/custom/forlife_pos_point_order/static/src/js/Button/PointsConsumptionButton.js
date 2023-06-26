odoo.define('forlife_pos_point_order.PointsConsumptionButton', function (require) {
    "use strict";

    const {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const rpc = require('web.rpc');


    class PointsConsumptionButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        get promotion () {
            var self = this;
            let data = {
                'session_id': self.env.pos.pos_session.id,
                'date_order': self.env.pos.selectedOrder.creation_date,
            }
            return rpc.query({
                model: 'pos.order',
                method: 'get_program_promotion',
                args: [data],
                context: {
                     from_PointsConsumptionPos :true
                }
            });
        }

        get order_lines(){
            return this.env.pos.get_order().get_orderlines();
        }

        async onClick() {
            if(!this.env.pos.selectedOrder.partner){
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(
                        this.env._t(
                            "Vui lòng chọn 1 khách hàng trước!"
                        ),
                        ''
                    ),
                });
                return;
            }
            if (!this.env.pos.pos_branch) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(
                        this.env._t(
                            "Chưa thiết lập chi nhánh cho POS này!"
                        ),
                        ''
                    ),
                });
                return;
            }
            var points_of_customer = null;
            for (let index = 0; index < this.env.pos.pos_branch.length; index++) {
                if(this.env.pos.pos_branch[index].name == "Format"){
                    points_of_customer = this.env.pos.selectedOrder.partner.total_points_available_format
                }else {
                    points_of_customer = this.env.pos.selectedOrder.partner.total_points_available_forlife
                }
            }
            var order_lines = this.order_lines;
            var promotion = await this.promotion;
            var product_valid_apply_all = [];
            var product_valid = [];
            var values = $('.o_input');
//                các sản phẩm hợp lệ được cấu hình
            for (let i=0; i< order_lines.length;i++){
                    for(let j=0;j<promotion.point_consumption_ids.length;j++){
                        if(order_lines[i].product.id == promotion.point_consumption_ids[j].id && !order_lines[i].is_product_defective){
                            product_valid.push(order_lines[i]);
                        }
                    }
            };

            for (let i=0; i< order_lines.length;i++){
                    if(!order_lines[i].is_product_defective){
                       product_valid_apply_all.push(order_lines[i])
                    }
            };
            var old_data_props = []
            let currentOrder = this.env.pos.selectedOrder;
            if (currentOrder._checkHasNotExistedLineOnOldData()) {
                currentOrder.resetPointOrder();
            };
            if(!this.env.pos.selectedOrder.old_data){
                old_data_props = false;
            }else{
                old_data_props = this.env.pos.selectedOrder.old_data
            }

            const {confirmed, payload: data} = await this.showPopup('PointsConsumptionPopup', {
                startingValue: this.order_lines,
                product_valid_apply_all: product_valid_apply_all,
                old_data_props: old_data_props,
                product_valid: product_valid,
                points_of_customer: points_of_customer,
                order: this.env.pos.get_order(),
                program_promotion: promotion,
                title: this.env._t('Tiêu điểm'),
                confirmTitle: this.env._t('Xác nhận '),
                divisionpoint: this.env._t('Chia điểm'),
                deleteTitle: this.env._t('Xóa'),
                cancelTitle: this.env._t('Hủy bỏ'),
            });
            if (confirmed){
                let order_lines = this.order_lines;
                var tempResult = {}
                for(let { id, point } of data){
                        tempResult[id] = {
                        id,
                        point: tempResult[id] ? point + (tempResult[id].point) : point,
                    }
                }
                let result = Object.values(tempResult)
                var OrderCurrent = this.env.pos.get_order()
//                var filteredDataItems = data.filter(item => item.point !== 0)
                var list_order_line_new = []
                if(!this.env.pos.selectedOrder.old_data){
                    for(let i = 0; i< data.length; i ++){
                        for(let j = 0; j< order_lines.length; j++){
                            if(!order_lines[j].is_product_defective){
                                if(order_lines[j].quantity == 1 && data[i].id == order_lines[j].id){
                                    order_lines[j].set_point(-data[i].point*1000)
                                    order_lines[j].is_new_line_point = false
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                                }
                                if(data[i].id == order_lines[j].id && data[i].point !==0 && order_lines[j].quantity >=2 ){
                                    let line = Orderline.create({}, {pos: this.env.pos, order: this.env.pos.get_order(), product: order_lines[j].product});
                                    let line_new = OrderCurrent.createNewLinePoint(line)
                                    // Set remaining quantity for the original orderline
                                    order_lines[j].set_quantity(order_lines[j].quantity - line_new.quantity)
                                    list_order_line_new.push({id: line_new.id, point:data[i].point})
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,line_new.id, true)
                                }
                                if(data[i].id == order_lines[j].id && data[i].point ==0){
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                                }
                            }
                        }
                    }
               }else{
                    for(let i =0; i< data.length;i++){
                        for(let j=0; j< order_lines.length;j++){
                            if(!order_lines[j].is_product_defective){
                                if(order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point !==0 ){
                                    order_lines[j].set_point(-data[i].point*1000)
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, true)
                                }else if(!order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point == 0){
                                    order_lines[j].set_point(0)
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                                }else if(!order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point !== 0 && order_lines[j].quantity >=2 ){
                                    let line = Orderline.create({}, {pos: this.env.pos, order: this.env.pos.get_order(), product: order_lines[j].product});
                                    let line_new = OrderCurrent.createNewLinePoint(line)
                                    // Set remaining quantity for the original orderline
                                    order_lines[j].set_quantity(order_lines[j].quantity - line_new.quantity)
                                    list_order_line_new.push({id: line_new.id, point:data[i].point})
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,line_new.id, true)
                                }else if(order_lines[j].is_new_line_point == true && data[i].id == order_lines[j].id && data[i].point == 0){
                                    order_lines[j].set_point(0)
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                                }else if(!order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point != 0){
                                    order_lines[j].set_point(-data[i].point*1000)
                                    this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                                }
                            }
                        }
                    }
               }
               for(let i=0; i< order_lines.length; i++){
                    for(let j=0; j< list_order_line_new.length;j++){
                        if(order_lines[i].id == list_order_line_new[j].id && !order_lines[i].is_product_defective){
                            order_lines[i].set_point(-list_order_line_new[j].point * 1000)
                            order_lines[i].is_new_line_point = true
                        }
                    }
               }

                this.env.pos.selectedOrder.old_data = data;
//                }

                //--------/
                var total_point_used = 0;
                order_lines.forEach(function(item){
                    if(!item.point){
                        item.point = 0;
                    }
                    if(item.point != 0){
                        if(item.card_rank_applied && item.card_rank_discount>0){
                            item.card_rank_applied = false;
                            item.card_rank_discount = 0;
                        }
                    }
                    let point = -item.point
                    total_point_used += point
                })
                OrderCurrent.detelte_history_point = true
                this.env.pos.selectedOrder.total_order_line_point_used = total_point_used/1000;
                this.env.pos.selectedOrder.total_order_line_redisual = points_of_customer - this.env.pos.selectedOrder.total_order_line_point_used
            }
        }

        set_param_old_data(data,display_name,price,index, id_new, is_new_line_point){
            data['display_name'] = display_name
            data['unit_price'] = price
            data['idx'] = index
            data['id_new'] = id_new
            data['is_new_line_point'] = is_new_line_point
            return data
        }


    }

    PointsConsumptionButton.template = 'PointsConsumptionButton';

    ProductScreen.addControlButton({
        component: PointsConsumptionButton,
        condition: function () {
            let order = this.env.pos && this.env.pos.get_order();
            let partner = order && order.get_partner();
            return partner && partner.generated_by_scan_barcode;
        },
    })

    Registries.Component.add(PointsConsumptionButton);

    return PointsConsumptionButton;
})