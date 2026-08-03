//globalModal.js
const modal2 = document.getElementById("globalModal");
const modalBody2 = modal2.querySelector(".modal-body");

function openModal(html){
    modalBody2.innerHTML = html;
    modal2.classList.add("show");
}

function closeModal(){
    modal2.classList.remove("show");
}

modal2.addEventListener("click",function(e){
    if(e.target === modal2){
        closeModal();
    }
});

function openMenu(options){

    let html = "";

    options.forEach(opt=>{
        html += `<button class="modal-btn" onclick="modalSelect('${opt.value}')">${opt.label}</button>`;
    });

    openModal(html);

    window.modalSelect = function(value){
        closeModal();
        if(options.callback){
            options.callback(value);
        }
    };
}