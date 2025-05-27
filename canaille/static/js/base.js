function onDomChanges() {
    $('.ui.dropdown').each(function(){
        $(this).dropdown({"placeholder": $(this).attr("placeholder")});
    });
    $('*[title]').popup();
}

document.addEventListener('DOMContentLoaded', function() {
    $('.autofocus').focus();
    htmx.config.requestClass = "loading"
    htmx.config.includeIndicatorStyles = false
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

// the following code's purpose is to make jquery compatible with a strict content security policy
// https://github.com/fomantic/Fomantic-UI/issues/214#issuecomment-1002927066

var setAttribute_ = Element.prototype.setAttribute;

Element.prototype.setAttribute = function (attr, val) {
    if (attr.toLowerCase() !== 'style') {
        setAttribute_.apply(this, [attr, val]);
    } else {
        var arr = val.split(';').map( (el, index) => el.trim() );
        for (var i=0, tmp; i < arr.length; ++i) {
            if (! /:/.test(arr[i]) ) continue;
            tmp = arr[i].split(':').map( (el, index) => el.trim() );
            this.style[ camelize(tmp[0]) ] = tmp[1];
        }
    }
}

function camelize(str) {
    return str.split('-').map(
        (word, index) => index == 0 ? word : word[0].toUpperCase() + word.slice(1)
    ).join('');
}
