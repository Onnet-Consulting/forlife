odoo.define('forlife_pos_point_order.PointsConsumptionButton', function (require) {
    "use strict";


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
                        if(order_lines[i].product.id == promotion.point_consumption_ids[j].id){
                            product_valid.push(order_lines[i]);
                        }
                    }
            };

            for (let i=0; i< order_lines.length;i++){
                    product_valid_apply_all.push(order_lines[i])
            };

            const {confirmed, payload: data} = await this.showPopup('PointsConsumptionPopup', {
                startingValue: this.order_lines,
                product_valid_apply_all: product_valid_apply_all,
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
                var tempResult = {}
                for(let { id, point } of data){
                        tempResult[id] = {
                        id,
                        point: tempResult[id] ? point + (tempResult[id].point) : point,
                        // count: tempResult[id] ? tempResult[id].count + 1 : 1
                    }
                }
                let result = Object.values(tempResult)
                let order_lines = this.order_lines;
                if (result.length < order_lines.length){
                    for(let i = 0; i< order_lines.length; i++){
                        for(let j = 0; j< result.length; j++){
                            if (order_lines[i].id == result[j].id){
                                order_lines[i].set_point(-result[j].point * 1000)
                            }
                        }
                    }
                }else{
                    for(let i = 0; i< result.length; i++){
                        order_lines[i].set_point(- result[i].point * 1000)
                    }
                };
                var total_point_used = 0;
                order_lines.forEach(function(item){
                    if(!item.point){
                        item.point = 0;
                    }
                    let point = -item.point
                    total_point_used += point
                })
                this.env.pos.selectedOrder.total_order_line_point_used = total_point_used/1000;
                this.env.pos.selectedOrder.total_order_line_redisual = points_of_customer - this.env.pos.selectedOrder.total_order_line_point_used
            }
        }

    }

    PointsConsumptionButton.template = 'PointsConsumptionButton';

    ProductScreen.addControlButton({
        component: PointsConsumptionButton,
        condition: function () {
            return this.env.pos;
        },
    })

    Registries.Component.add(PointsConsumptionButton);

    return PointsConsumptionButton;
})