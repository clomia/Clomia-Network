const clientDownload = document.querySelector('.bownload__client-download')
const serverDownload = document.querySelector('.bownload__server-download')
const linkForum = document.querySelector('.link__forum')
const linkTech = document.querySelector('.link__tech')

function serverDownload_displayNone(event) {
    serverDownload.classList.add('disappear');
}

function clientDownload_displayNone(event) {
    clientDownload.classList.add('disappear');
}
function serverDownload_displayFlex(event) {
    serverDownload.classList.remove('disappear');
}

function clientDownload_displayFlex(event) {
    clientDownload.classList.remove('disappear');
}
//--------
function linkForum_displayNone(event) {
    linkForum.classList.add('disappear');
}

function linkTech_displayNone(event) {
    linkTech.classList.add('disappear');
}
function linkForum_displayFlex(event) {
    linkForum.classList.remove('disappear');
}

function linkTech_displayFlex(event) {
    linkTech.classList.remove('disappear');
}





function init() {
    clientDownload.addEventListener('mouseover', serverDownload_displayNone);
    clientDownload.addEventListener('mouseout', serverDownload_displayFlex);
    serverDownload.addEventListener('mouseover', clientDownload_displayNone);
    serverDownload.addEventListener('mouseout', clientDownload_displayFlex);
    //------
    linkForum.addEventListener('mouseover', linkTech_displayNone);
    linkForum.addEventListener('mouseout', linkTech_displayFlex);
    linkTech.addEventListener('mouseover', linkForum_displayNone);
    linkTech.addEventListener('mouseout', linkForum_displayFlex);
}

init();