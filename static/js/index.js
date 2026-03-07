    // Arabic intro text (above form)
    const introLines = [
        "اداة بسيطة تمكنك من قص اي جزء تريد من اي فديو يوتيوب دون الحاجه لتنزيل المقطع كامل وقصه",
        "فقط يمكنك وضع رابط المقطع وسيتم تحميل الجودات المتاحة لهذا المقطع",
        "قم باختيار الجودة التي تريد وحدد الجزء الذي تريد قصه وسيتم في لحظات تحويلك لصفحة التحميل"
    ];
    const introElem = document.getElementById('introAR');

    async function loopIntroText() {
        let i = 0;
        while (true) {
            await typeWriterLoop(introElem, introLines[i % introLines.length], 50);
            i++;
        }
    }

    // Bilingual text below the form
    const linesEN = [
        "Since it is a free hosting,",
        "it only works on small videos and still has problems,",
        "and may crash many times till you can get your video... ",
        "sorry for that and we hope you wait for the final version."
    ];

    const linesAR = [
        "نظرًا لأنها استضافة مجانية،",
        "فإنه يعمل فقط على مقاطع الفيديو الصغيرة ولا يزال به بعض المشاكل",
        "وقد يتعطل عدة مرات حتى تتمكن من الحصول على الفيديو الخاص بك...",
        "نأسف لذلك ونأمل أن تنتظر الإصدار النهائي."
    ];

    const elemEN = document.getElementById('lineEN');
    const elemAR = document.getElementById('lineAR');

    async function loopBilingualText() {
        let i = 0;
        while (true) {
            await Promise.all([
                typeWriterLoop(elemEN, linesEN[i % linesEN.length]),
                typeWriterLoop(elemAR, linesAR[i % linesAR.length])
            ]);
            i++;
        }
    }

    // Generic typewriter loop function
    function typeWriterLoop(element, text, speed = 60) {
        return new Promise(async(resolve) => {
            for (let i = 0; i <= text.length; i++) {
                element.textContent = text.substring(0, i);
                await new Promise(r => setTimeout(r, speed));
            }
            await new Promise(r => setTimeout(r, 1000));
            for (let i = text.length; i >= 0; i--) {
                element.textContent = text.substring(0, i);
                await new Promise(r => setTimeout(r, speed));
            }
            await new Promise(r => setTimeout(r, 500));
            resolve();
        });
    }

    // Modal typewriter functionality
    const form = document.getElementById('downloadForm');
    const modal = document.getElementById('loadingModal');
    const typewriter = document.getElementById('typewriterText');
    const modalMessage = "Processing the video resolutions...";
    let index = 0;
    let isDeleting = false;

    function loopTypewriterModal() {
        let currentText = typewriter.textContent;

        if (!isDeleting) {
            typewriter.textContent = modalMessage.substring(0, index + 1);
            index++;
            if (index === modalMessage.length) {
                isDeleting = true;
                setTimeout(loopTypewriterModal, 500);
                return;
            }
        } else {
            typewriter.textContent = modalMessage.substring(0, index - 1);
            index--;
            if (index === 0) {
                isDeleting = false;
            }
        }

        setTimeout(loopTypewriterModal, 60);
    }

    // Trigger modal on form submit
    form.addEventListener('submit', function() {
        document.getElementById('submitBtn').disabled = true;
        document.getElementById('buttonText').textContent = 'Processing...';
        document.getElementById('spinner').classList.remove('hidden');
        modal.classList.remove('hidden');
        loopTypewriterModal();
    });

    // Start everything on page load
    window.addEventListener('load', () => {
        loopIntroText();
        loopBilingualText();
    });