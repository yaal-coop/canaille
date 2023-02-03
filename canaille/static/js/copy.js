function copy(event) {
    var copyInputId = event.target.dataset.copy;
    var copyText = document.getElementById(copyInputId);
    copyText.select();
    document.execCommand("copy");
}

Object.values(document.getElementsByClassName("copy-button")).forEach(elt => elt.addEventListener("click", copy));
Object.values(document.getElementsByClassName("copy-text")).forEach(elt => elt.addEventListener("focus", copy));
