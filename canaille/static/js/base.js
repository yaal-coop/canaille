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

document.body.addEventListener('htmx:beforeOnLoad', function (evt) {
    if (evt.detail.xhr.status >= 400) {
        evt.detail.shouldSwap = true;
        evt.detail.isError = false;
    }
});

// the following code's purpose is to make jquery compatible with a strict content security policy
// https://github.com/fomantic/Fomantic-UI/issues/214#issuecomment-1002927066

var setAttribute_ = Element.prototype.setAttribute;	// Save source of Elem.setAttribute funct

Element.prototype.setAttribute = function (attr, val) {
  if (attr.toLowerCase() !== 'style') {
    // console.log("set " + attr + "=`" + val + "` natively");
    setAttribute_.apply(this, [attr, val]);		// Call the saved native Elem.setAttribute funct
  } else {
    // 'color:red; background-color:#ddd' -> el.style.color='red'; el.style.backgroundColor='#ddd';
    // console.log("set " + attr + "=`" + val + "` via setAttribute('style') polyfill");
    var arr = val.split(';').map( (el, index) => el.trim() );
    for (var i=0, tmp; i < arr.length; ++i) {
      if (! /:/.test(arr[i]) ) continue;		// Empty or wrong
      tmp = arr[i].split(':').map( (el, index) => el.trim() );
      this.style[ camelize(tmp[0]) ] = tmp[1];
      //console.log(camelize(tmp[0]) + ' = '+ tmp[1]);
    }
  }
}

function camelize(str) {
  return str
  .split('-')	// Parse 'my-long-word' to ['my', 'long', 'word']
  .map(
    // Converts all elements to uppercase except first: ['my', 'long', 'word'] -> ['my', 'Long', 'Word']
    (word, index) => index == 0 ? word : word[0].toUpperCase() + word.slice(1)
  )
  .join(''); // Join ['my', 'Long', 'Word'] в 'myLongWord'
}
