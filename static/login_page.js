document.getElementById("login_submit").addEventListener("click", function(){submit_login()})

function submit_login()
{
    u_name = document.getElementById("username").value;
    p_key = document.getElementById("password").value;
    data = JSON.stringify({"username": u_name,"password": p_key});
    post_to_server("130.245.168.249/login", data)
    
}

function post_to_server(path, data)
{
    //console.log("Posting to server:")
    //console.log(data)
    $.post(path, data); 
}
