console.log('initializing');
var conditional_fields = document.getElementById('id_contact_days');
conditional_fields.hide();

$("#id_resorts").change(function() {
    console.log('running change function');
    if ($(this).prop('checked') === 'checked') {
        conditional_fields.show();
    } else {
        conditional_fields.hide();
    }
});