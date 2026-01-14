// Patch to make fomantic-ui/jquery compatible with a strict content security policy
// This must be loaded BEFORE semantic.min.js
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
