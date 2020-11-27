/* Javascript code for the reformatting tool */


/*  Literally no reason to wrap the entire JS part of the app inside of an IIFE 
other than to not have the variables in the environment */ 
(function(){
    let photoLists = [".unaccounted-photo-list",".misnamed-photoid-list",".missing-photo-list"];
    let hiddenItems = [
        ".after-upload",".files-received",".reformat-download",
        ".unaccounted-photo-container",".misnamed-photoid-container",
        ".missing-photo-container"
    ];

    const submissionForm = document.getElementById("upload");
    submissionForm.addEventListener("submit", async function(event) {
        event.stopPropagation();
        event.preventDefault();
        photoLists.map(s => {document.querySelector(s).innerHTML = ""});
        hiddenItems.map(s => {document.querySelector(s).classList.add("hidden")});
        document.querySelector(".loading-image-container").classList.remove("hidden");

        fetch(`/reformat/clear`)
            .then(response => response.json())
            .then(data => console.log(data.message))
            .catch((error) => {
                console.error('Error:', error);
              });

        const dropped_files = document.querySelector('[type=file]').files;
        const formData = new FormData();
        for(let i = 0; i < dropped_files.length; ++i){
            /* submit as array to as file array - otherwise will fail */
            formData.append('files[]', dropped_files[i]);
        }
        formData.append("email",document.querySelector("#email").value);
        let result = await fetch(
            `/reformat/upload`,
            {
                method: 'post',
                body: formData
            }
            );
            let data = await result.json();
            document.querySelector(".loading-image-container").classList.add("hidden");
            document.querySelector(".files-received").classList.add("hidden");
            document.querySelector(".after-upload").classList.remove("hidden");
            console.log(data);
            if (data.error) {
                console.log(data.message);
                alert(data.message);
                /*  Implement notification when the app crashes
                    Let user know that we were notified */
            } else {

                /* Let them download their data regardless */
                document.querySelector(".reformat-download").classList.remove("hidden");
                
                /* Warn the user of photos uploaded but have no correspondiong records */
                if (data.unaccounted_photos.length > 0) {
                    document.querySelector(".unaccounted-photo-container").classList.remove("hidden");
                    data.unaccounted_photos.map(p => {
                        document.querySelector(".unaccounted-photo-list")
                        .innerHTML += `<li>${p}</li>`
                    })
                    if (data.missing_photos.length > 0) {
                        /* Warn user of photos that are missing
                        SCCWRP also needs to be made aware of this */

                        document.querySelector(".misnamed-photoid-container").classList.remove("hidden");
                        data.missing_photos.map(p => {
                            document.querySelector(".misnamed-photoid-list")
                            .innerHTML += `<li>${p}</li>`
                        })
                    }
                } else if (data.missing_photos.length > 0) {
                    /* Warn user of photos that are missing
                    SCCWRP also needs to be made aware of this */

                    document.querySelector(".missing-photo-container").classList.remove("hidden");
                    data.missing_photos.map(p => {
                        document.querySelector(".missing-photo-list")
                        .innerHTML += `<li>${p}</li>`
                    })
                } else {
                    console.log("Nothing missing")
                }

            } 
    })

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


})()
