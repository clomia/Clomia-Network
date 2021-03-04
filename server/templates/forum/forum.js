const inputOpenBtn = document.querySelector('.input-open-btn');
const textInput = document.querySelector('.text-input');
const delBtn = document.querySelectorAll('.del-btn')[0];
const delForm = document.querySelector('.del-form');
let isClicked_inputOpen = false;
function inputOpen(event) {
    if (isClicked_inputOpen === false) {
        textInput.classList.replace('display-none', 'display-inherit');
        isClicked_inputOpen = true;
    } else {
        textInput.classList.replace('display-inherit', 'display-none');
        isClicked_inputOpen = false;
    }
}
let isClicked_delBtn = false;
function inspectOpen(event) {
    if (isClicked_delBtn === false) {
        delForm.classList.replace('display-none', 'display-inherit');
        isClicked_delBtn = true;
    } else {
        delForm.classList.replace('display-inherit', 'display-none');
        isClicked_delBtn = false;
    }
}

function init() {
    inputOpenBtn.addEventListener('click', inputOpen);
    delBtn.addEventListener('click', inspectOpen);
}
init();