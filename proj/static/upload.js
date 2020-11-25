/* Javascript code for the receipt tool */


/*  Literally no reason to wrap the entire JS part of the app inside of an IIFE 
other than to not have the variables in the environment */ 
(function(){
    const submissionForm = document.querySelector("");
    submissionForm.addEventListener("submit", async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        formData.append('limit',10);
        const response = await fetch("/reformat/upload", {
            method: 'post',
            body: formData
        });
        console.log(response);
        const result = await response.json();
        console.log(result);
    })

})()
