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
    // var pricelist_item_model = null;
    const ProductScreen = require('point_of_sale.ProductScreen').prototype


    // models.load_models({
    //     model: 'mongo.server.config',
    //     fields: ['cache_last_update_time', 'pos_live_sync', 'active_record'],
    //     loaded: function (self, mongo) {
    //         self.db.mongo_config = {};
    //         if (mongo && mongo.filter(a=> a.active_record)) {
    //             self.db.mongo_config = mongo.filter(a=> a.active_record);
    //         }
    //     }
    // }, {
    //     'before': 'res.partner'
    // });

    var { PosGlobalState } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            if (loadedData['mongo.server.config']){
                this.db.mongo_config = loadedData['mongo.server.config'][0];
            }
            
        }
    }
    Registries.Model.extend(PosGlobalState, PosCustomPosGlobalState);



    // for (var i = 0, len = model_list.length; i < len; i++) {
    //     if (model_list[i].model == "product.product") {
    //         product_model = model_list[i];

    //     } else if (model_list[i].model == "res.partner") {
    //         partner_model = model_list[i]

    //     } else if (model_list[i].model == "product.pricelist.item") {
    //         pricelist_item_model = model_list[i]
    //     }
    // }

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


    // ********************Updating Products Context***************************************



    var super_product_context = product_model.context;
    if (super_product_context && typeof (super_product_context) == 'function') {
        try {
            var request = window.indexedDB.open('cacheDate', 1);
            request.onsuccess = function (event) {
                var db = event.target.result;
                if (db.objectStoreNames.contains('last_update')) {
                    getRecordsIndexedDB(db, 'last_update').then(function (res) {
                        product_model.context = function (self) {
                            var data = super_product_context();
                            if (typeof (data) == 'object') {
                                data['sync_from_mongo'] = true;
                                data['is_indexed_updated'] = res;
                            }
                            return data
                        }
                    });
                }
            }
            request.onupgradeneeded = function (event) {
                var db = event.target.result;
                var itemsStore = db.createObjectStore('last_update', {
                    keyPath: 'id'
                });
            }
            product_model.context = function (self) {
                var data = super_product_context();
                if (typeof (data) == 'object') {
                    data['sync_from_mongo'] = true;
                }
                return data
            }

        } catch (err) {
            product_model.context = function (self) {
                var data = super_product_context();
                if (typeof (data) == 'object') {
                    data['sync_from_mongo'] = true;
                }
                return data
            }
            console.log("***************Error*************", err);
        }

    } else if (super_product_context && typeof (super_product_context) == 'object') {
        try {
            var request = window.indexedDB.open('cacheDate', 1);
            request.onsuccess = function (event) {
                var db = event.target.result;
                if (db.objectStoreNames.contains('last_update')) {
                    getRecordsIndexedDB(db, 'last_update').then(function (res) {
                        product_model.context['sync_from_mongo'] = true;
                        product_model.context['is_indexed_updated'] = res;
                    })
                }
            }
            request.onupgradeneeded = function (event) {
                var db = event.target.result;
                var itemsStore = db.createObjectStore('last_update', {
                    keyPath: 'id'
                });
            }
            product_model.context['sync_from_mongo'] = true;
        } catch (err) {
            product_model.context['sync_from_mongo'] = true;
            console.log("***************Error*************", err);
        }
    } else {
        try {
            var request = window.indexedDB.open('cacheDate', 1);
            request.onsuccess = function (event) {
                var db = event.target.result;
                if (db.objectStoreNames.contains('last_update')) {
                    getRecordsIndexedDB(db, 'last_update').then(function (res) {
                        product_model.context = {
                            'sync_from_mongo': true,
                            'is_indexed_updated': res
                        };
                        return;
                    })
                }
            }
            request.onupgradeneeded = function (event) {
                var db = event.target.result;
                var itemsStore = db.createObjectStore('last_update', {
                    keyPath: 'id'
                });
            }
            product_model.context = {
                'sync_from_mongo': true
            };

        } catch (err) {
            product_model.context = {
                'sync_from_mongo': true
            };
            console.log("***************Error*************", err);
        }
    }




    // // ********************Updating Partner Context***************************************


    // var super_partner_context = partner_model.context;
    // if (super_partner_context && typeof (super_partner_context) == 'function') {
    //     try {
    //         var request = window.indexedDB.open('cacheDate', 1);
    //         request.onsuccess = function (event) {
    //             var db = event.target.result;
    //             if (db.objectStoreNames.contains('last_update')) {
    //                 getRecordsIndexedDB(db, 'last_update').then(function (res) {
    //                     partner_model.context = function (self) {
    //                         var data = super_partner_context();
    //                         if (typeof (data) == 'object') {
    //                             data['sync_from_mongo'] = true;
    //                             data['is_indexed_updated'] = res;
    //                         }
    //                         return data
    //                     }
    //                 });
    //             }
    //         }
    //         request.onupgradeneeded = function (event) {
    //             var db = event.target.result;
    //             var itemsStore = db.createObjectStore('last_update', {
    //                 keyPath: 'id'
    //             });

    //         }
    //         partner_model.context = function (self) {
    //             var data = super_partner_context();
    //             if (typeof (data) == 'object') {
    //                 data['sync_from_mongo'] = true;
    //             }
    //             return data
    //         }
    //     } catch (err) {
    //         partner_model.context = function (self) {
    //             var data = super_partner_context();
    //             if (typeof (data) == 'object') {
    //                 data['sync_from_mongo'] = true;
    //             }
    //             return data
    //         }
    //         console.log("***************Error*************", err);
    //     }
    // } else if (super_partner_context && typeof (super_partner_context) == 'object') {
    //     try {
    //         var request = window.indexedDB.open('cacheDate', 1);
    //         request.onsuccess = function (event) {
    //             var db = event.target.result;
    //             if (db.objectStoreNames.contains('last_update')) {
    //                 getRecordsIndexedDB(db, 'last_update').then(function (res) {
    //                     partner_model.context['sync_from_mongo'] = true;
    //                     partner_model.context['is_indexed_updated'] = res;
    //                 })
    //             }

    //         }
    //         request.onupgradeneeded = function (event) {
    //             var db = event.target.result;
    //             var itemsStore = db.createObjectStore('last_update', {
    //                 keyPath: 'id'
    //             });
    //         }
    //         partner_model.context['sync_from_mongo'] = true;

    //     } catch (err) {
    //         partner_model.context['sync_from_mongo'] = true;
    //         console.log("***************Error*************", err);
    //     }
    // } else {
    //     try {
    //         var request = window.indexedDB.open('cacheDate', 1);
    //         request.onsuccess = function (event) {
    //             var db = event.target.result;
    //             if (db.objectStoreNames.contains('last_update')) {
    //                 getRecordsIndexedDB(db, 'last_update').then(function (res) {
    //                     partner_model.context = {
    //                         'sync_from_mongo': true,
    //                         'is_indexed_updated': res
    //                     };
    //                     return;
    //                 })
    //             }
    //         }
    //         request.onupgradeneeded = function (event) {
    //             var db = event.target.result;
    //             var itemsStore = db.createObjectStore('last_update', {
    //                 keyPath: 'id'
    //             });
    //         }
    //         partner_model.context = {
    //             'sync_from_mongo': true
    //         };

    //     } catch (err) {
    //         partner_model.context = {
    //             'sync_from_mongo': true
    //         };
    //         console.log("***************Error*************", err);
    //     }
    // }


    // // ********************Updating PriceList Items Context***************************************

    // var super_price_item_context = pricelist_item_model.context;
    // if (super_price_item_context && typeof (super_price_item_context) == 'function') {
    //     try {
    //         var request = window.indexedDB.open('cacheDate', 1);
    //         request.onsuccess = function (event) {
    //             var db = event.target.result;
    //             if (db.objectStoreNames.contains('last_update')) {
    //                 getRecordsIndexedDB(db, 'last_update').then(function (res) {
    //                     pricelist_item_model.context = function (self) {
    //                         var data = super_price_item_context();
    //                         if (typeof (data) == 'object') {
    //                             data['sync_from_mongo'] = true;
    //                             data['is_indexed_updated'] = res;
    //                         }
    //                         return data
    //                     }
    //                 });
    //             }
    //         }
    //         request.onupgradeneeded = function (event) {
    //             var db = event.target.result;
    //             var itemsStore = db.createObjectStore('last_update', {
    //                 keyPath: 'id'
    //             });
    //         }
    //         pricelist_item_model.context = function (self) {
    //             var data = super_price_item_context();
    //             if (typeof (data) == 'object') {
    //                 data['sync_from_mongo'] = true;
    //             }
    //             return data
    //         }
    //     } catch (err) {
    //         pricelist_item_model.context = function (self) {
    //             var data = super_price_item_context();
    //             if (typeof (data) == 'object') {
    //                 data['sync_from_mongo'] = true;
    //             }
    //             return data
    //         }
    //         console.log("***************Error*************", err);
    //     }
    // } else if (super_price_item_context && typeof (super_price_item_context) == 'object') {
    //     try {
    //         var request = window.indexedDB.open('cacheDate', 1);
    //         request.onsuccess = function (event) {
    //             var db = event.target.result;
    //             if (db.objectStoreNames.contains('last_update')) {
    //                 getRecordsIndexedDB(db, 'last_update').then(function (res) {
    //                     pricelist_item_model.context['sync_from_mongo'] = true;
    //                     pricelist_item_model.context['is_indexed_updated'] = res;
    //                 })
    //             }

    //         }
    //         request.onupgradeneeded = function (event) {
    //             var db = event.target.result;
    //             var itemsStore = db.createObjectStore('last_update', {
    //                 keyPath: 'id'
    //             });
    //         }
    //         pricelist_item_model.context['sync_from_mongo'] = true;

    //     } catch (err) {
    //         pricelist_item_model.context['sync_from_mongo'] = true;
    //         console.log("***************Error*************", err)
    //     }
    // } else {
    //     try {
    //         var request = window.indexedDB.open('cacheDate', 1);
    //         request.onsuccess = function (event) {
    //             var db = event.target.result;
    //             if (db.objectStoreNames.contains('last_update')) {
    //                 getRecordsIndexedDB(db, 'last_update').then(function (res) {
    //                     pricelist_item_model.context = {
    //                         'sync_from_mongo': true,
    //                         'is_indexed_updated': res
    //                     };
    //                     return;
    //                 })
    //             }
    //         }
    //         request.onupgradeneeded = function (event) {
    //             var db = event.target.result;
    //             var itemsStore = db.createObjectStore('last_update', {
    //                 keyPath: 'id'
    //             });
    //         }
    //         pricelist_item_model.context = {
    //             'sync_from_mongo': true
    //         };

    //     } catch (err) {
    //         pricelist_item_model.context = {
    //             'sync_from_mongo': true
    //         };
    //         console.log("***************Error*************", err)
    //     }
    // }




    // // ********************Updating PricelistItems Loaded***************************************


    // var super_price_item_loaded = pricelist_item_model.loaded;
    // if (super_price_item_loaded) {
    //     // ******************Stroring code to indexedDB***********
    //     if (!('indexedDB' in window)) {
    //         console.log('This browser doesn\'t support IndexedDB');
    //     } else {
    //         pricelist_item_model.loaded = function (self, pricelist_items) {
    //             if (pricelist_items.length)
    //                 super_price_item_loaded.call(this, self, pricelist_items);
    //             var request = window.indexedDB.open('Items', 1);
    //             request.onsuccess = function (event) {
    //                 var db = event.target.result;
    //                 if (!(pricelist_items.length) && pricelist_item_model.context.is_indexed_updated && pricelist_item_model.context.is_indexed_updated.length) {
    //                     getRecordsIndexedDB(db, 'items').then(function (res) {
    //                         super_price_item_loaded.call(this, self, res);
    //                     });
    //                 } else {
    //                     if (db.objectStoreNames.contains('items')) {
    //                         try {
    //                             var transaction = db.transaction('items', 'readwrite');
    //                             var itemsStore = transaction.objectStore('items');
    //                             pricelist_items.forEach(function (item) {
    //                                 var data_store = itemsStore.get(item.id);
    //                                 data_store.onsuccess = function (event) {
    //                                     var data = event.target.result;
    //                                     data = item;
    //                                     var requestUpdate = itemsStore.put(data);
    //                                 }
    //                             });
    //                         } catch {
    //                             console.log("-----exception --- items")
    //                         }
    //                     }
    //                 };
    //             }
    //             request.onupgradeneeded = function (event) {
    //                 var db = event.target.result;
    //                 var itemsStore = db.createObjectStore('items', {
    //                     keyPath: 'id'
    //                 });
    //             };
    //         }
    //     }

    // }

    // ********************Updating Products Loaded***************************************


    var product_loaded = product_model.loaded;
    if (!('indexedDB' in window)) {
        console.log('This browser doesn\'t support IndexedDB');
    } else {
        product_model.loaded = function (self, products) {
            self.db.product_loaded = false;
            if (products.length) {
                _.each(products, function (obj) {
                    obj.pos = self;
                    // obj.active = true;
                    // obj.available_in_pos = true;
                })
                product_loaded.call(this, self, products);
                console.log("product loaded through default...........");
            }

            var request = window.indexedDB.open('Product', 1);
            request.onsuccess = function (event) {
                var db = event.target.result;
                if (!(products.length)) {
                    getRecordsIndexedDB(db, 'products').then(function (res) {
                        $.blockUI({
                            message: '<h1 style="color:rgb(220, 236, 243);"><i class="fa fa-spin fa-spinner"></i> Product Loading...</h1>'
                        });
                        _.each(res, function (obj) {
                            obj.pos = self;
                            // obj.active = true;
                            // obj.available_in_pos = true;
                        })
                        product_loaded.call(this, self, res);
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
                                    productsStore.put(data);
                                }
                            });
                        } catch {
                            console.log("----exception---- products")
                        }
                    }
                }
            }
            request.onupgradeneeded = function (event) {
                var db = event.target.result;
                var productsStore = db.createObjectStore('products', {
                    keyPath: 'id'
                });
            };

        }


        // ********************Updating Partner Loaded***************************************

        // var partner_loaded = partner_model.loaded;
        // if (!('indexedDB' in window)) {
        //     console.log('This browser doesn\'t support IndexedDB');
        // } else {
        //     partner_model.loaded = function (self, partners) {
        //         if (partners.length)
        //             partner_loaded.call(this, self, partners);
        //         var request = window.indexedDB.open('Partners', 1);
        //         request.onsuccess = function (event) {
        //             var db = event.target.result;
        //             if (!(partners.length)) {
        //                 getRecordsIndexedDB(db, 'partners').then(function (res) {
        //                     partner_loaded.call(this, self, res);
        //                 });
        //             }
        //             else {
        //                 if (db.objectStoreNames.contains('partners')) {
        //                     try {
        //                         var transaction = db.transaction('partners', 'readwrite');
        //                         var partnersStore = transaction.objectStore('partners');
        //                         /*************************************/
        //                         partners.forEach(function (partner) {
        //                             var data_store = partnersStore.get(partner.id);
        //                             data_store.onsuccess = function (event) {
        //                                 var data = event.target.result;
        //                                 data = partner;
        //                                 var requestUpdate = partnersStore.put(data);
        //                             }
        //                         });
        //                     } catch {
        //                         console.log("--- exception --- partners")
        //                     }
        //                 }
        //             };
        //         }
        //         request.onupgradeneeded = function (event) {
        //             var db = event.target.result;
        //             var partnersStore = db.createObjectStore('partners', {
        //                 keyPath: 'id'
        //             });
        //         };

        //         // **********date*******
        //         var date_request = window.indexedDB.open('cacheDate', 1);
        //         date_request.onupgradeneeded = function (event) {
        //             var db = event.target.result;
        //             var lastUpdateTimeStore = db.createObjectStore('last_update', {
        //                 keyPath: 'id'
        //             });
        //         };
        //         date_request.onsuccess = function (event) {
        //             var date_db = event.target.result;
        //             try {
        //                 var time_transaction = date_db.transaction('last_update', 'readwrite');
        //                 var lastTimeStore = time_transaction.objectStore('last_update');
        //                 var last_date_store = lastTimeStore.get('time');
        //                 last_date_store.onsuccess = function (event) {
        //                     var data = event.target.result;
        //                     data = {
        //                         'id': 'time',
        //                         'time': self.db.mongo_config.cache_last_update_time
        //                     };
        //                     var last_updated_time = lastTimeStore.put(data);
        //                 }
        //             } catch {
        //                 console.log("-----exception---- last update");
        //             }
        //         };
        //     }
        // }
    }
});



