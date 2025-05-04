countDownDuration = 10;
countdown = document.getElementById("countdown");
countdown.innerHTML = countDownDuration;
button = countdown.parentNode;
button.setAttribute("disabled", "");

x = setInterval(() => {
    countDownDuration--;
    if (countDownDuration <= 0) {
        clearInterval(x);
        countdown.innerHTML = "";
        button.removeAttribute("disabled");
    } else {
        countdown.innerHTML = countDownDuration;
    }
}, 1000);
