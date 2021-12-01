function copy() {
    var copyText = document.querySelector("#copy-text");
    copyText.select();
    document.execCommand("copy");
}

document.querySelector("#copy-button").addEventListener("click", copy);
document.querySelector("#copy-text").addEventListener("focus", copy);
