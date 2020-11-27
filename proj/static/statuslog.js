/* Javascript code for the reformatter tool */


/*  Literally no reason to wrap the entire JS part of the app inside of an IIFE 
other than to not have the variables in the environment */ 
(function(){
    const getStatus = async function (){
        let result = await fetch(`/reformat/status`);
        let data = await result.json();
        console.log(data.message);
        if (data.message === "nothing") {
            console.log("nothing");
            document.querySelector(".files-received").classList.add("hidden");
            setTimeout(getStatus, 2000);
        } else if (data.message === "files received") {
            document.querySelector(".files-received").classList.remove("hidden");
            setTimeout(getStatus, 1000);
        } else if (data.message = "files processed"){
            document.querySelector(".files-received").classList.add("hidden");
        } else {
            console.log("getStatus received an unexpected response");
        }
    }

    const submissionForm = document.getElementById("upload");
    submissionForm.addEventListener("submit", async function(event) {
        getStatus();
    });
})()