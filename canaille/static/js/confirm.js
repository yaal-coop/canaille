$('.confirm').click(function(e){
    e.preventDefault();
    $('.ui.modal')
        .modal({
            onApprove : function() {
                $('.confirm').unbind('click').click();
            },
        })
        .modal('show');
});
