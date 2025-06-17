frm.add_custom_button(__('Calculate Order Quantities'), function() {
    console.log('Calculate Order Quantities button clicked');
    calculate_order_quantities(frm);
}).addClass('btn-info'); 