let canvas = document.getElementById("wheelCanvas");
let ctx = canvas.getContext("2d");

let img1 = new Image();
let img2 = new Image();
let img3 = new Image();

img1.src = "/static/11.svg";
img2.src = "/static/22.svg";
img3.src = "/static/33.svg";

let loaded = 0;
[img1, img2, img3].forEach(img => img.onload = () => { loaded++; if (loaded === 3) draw(); });

let s1 = document.getElementById("slider1");   // A (keys wheel)
let s2 = document.getElementById("slider2");   // B (modes wheel)
let link = document.getElementById("linkBox");
let saveBtn = document.getElementById("saveBtn");

let offset = 0;    // identical to PySide logic
let scaleUI = 0.90;

let currentTonality = "";   // updated every draw, sent to backend

// ----------------- Tonality logic (same as PySide) -----------------
function getMode(angle) {
    angle = ((angle % 360) + 360) % 360;
    const index = Math.floor(angle / 30) % 12;
    const modes = [
        "Major", "Mixolydian", "Dorian", "Minor", "Phrygian",
        "Locrian", "", "", "", "", "", "Lydian"
    ];
    return modes[index];
}

function rotateArray(arr, n) {
    const len = arr.length;
    if (len === 0) return arr.slice();
    n = ((n % len) + len) % len;
    return arr.slice(n).concat(arr.slice(0, n));
}

function getTonality(slider1, slider2) {
    slider1 = ((slider1 % 360) + 360) % 360;
    const index = Math.floor(slider1 / 30) % 12;

    let tonalities = [
        "G", "D", "A", "E", "B",
        "F#", "C#", "Ab", "Eb", "Bb", "F", "C"
    ].reverse();

    const mode = getMode(slider2);

    const shifts = {
        "Lydian": 1,
        "Mixolydian": -1,
        "Dorian": -2,
        "Minor": -3,
        "Phrygian": -4,
        "Locrian": -5,
        "Major": 0
    };

    if (!(mode in shifts)) return "";

    tonalities = rotateArray(tonalities, shifts[mode]);
    return tonalities[index] + " " + mode;
}

// identical drawing math as PySide
function draw() {
    if (loaded !== 3) return;

    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;

    let cx = canvas.width / 2;
    let cy = canvas.height / 2;
    let size = Math.min(canvas.width, canvas.height) * scaleUI;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    function render(img, angle, k = 1.0) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle * Math.PI / 180);

        // base image size * scale factor
        const w = size * k;
        const h = size * k;

        // draw so that the *scaled* image still remains centered
        ctx.drawImage(img, -w / 2, -h / 2, w, h);

        ctx.restore();
    }

    render(img1, +s1.value);
    render(img2, +s2.value, 1.016);
    render(img3, 0);

    // ----------------- Tonality label in canvas -----------------
    const tonality = getTonality(+s1.value, +s2.value);
    currentTonality = tonality;

    if (tonality) {
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "alphabetic";

        const longWord = /Mixolydian|Phrygian|Locrian/.test(tonality);
        const factor = longWord ? 0.045 : 0.055;   // same idea as PySide/Qt
        const fontSize = size * factor;

        ctx.font = `${fontSize}px sans-serif`;
        ctx.fillStyle = "#701e22";

        const y = cy + fontSize * 0.35;  // visually similar to PySide export

        ctx.fillText(tonality, cx, y);
        ctx.restore();
    }
}

// ------------------------------------------
// PERFECT 1:1 Linked slider behaviour
// ------------------------------------------
function apply_link() {
    if (link.checked) {
        offset = (+s2.value) - (+s1.value);

        s1.min = -180; s1.max = 180;
        s2.min = -180; s2.max = 180;

        s1.oninput = () => followA();
        s2.oninput = () => followB();

    } else {
        // restore original ranges
        s1.min = -180; s1.max = 180;
        s2.min = -30; s2.max = 150;

        s1.oninput = draw;
        s2.oninput = draw;
    }
    draw();
}

function followA() {
    let master = +s1.value;
    let target = master + offset;

    // wrap B (slave) only
    target = wrap(target, +s2.min, +s2.max);

    s2.value = target;
    draw();
}

function followB() {
    let master = +s2.value;
    let target = master - offset;

    // wrap A (slave) only
    target = wrap(target, +s1.min, +s1.max);

    s1.value = target;
    draw();
}

// cyclic wrap identical to original python
function wrap(v, min, max) {
    let span = max - min;
    while (v < min) v += span;
    while (v > max) v -= span;
    return Math.round(v / 30) * 30;   // snap to step 30°
}

link.onchange = apply_link;
s1.oninput = draw;
s2.oninput = draw;
draw();


//---------------------------------------------------------
// SAVE BUTTON DROPDOWN
//---------------------------------------------------------
let menu = document.getElementById("saveMenu");

// Toggle dropdown
saveBtn.onclick = (e) => {
    e.stopPropagation(); // prevent immediate close
    menu.classList.toggle("hidden");
};

// Hide dropdown on outside click
document.addEventListener("click", (e) => {
    if (!menu.contains(e.target) && e.target !== saveBtn) {
        menu.classList.add("hidden");
    }
});

// Menu click → call backend
menu.onclick = async (e) => {
    const type = e.target.dataset.type;
    if (!type) return;

    menu.classList.add("hidden");

    const form = new FormData();
    form.append("svg1", await fetchSvg("/static/11.svg"));
    form.append("svg2", await fetchSvg("/static/22.svg"));
    form.append("svg3", await fetchSvg("/static/33.svg"));
    form.append("angles", `${s1.value},${s2.value}`);
    form.append("format", type);
    form.append("tonality", currentTonality || "");

    try {
        const res = await fetch("/export", {
            method: "POST",
            body: form
        });

        if (!res.ok) {
            console.error("Export failed, status:", res.status);
            return;
        }

        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);

        let base = currentTonality || "circle";
        base = base.replace(/\s+/g, "_");

        a.download = base + (type === "png" ? ".png" : ".pdf");
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (err) {
        console.error("Export error:", err);
    }
};

async function fetchSvg(url) {
    const res = await fetch(url);
    return await res.text();
}
