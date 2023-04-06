/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define('pos_fast_loading.models', function (require) {
    // "use strict";

    var models = require('point_of_sale.models');
    var { Product } = require('point_of_sale.models');
    // var model_list = models.PosModel.prototype.models;

    var product_model = Product;
    // var partner_model = null;
    var pricelist_item_model = require('point_of_sale.ProductItem');
    var ProductItem = require('point_of_sale.ProductItem');
    const ProductScreen = require('point_of_sale.ProductScreen').prototype
    const { onRendered } = owl;
    var { PosGlobalState } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    // ********************Function for getting data from indexedDB***************************************

    function getRecordsIndexedDB(db, store) {
        return new Promise((resolve, reject) => {
            if (db.objectStoreNames.contains(store)) {
                try {
                    var transaction = db.transaction(store, "readwrite");
                    var objectStore = transaction.objectStore(store);
                    var data_request = objectStore.getAll();
                    data_request.onsuccess = function (event) {
                        resolve(event.target.result);
                    }
                    data_request.onerror = function (event) {
                        reject();
                    }
                }
                catch (e) {
                    console.log("No Items found", e)
                }
            }
        });
    }

    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            if (loadedData['mongo.server.config']){
                this._loadMongoConfig(loadedData['mongo.server.config'][0]);
            }
            this._loadProductBackground();
        }

        _loadMongoConfig(config) {
            this.db.mongo_config = config;
        }

        // This is old function, using to load product to pos of base
        _loadProductToPOS(products) {
            const productMap = {};
            const productTemplateMap = {};

            const modelProducts = products.map(product => {
                product.pos = this;
                product.applicablePricelistItems = {};
                productMap[product.id] = product;
                productTemplateMap[product.product_tmpl_id[0]] = (productTemplateMap[product.product_tmpl_id[0]] || []).concat(product);
                return Product.create(product);
            });

            for (let pricelist of this.pricelists) {
                for (const pricelistItem of pricelist.items) {
                    if (pricelistItem.product_id) {
                        let product_id = pricelistItem.product_id[0];
                        let correspondingProduct = productMap[product_id];
                        if (correspondingProduct) {
                            this._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                        }
                    }
                    else if (pricelistItem.product_tmpl_id) {
                        let product_tmpl_id = pricelistItem.product_tmpl_id[0];
                        let correspondingProducts = productTemplateMap[product_tmpl_id];
                        for (let correspondingProduct of (correspondingProducts || [])) {
                            this._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                        }
                    }
                    else {
                        for (const correspondingProduct of products) {
                            this._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                        }
                    }
                }
            }
            this.db.add_products(modelProducts)
            this.db.product_loaded = true;
        }

        _getProductBackground(last_update){
            var self = this;
            var params = {
                model: "product.product",
                context: _.extend({sync_from_mongo: true, is_indexed_updated: last_update}, {}),
                method: 'search_read',
                fields: ['display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                 'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                 'product_tmpl_id','tracking', 'write_date', 'available_in_pos', 'attribute_line_ids', 'active'],
                domain: ['&', '&', ['sale_ok','=',true],['available_in_pos','=',true],'|',['company_id','=',this.config.company_id[0]],['company_id','=',false]]
            };
            this.env.services.rpc(params).then(function (result) {
                self._loadProductProduct(result);
            }, function (err) {
                reject(err);
            });
        }

        async _loadProductBackground(){
            var self = this;
            let request_cacheDate = window.indexedDB.open('cacheDate', 1);
            request_cacheDate.onsuccess = function (event) {
                var db = event.target.result;
                if (db.objectStoreNames.contains('last_update')) {
                    getRecordsIndexedDB(db, 'last_update').then(function (res) {
                        self._getProductBackground(res);
                    });
                }
            }
            request_cacheDate.onupgradeneeded = function (event) {
                var db = event.target.result;
                var itemsStore = db.createObjectStore('last_update', {
                    keyPath: 'id'
                });
            }

        }

        // Override by QTH
        _loadProductProduct(products) {
            let self = this;
            self.db.product_loaded = false;
            if (!('indexedDB' in window)) {
                console.log('This browser doesn\'t support IndexedDB');
            } else {
                if ( products && products.length) {
                    self._loadProductToPOS(products);
                };

                let request_product = window.indexedDB.open('Product', 1);
                request_product.onsuccess = function (event) {
                    let db = event.target.result;
                    if (!(products && products.length)) {
                        getRecordsIndexedDB(db, 'products').then(function (res) {
                            $.blockUI({
                                message: '<h1 style="color:rgb(220, 236, 243);"><i class="fa fa-spin fa-spinner"></i> Product Loading...</h1>'
                            });
                            self._loadProductToPOS(res)
                            console.log("product loaded through indexdb...........");
                            $.unblockUI();
                        });
                    } else {
                        if (db.objectStoreNames.contains('products')) {
                            try {
                                var product_transaction = db.transaction('products', 'readwrite');
                                var productsStore = product_transaction.objectStore('products');
                                /*************************************/
                                products.forEach(function (product) {
                                    var data_store = productsStore.get(product.id);
                                    data_store.onsuccess = function (event) {
                                        var data = event.target.result;
                                        data = product;
                                        // data.active = true;
                                        // data.available_in_pos = true;
                                        delete data['pos']
                                        try {
                                            productsStore.put(data);
                                        }
                                        catch(err) {
                                            console.log(err.message);
                                        }
                                    }
                                });
                            } catch {
                                console.log("----exception---- products")
                            }
                        }
                    }
                };
                request_product.onupgradeneeded = function (event) {
                    var db = event.target.result;
                    var productsStore = db.createObjectStore('products', {
                        keyPath: 'id'
                    });
                };
            }
        }
    }
    Registries.Model.extend(PosGlobalState, PosCustomPosGlobalState);
});



