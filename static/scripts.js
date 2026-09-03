$(document).ready(function() {
    // Theme initialization: apply `dark` class for dark mode (prefers-color-scheme or saved preference)
    try {
        var savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark' || (!savedTheme && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.body.classList.add('dark');
            $('#theme_icon').removeClass('fa-moon').addClass('fa-sun');
        } else {
            document.body.classList.remove('dark');
            $('#theme_icon').removeClass('fa-sun').addClass('fa-moon');
        }
    } catch (e) {
        // ignore storage errors
    }

    // Theme toggle button
    $('#theme_toggle').on('click', function() {
        var isDark = document.body.classList.toggle('dark');
        try { localStorage.setItem('theme', isDark ? 'dark' : 'light'); } catch (e) {}
        if (isDark) {
            $('#theme_icon').removeClass('fa-moon').addClass('fa-sun');
        } else {
            $('#theme_icon').removeClass('fa-sun').addClass('fa-moon');
        }
    });
    // ------------------------------------------------------------------
    // 1. Live Digital Clock & System Monitor
    // ------------------------------------------------------------------
    function updateClock() {
        var now = new Date();
        var hours = String(now.getHours()).padStart(2, '0');
        var minutes = String(now.getMinutes()).padStart(2, '0');
        var seconds = String(now.getSeconds()).padStart(2, '0');
        $('#digital-clock').text(hours + ':' + minutes + ':' + seconds);
    }
    updateClock();
    setInterval(updateClock, 1000);

    // ------------------------------------------------------------------
    // 2. Terminal Console Output Helper
    // ------------------------------------------------------------------
    function logTerminal(message, isError) {
        var now = new Date();
        var timeStr = now.toTimeString().split(' ')[0];
        var prefix = isError ? '[ERROR]' : '[INFO]';
        var colorStyle = isError ? 'color: #ff3b5c;' : 'color: #00ff9d;';
        
        var formattedMsg = '<span style="' + colorStyle + '">> [' + timeStr + '] ' + prefix + ' ' + message + '</span>';
        
        $('#message').html(formattedMsg);
        
        // Pulse system status badge
        if (isError) {
            $('#sys-status').text('ATTN REQUIRED').css('color', '#ff3b5c');
            $('.status-dot').css('background-color', '#ff3b5c').css('box-shadow', '0 0 8px #ff3b5c');
        } else {
            $('#sys-status').text('SYSTEM READY').css('color', '#00ff9d');
            $('.status-dot').css('background-color', '#00ff9d').css('box-shadow', '0 0 8px #00ff9d');
        }
    }

    // ------------------------------------------------------------------
    // 3. Train Image
    // ------------------------------------------------------------------
    $('#train_image').click(function() {
        var btn = $(this);
        var student_name = $('#student_name').val().trim();
        var aktu_roll_number = $('#aktu_roll_number').val().trim();

        if (student_name === "" || aktu_roll_number === "") {
            logTerminal("Registration failed: Please enter both Student Name and Roll Number.", true);
            return;
        }

        btn.addClass('pressed');
        logTerminal("Initiating face scan & registration process...", false);

        $.ajax({
            url: '/train_image',
            type: 'POST',
            data: {
                student_name: student_name,
                aktu_roll_number: aktu_roll_number
            },
            success: function(response) {
                btn.removeClass('pressed');
                if (response.status === 'success') {
                    logTerminal(response.message + " (Detected " + (response.face_count || 1) + " face)", false);
                    $('#student_name').val('');
                    $('#aktu_roll_number').val('');
                } else {
                    logTerminal("Error: " + response.message, true);
                }
            },
            error: function() {
                btn.removeClass('pressed');
                logTerminal("Network Error: Failed to communicate with training module.", true);
            }
        });
    });

    // ------------------------------------------------------------------
    // 4. Take Attendance
    // ------------------------------------------------------------------
    $('#take_attendance').click(function() {
        var btn = $(this);
        btn.addClass('pressed');
        logTerminal("Scanning video feed for face recognition...", false);

        $.ajax({
            url: '/take_attendance',
            type: 'POST',
            success: function(response) {
                btn.removeClass('pressed');
                if (response.status === 'success') {
                    logTerminal(response.message, false);
                } else {
                    logTerminal("Attendance Error: " + response.message, true);
                }
            },
            error: function() {
                btn.removeClass('pressed');
                logTerminal("Network Error: Failed to log attendance.", true);
            }
        });
    });

    // ------------------------------------------------------------------
    // 5. Send Attendance via Email
    // ------------------------------------------------------------------
    $('#send_email').click(function() {
        var btn = $(this);
        var email = prompt("Enter recipient email address for attendance log:");

        if (email === null || email.trim() === "") {
            logTerminal("Email dispatch cancelled or empty address.", true);
            return;
        }

        btn.addClass('pressed');
        logTerminal("Compiling attendance report & sending email to: " + email + "...", false);

        $.ajax({
            url: '/send_email',
            type: 'POST',
            data: { email: email.trim() },
            success: function(response) {
                btn.removeClass('pressed');
                if (response.status === 'success') {
                    logTerminal(response.message, false);
                } else {
                    logTerminal("Email Error: " + response.message, true);
                }
            },
            error: function() {
                btn.removeClass('pressed');
                logTerminal("Network Error: Unable to send email report.", true);
            }
        });
    });

    // ------------------------------------------------------------------
    // 6. Delete Data
    // ------------------------------------------------------------------
    $('#delete_data').click(function() {
        var btn = $(this);
        if (confirm("WARNING: Are you sure you want to delete all trained faces, student records, and attendance data?")) {
            btn.addClass('pressed');
            logTerminal("Executing system reset & data purge...", true);

            $.ajax({
                url: '/delete_data',
                type: 'POST',
                success: function(response) {
                    btn.removeClass('pressed');
                    if (response.status === 'success') {
                        logTerminal(response.message, false);
                    } else {
                        logTerminal("Purge Error: " + response.message, true);
                    }
                },
                error: function() {
                    btn.removeClass('pressed');
                    logTerminal("Network Error: System purge request failed.", true);
                }
            });
        }
    });
});
