document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.captcha-audio-button').forEach(button => {
        button.addEventListener('click', function() {
            const audioId = this.dataset.audioId;
            const audio = document.getElementById(audioId);
            if (audio) {
                audio.play();
            }
        });
    });
});
