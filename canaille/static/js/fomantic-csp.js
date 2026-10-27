// Patch to make fomantic-ui/jquery compatible with a strict content security policy
// This must be loaded BEFORE semantic.min.js
// https://github.com/fomantic/Fomantic-UI/issues/214#issuecomment-1002927066

var setAttribute_ = Element.prototype.setAttribute;

// The style attribute is blocked by the policy, so its declarations are set
// through the CSSOM. setProperty keeps the !important priority, that Fomantic
// uses for instance to display the elements during their transitions.
Element.prototype.setAttribute = function (attr, val) {
    if (attr.toLowerCase() !== 'style') {
        setAttribute_.apply(this, [attr, val]);
        return;
    }

    for (const declaration of val.split(';')) {
        const index = declaration.indexOf(':');
        if (index === -1) continue;
        const property = declaration.slice(0, index).trim();
        const value = declaration.slice(index + 1).trim();
        const important = /!\s*important$/i.test(value);
        this.style.setProperty(
            property,
            value.replace(/\s*!\s*important$/i, ''),
            important ? 'important' : '',
        );
    }
}
