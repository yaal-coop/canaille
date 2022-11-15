$('.confirm').click(function(e){
    e.preventDefault();
    $('#modal-' + e.target.id + '.ui.modal')
        .modal({
            onApprove : function() {
                $('.confirm').unbind('click').click();
            },
        })
        .modal('show');
});
