function onDomChanges() {
    $('.ui.dropdown').each(function(){
        $(this).dropdown({"placeholder": $(this).attr("placeholder")});
    });
    $('*[title]').popup();
}

document.addEventListener('DOMContentLoaded', function() {
    $('.autofocus').focus();
    onDomChanges();
});


document.addEventListener('htmx:load', onDomChanges);

document.body.addEventListener('htmx:beforeOnLoad', function (evt) {
    if (evt.detail.xhr.status >= 400) {
        evt.detail.shouldSwap = true;
        evt.detail.isError = false;
    }
});
