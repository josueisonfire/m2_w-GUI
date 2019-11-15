function play(inDeX)
{
    //console.log("Event detected at index:")
    //console.log(inDeX)
    //document.getElementById(inDeX.toString()).style.backgroundColor = "red";
    if (document.getElementById(inDeX.toString()).innerHTML == " ")
    {
        // for the move property, update... 
        //document.getElementById(inDeX.toString()).innerHTML = "X";
        make_move(inDeX)
    }
    else
    {
        //console.log("Invalid cell pressed.")
    }
}


document.getElementById("0").addEventListener("click", function(){play(0)});
document.getElementById("1").addEventListener("click", function(){play(1)});
document.getElementById("2").addEventListener("click", function(){play(2)});
document.getElementById("3").addEventListener("click", function(){play(3)});
document.getElementById("4").addEventListener("click", function(){play(4)});
document.getElementById("5").addEventListener("click", function(){play(5)});
document.getElementById("6").addEventListener("click", function(){play(6)});
document.getElementById("7").addEventListener("click", function(){play(7)});
document.getElementById("8").addEventListener("click", function(){play(8)});
document.getElementById("reset_button").addEventListener("click", function(){post_to_server(JSON.stringify({"grid" : "", "move":"r"}))});

function write_to_table(json_object)
{
    //console.log("write to table invoked.")
    //console.log(json_object)
    winner = json_object['winner']
    grid = json_object['grid']
    for (var i=0; i < 9; i++)
    {
        document.getElementById(i.toString()).innerHTML = grid[i];
    }
    document.getElementById("winner").innerHTML = winner;
}

function read_from_table(inDeX)
{
    //console.log("reading from table...")
    read_vals = [" "," "," "," "," "," "," "," "," "];
    var i = 0;
    var empty_spaces = 0
    while(document.getElementById(i.toString()) != null)
    {
        read_vals[i] = document.getElementById(i.toString()).innerHTML;
        if (read_vals[i] == " ")
        {
            empty_spaces++;
        }
        i++;
    }
    if (empty_spaces == 0)
    {
        //ITS A TIE!
        read_vals[9] = 'TIE'
    }
    json_obj = JSON.stringify({"grid" : read_vals, "move":inDeX});
    //console.log(json_obj)
    return json_obj;
}

function make_move(inDeX)
{
    //console.log("make_move invoked.")
    // Read from Table
    // Post data to server
    
    return post_to_server(read_from_table(inDeX))
}

function post_to_server(data)
{
    //console.log("Posting to server:")
    //console.log(data)
    $.post("/ttt/play",data,
    function(data) {write_to_table(data);}); 
}

function reset()
{
    //does a RESTful request with 'name' attribute to start tictactoe game. Can be used to reset the game.
    data = null
    //post to server.
    post_to_server(data)
}
