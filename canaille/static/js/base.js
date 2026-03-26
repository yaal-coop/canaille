function onDomChanges() {
    $('.ui.dropdown').each(function(){
        $(this).dropdown({"placeholder": $(this).attr("placeholder")});
    });
    $('*[title]').popup({exclusive: true});

    $('.toggle-password-visibility').off('click').on('click', function() {
        togglePasswordVisibility(this);
    }).off('keypress').on('keypress', function(e) {
        if (e.which === 13 || e.which === 32) { // Enter or Space
            e.preventDefault();
            togglePasswordVisibility(this);
        }
    });
}

function togglePasswordVisibility(icon) {
    const input = $(icon).siblings('input[type="password"], input[type="text"]');
    const isPassword = input.attr('type') === 'password';

    input.attr('type', isPassword ? 'text' : 'password');

    if (isPassword) {
        $(icon).removeClass('eye').addClass('eye slash');
    } else {
        $(icon).removeClass('eye slash').addClass('eye');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (typeof htmx !== 'undefined') {
        htmx.config.requestClass = "loading"
        htmx.config.includeIndicatorStyles = false
        htmx.config.defaultSwapStyle = "morph"
        Idiomorph.defaults.ignoreActiveValue = true
    }
    onDomChanges();
});


document.addEventListener('htmx:load', onDomChanges);

/* Display a header message when the Canaille application server
 * is unreachable.
 */
document.addEventListener('htmx:sendError', function(x) {
    $('.network-error.nag').nag();
});

document.body.addEventListener('htmx:beforeOnLoad', function (evt) {
    if (evt.detail.xhr.status >= 400) {
        evt.detail.shouldSwap = true;
        evt.detail.isError = false;
    }
});
