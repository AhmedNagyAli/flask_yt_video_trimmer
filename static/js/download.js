    function formatTime(seconds) {
        const hrs = String(Math.floor(seconds / 3600)).padStart(2, '0');
        const mins = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
        const secs = String(seconds % 60).padStart(2, '0');
        return `${hrs}:${mins}:${secs}`;
    }

    const startSlider = document.getElementById('start_time');
    const endSlider = document.getElementById('end_time');
    const startLabel = document.getElementById('startTimeLabel');
    const endLabel = document.getElementById('endTimeLabel');

    function updateLabels() {
        let start = parseInt(startSlider.value);
        let end = parseInt(endSlider.value);

        if (start >= end) {
            start = end - 1;
            startSlider.value = start;
        }

        startLabel.textContent = formatTime(start);
        endLabel.textContent = formatTime(end);
    }

    startSlider.addEventListener('input', updateLabels);
    endSlider.addEventListener('input', updateLabels);
    updateLabels();

    // Modal Typewriter Logic
    const form = document.getElementById('downloadForm');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btnText');
    const modal = document.getElementById('loadingModal');
    const typewriter = document.getElementById('typewriterText');
    const message = "Trimming your video, please wait...";
    let index = 0;
    let isDeleting = false;

    function loopTypewriter() {
        if (!isDeleting) {
            typewriter.textContent = message.substring(0, index + 1);
            index++;
            if (index === message.length) {
                isDeleting = true;
                setTimeout(loopTypewriter, 1000);
                return;
            }
        } else {
            typewriter.textContent = message.substring(0, index - 1);
            index--;
            if (index === 0) {
                isDeleting = false;
            }
        }
        setTimeout(loopTypewriter, 60);
    }

    form.addEventListener('submit', () => {
        spinner.classList.remove('hidden');
        btnText.textContent = "Processing...";
        submitBtn.disabled = true;
        modal.classList.remove('hidden');
        loopTypewriter();
    });