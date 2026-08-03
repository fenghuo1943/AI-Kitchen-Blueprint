function showModal(title, html,showCloseBtn=true) {
    document.getElementById("selectTitle").textContent = title;
    document.getElementById("selectContent").innerHTML = html;
    if(showCloseBtn){
        document.getElementById("selectCloseBtn").style.display = "block";
    }else{
        document.getElementById("selectCloseBtn").style.display = "none";
    }
    document.getElementById("selectModal").style.display = "flex";
}

function closeModal() {
    document.getElementById("selectModal").style.display = "none";
}
function overlayClick(e) {
    // 只有点击背景（overlay本身）才关闭
    if (e.target.id === 'selectModal') {
        closeModal();
    }
}