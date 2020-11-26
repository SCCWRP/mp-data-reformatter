/* Javascript code for the receipt tool */


/*  Literally no reason to wrap the entire JS part of the app inside of an IIFE 
other than to not have the variables in the environment */ 
(function(){
    
    /*  
    From StackOverflow
    https://stackoverflow.com/questions/8006715/drag-drop-files-into-standard-html-file-input */
    document.ondragover = document.ondragenter = function(evt) {
        evt.preventDefault();
    };
    document.ondrop = function(evt) {
        // pretty simple -- but not for IE :(
        document.getElementById("files").files = evt.dataTransfer.files;
        evt.preventDefault();
    };
    /* End code from StackOverflow */

    const submissionForm = document.getElementById("upload");
    submissionForm.addEventListener("submit", async function(event) {
        event.stopPropagation();
        event.preventDefault();
        document.querySelector(".loading-image-container").classList.remove("hidden");
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
            document.querySelector(".loading-image-container").classList.add("hidden");
            console.log(data);
            if (data.error) {
                alert(data.message)
            } else if (data.photo_error) {
                document.querySelector(".unaccounted-photo-container").classList.remove("hidden");
                data.unaccounted_photos.map(p => {
                    document.querySelector(".unaccounted-photo-list")
                    .innerHTML += `<li>${p}</li>`
                })
            } else {
                document.querySelector(".reformat-download").classList.remove("hidden");
            }
    })

})()
