function startPinging() {
    let pingInterval = null;

    console.log("Starting to ping the server every 5 seconds");
    pingInterval = setInterval(sendPing, 30000); // Ping every 30 seconds

    function sendPing() {
        var username = currentUsername; // Use the variable set by the server-side template
        console.log("Sending ping to the server for user:", username);
        
        fetch('/ping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username: username })
        }).then(response => {
            if (!response.ok) {
                console.log("Ping unsuccessful. Server responded with status:", response.status);
                // Handle unsuccessful ping
            } else {
                console.log("Ping successful for user:", username);
            }
        }).catch(error => {
            console.error('Error sending ping:', error);
        });
    }
}

function startInactivityTimer() {
    let time_inactivity;
    document.onmousemove = resetTimer_inactivity;
    document.onkeydown = resetTimer_inactivity;

    function logout_inactivity() {
        fetch('/validate_session', { method: 'HEAD' })
            .then(response => {
                if (response.ok) {  // If the response status is 2xx
                    // Session is active, proceed with the logout
                    $.ajax({
                        url: '/logout',
                        method: 'POST',
                        success: function() {
                            window.location.href = '/login'; // Redirect to login page
                        }
                    });
                } else {
                    // Handle the case where the session is not active
                }
            })
            .catch(error => console.error('Error:', error));
    }

    function resetTimer_inactivity() {
        clearTimeout(time_inactivity);
        time = setTimeout(logout_inactivity, 120000);  // 120000 milliseconds = 2 minutes
    }
};

window.onload = function() {
    console.log("Window loaded, initializing ping process and reset timer");
    startPinging(); // Start the ping process and handle session
    startInactivityTimer(); // Start the inactivity process and handle session
};
