/* Javascript code for the receipt tool */


/*  Literally no reason to wrap the entire JS part of the app inside of an IIFE 
other than to not have the variables in the environment */ 
(function(){

    const submissionForm = document.getElementById("upload");
    submissionForm.addEventListener("submit", async function(event) {
        event.stopPropagation();
        event.preventDefault();
        //document.querySelector(".records-display-inner-container").innerHTML = '<img src="/changerequest/static/loading.gif">';
        //const dropped_files = event.originalEvent.dataTransfer.files;
        const dropped_files = document.querySelector('[type=file]').files;
        const formData = new FormData();
        for(let i = 0; i < dropped_files.length; ++i){
            /* submit as array to as file array - otherwise will fail */
            formData.append('files[]', dropped_files[i]);
        }
        let result = await fetch(
            `/reformat/upload`,
            {
                method: 'post',
                body: formData
            }
        );
        let data = await result.json();
        console.log(data);
        if (data.error === "true") {
            alert(data.message)
        } else {
            document.querySelector(".reformat-download").classList.remove("hidden");
        }
    })

})()
