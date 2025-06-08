button = document.getElementById("resend-button");
icon = document.getElementById("resend-icon");
delay = button.dataset.delay * 1000;

if (delay) {
    setTimeout(() => {
        button.classList.remove("disabled")
        icon.classList.remove("hourglass")
        icon.classList.remove("half")
        icon.classList.add("send")
    }, delay);
}
