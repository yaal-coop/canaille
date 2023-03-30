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
