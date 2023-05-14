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
                        if(order_lines[i].product.id == promotion.point_consumption_ids[j].id){
                            product_valid.push(order_lines[i]);
                        }
                    }
            };

            for (let i=0; i< order_lines.length;i++){
                    product_valid_apply_all.push(order_lines[i])
            };
            var old_data_props = []
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
                            if(data[i].id == order_lines[j].id && data[i].point !==0){
                                let line = Orderline.create({}, {pos: this.env.pos, order: this.env.pos.get_order(), product: order_lines[j].product});
                                let line_new = OrderCurrent.createNewLinePoint(line)
                                OrderCurrent.set_orderline_options(order_lines[j], {quantity: order_lines[j].quantity - line_new.quantity})
                                list_order_line_new.push({id: line_new.id, point:data[i].point})
                                this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,line_new.id, true)
                            }
                            if(data[i].id == order_lines[j].id && data[i].point ==0){
                                this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                            }
                        }
                    }
               }else{
                    for(let i =0; i< data.length;i++){
                        for(let j=0; j< order_lines.length;j++){
                            if(order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point !==0){
                                order_lines[j].set_point(-data[i].point*1000)
                                this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, true)
                            }else if(!order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point == 0){
                                this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                            }else if(!order_lines[j].is_new_line_point && data[i].id == order_lines[j].id && data[i].point !== 0){
                                let line = Orderline.create({}, {pos: this.env.pos, order: this.env.pos.get_order(), product: order_lines[j].product});
                                let line_new = OrderCurrent.createNewLinePoint(line)
//                                order_lines[j].quantity = order_lines[j].quantity - line_new.quantity
//                                order_lines[j].quantityStr = (order_lines[j].quantity - line_new.quantity).toString()
                                OrderCurrent.set_orderline_options(order_lines[j], {quantity: order_lines[j].quantity - line_new.quantity})
                                list_order_line_new.push({id: line_new.id, point:data[i].point})
                                this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,line_new.id, true)

                            }else if(order_lines[j].is_new_line_point == true && data[i].id == order_lines[j].id && data[i].point == 0){
                                order_lines[j].set_point(0)
                                this.set_param_old_data(data[i],order_lines[j].product.display_name,order_lines[j].price,i,order_lines[j].id, false)
                            }
                        }
                    }
               }
               for(let i=0; i< order_lines.length; i++){
                    for(let j=0; j< list_order_line_new.length;j++){
                        if(order_lines[i].id === list_order_line_new[j].id){
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

        async _getAddProductOptions(product, base_code) {
            let price_extra = 0.0;
            let draftPackLotLines, weight, description, packLotLinesToEdit;

            if (_.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                  .filter((attr) => attr !== undefined);
                let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
                    product: product,
                    attributes: attributes,
                });

                if (confirmed) {
                    description = payload.selected_attributes.join(', ');
                    price_extra += payload.price_extra;
                } else {
                    return;
                }
            }

            // Gather lot information if required.
            if (['serial', 'lot'].includes(product.tracking) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
                const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                if (isAllowOnlyOneLot) {
                    packLotLinesToEdit = [];
                } else {
                    const orderline = this.currentOrder
                        .get_orderlines()
                        .filter(line => !line.get_discount())
                        .find(line => line.product.id === product.id);
                    if (orderline) {
                        packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                    } else {
                        packLotLinesToEdit = [];
                    }
                }
                const { confirmed, payload } = await this.showPopup('EditListPopup', {
                    title: this.env._t('Lot/Serial Number(s) Required'),
                    isSingleItem: isAllowOnlyOneLot,
                    array: packLotLinesToEdit,
                });
                if (confirmed) {
                    // Segregate the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                    );
                    const newPackLotLines = payload.newArray
                        .filter(item => !item.id)
                        .map(item => ({ lot_name: item.text }));

                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                } else {
                    // We don't proceed on adding product.
                    return;
                }
            }

            // Take the weight if necessary.
            if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                // Show the ScaleScreen to weigh the product.
                if (this.isScaleAvailable) {
                    const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
                        product,
                    });
                    if (confirmed) {
                        weight = payload.weight;
                    } else {
                        // do not add the product;
                        return;
                    }
                } else {
                    await this._onScaleNotAvailable();
                }
            }

            if (base_code && this.env.pos.db.product_packaging_by_barcode[base_code.code]) {
                weight = this.env.pos.db.product_packaging_by_barcode[base_code.code].qty;
            }

            return { draftPackLotLines, quantity: weight, description, price_extra };
       }
//        combinedItems = (order_lines = []) => {
//           const res = order_lines.reduce((acc, obj) => {
//              let found = false;
//              for (let i = 0; i < acc.length; i++) {
//                 if (acc[i].id === obj.id && acc[i].point == obj.point && acc[i].point !=0) {
//                    found = true;
//                    acc[i].total_point=acc[i].total_point+obj.point;
//                    acc[i].count = acc[i].count+obj.count;;
//                 };
//              }
//              if (!found) {
//                 obj.total_point = obj.point;
//                 acc.push(obj);
//              }
//              return acc;
//           }, []);
//           return res;
//        }

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