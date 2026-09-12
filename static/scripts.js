$(document).ready(function() {
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
    function logTerminal(message, isError, isWarning) {
        var now = new Date();
        var timeStr = now.toTimeString().split(' ')[0];
        var prefix = isError ? '[ERROR]' : (isWarning ? '[ALERT]' : '[INFO]');
        var colorStyle = isError ? 'color: #e11d48; font-weight: 600;' : (isWarning ? 'color: #d97706; font-weight: 600;' : 'color: #2563eb; font-weight: 500;');
        
        var formattedMsg = '<span style="' + colorStyle + '">> [' + timeStr + '] ' + prefix + ' ' + message + '</span>';
        
        $('#message').html(formattedMsg);
        
        // Pulse system status badge
        if (isError) {
            $('#sys-status').text('ATTN REQUIRED').css('color', '#e11d48');
            $('.status-dot').css({'background-color': '#e11d48', 'box-shadow': '0 0 8px rgba(225, 29, 72, 0.6)'});
        } else if (isWarning) {
            $('#sys-status').text('CAUTION').css('color', '#d97706');
            $('.status-dot').css({'background-color': '#d97706', 'box-shadow': '0 0 8px rgba(217, 119, 6, 0.6)'});
        } else {
            $('#sys-status').text('SYSTEM READY').css('color', '#10b981');
            $('.status-dot').css({'background-color': '#10b981', 'box-shadow': '0 0 8px rgba(16, 185, 129, 0.6)'});
        }
    }

    // ------------------------------------------------------------------
    // 3. Biometric Confirmation HUD Card Helper
    // ------------------------------------------------------------------
    var confirmationTimer = null;

    function showConfirmationCard(type, name, roll, time, photoUrl) {
        var card = $('#confirmation_card');
        var badge = $('#confirm_badge');
        var nameElem = $('#confirm_name');
        var rollElem = $('#confirm_roll');
        var timeElem = $('#confirm_time');
        var avatarElem = $('#confirm_avatar');

        nameElem.text(name || 'Identified Student');
        rollElem.text(roll ? ('Roll No: ' + roll) : 'Verified Biometric Record');
        timeElem.text(time || new Date().toLocaleTimeString());

        if (photoUrl) {
            avatarElem.attr('src', photoUrl).show();
            avatarElem.parent().show();
        } else {
            avatarElem.parent().hide();
        }

        if (type === 'registered') {
            card.css({
                'background': 'rgba(0, 240, 255, 0.05)',
                'border-color': 'rgba(0, 240, 255, 0.4)',
                'box-shadow': '0 0 20px rgba(0, 240, 255, 0.2)'
            });
            badge.html('<i class="fa-solid fa-user-plus"></i> REGISTRATION SUCCESSFUL')
                 .css({ 'background': 'rgba(0, 240, 255, 0.2)', 'color': '#00f0ff', 'border-color': '#00f0ff' });
        } else if (type === 'already_marked') {
            card.css({
                'background': 'rgba(255, 183, 3, 0.05)',
                'border-color': 'rgba(255, 183, 3, 0.4)',
                'box-shadow': '0 0 20px rgba(255, 183, 3, 0.2)'
            });
            badge.html('<i class="fa-solid fa-clock-rotate-left"></i> ALREADY MARKED TODAY')
                 .css({ 'background': 'rgba(255, 183, 3, 0.2)', 'color': '#ffb703', 'border-color': '#ffb703' });
        } else { // attendance verified
            card.css({
                'background': 'rgba(0, 255, 157, 0.05)',
                'border-color': 'rgba(0, 255, 157, 0.4)',
                'box-shadow': '0 0 20px rgba(0, 255, 157, 0.2)'
            });
            badge.html('<i class="fa-solid fa-circle-check"></i> ATTENDANCE CONFIRMED')
                 .css({ 'background': 'rgba(0, 255, 157, 0.2)', 'color': '#00ff9d', 'border-color': '#00ff9d' });
        }

        card.stop(true, true).slideDown(300);

        if (confirmationTimer) clearTimeout(confirmationTimer);
        confirmationTimer = setTimeout(function() {
            card.slideUp(400);
        }, 10000); // Keep visible for 10 seconds
    }

    $('#close_confirm').click(function() {
        if (confirmationTimer) clearTimeout(confirmationTimer);
        $('#confirmation_card').slideUp(200);
    });

    // ------------------------------------------------------------------
    // Browser Webcam Initialization & Frame Capture Helper
    // ------------------------------------------------------------------
    var videoElement = document.getElementById('video_feed');
    var canvasElement = document.getElementById('capture_canvas');
    var cameraActive = false;

    function initCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            logTerminal("Camera Error: Browser does not support webcam media access.", true);
            return;
        }

        navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            },
            audio: false
        })
        .then(function(stream) {
            if (videoElement) {
                videoElement.srcObject = stream;
                videoElement.onloadedmetadata = function() {
                    videoElement.play().catch(function(err) {
                        console.warn("Video playback error:", err);
                    });
                    cameraActive = true;
                    logTerminal("Optical Scanner online: Browser webcam connected successfully.", false);
                };
            }
        })
        .catch(function(err) {
            cameraActive = false;
            console.error("Camera access error:", err);
            var errDetail = "Camera access denied or no camera device found.";
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                errDetail = "Camera permission denied. Please allow camera access in your browser address bar.";
            } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                errDetail = "No webcam hardware detected on this device.";
            } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
                errDetail = "Webcam is currently locked or in use by another application.";
            }
            logTerminal("Camera Error: " + errDetail, true);
        });
    }

    initCamera();

    function captureVideoFrame() {
        if (!videoElement || !videoElement.videoWidth || !videoElement.videoHeight) {
            return null;
        }
        var canvas = canvasElement || document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/jpeg', 0.85);
    }

    // ------------------------------------------------------------------
    // 4. Train Image (Biometric Registration)
    // ------------------------------------------------------------------
    $('#train_image').click(function() {
        var btn = $(this);
        var student_name = $('#student_name').val().trim();
        var roll_no = $('#roll_no').val().trim();

        if (student_name === "" || roll_no === "") {
            logTerminal("Registration failed: Please enter both Student Name and Roll Number.", true);
            return;
        }

        var imageData = captureVideoFrame();
        if (!imageData) {
            logTerminal("Registration failed: Camera feed is not ready. Please ensure your browser camera is allowed and active.", true);
            return;
        }

        btn.addClass('pressed');
        logTerminal("Capturing optical snapshot & training biometric model for: " + student_name + "...", false);

        $.ajax({
            url: '/train_image',
            type: 'POST',
            data: {
                student_name: student_name,
                roll_no: roll_no,
                image_data: imageData
            },
            success: function(response) {
                btn.removeClass('pressed');
                if (response.status === 'success') {
                    logTerminal(response.message, false);
                    showConfirmationCard('registered', response.student_name, response.roll_number, response.timestamp, response.photo);
                    $('#student_name').val('');
                    $('#roll_no').val('');
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
    // 5. Take Attendance (Facial Recognition)
    // ------------------------------------------------------------------
    $('#take_attendance').click(function() {
        var btn = $(this);

        var imageData = captureVideoFrame();
        if (!imageData) {
            logTerminal("Attendance failed: Camera feed is not ready. Please ensure your browser camera is allowed and active.", true);
            return;
        }

        btn.addClass('pressed');
        logTerminal("Scanning optical snapshot for facial biometric recognition...", false);

        $.ajax({
            url: '/take_attendance',
            type: 'POST',
            data: {
                image_data: imageData
            },
            success: function(response) {
                btn.removeClass('pressed');
                if (response.status === 'success') {
                    logTerminal(response.message, false);
                    showConfirmationCard('verified', response.student_name, response.roll_number, response.timestamp, response.photo);
                } else if (response.status === 'info' && response.already_marked) {
                    logTerminal(response.message, false, true);
                    showConfirmationCard('already_marked', response.student_name, response.roll_number, response.timestamp, response.photo);
                } else if (response.status === 'warning') {
                    logTerminal("Warning: " + response.message, false, true);
                } else {
                    logTerminal("Attendance Error: " + response.message, true);
                }
            },
            error: function() {
                btn.removeClass('pressed');
                logTerminal("Network Error: Failed to process attendance.", true);
            }
        });
    });

    // ------------------------------------------------------------------
    // 6. Send Attendance via Email (Interactive Modal)
    // ------------------------------------------------------------------
    var reportModal = null;
    function getReportModal() {
        if (!reportModal && window.bootstrap && bootstrap.Modal) {
            reportModal = new bootstrap.Modal(document.getElementById('sendReportModal'));
        }
        return reportModal;
    }

    $('#send_email').click(function() {
        var modal = getReportModal();
        $('#modal_alert').hide().removeClass('alert-success alert-danger alert-warning');
        $('#btn_mailto_fallback').hide();
        $('#btn_send_modal').prop('disabled', false).html('<span class="btn-label"><i class="fa-solid fa-paper-plane"></i> SEND NOW</span>');

        // Check current SMTP configuration from backend
        $.ajax({
            url: '/get_email_config',
            type: 'GET',
            success: function(res) {
                if (res.configured) {
                    $('#smtp_status_chip').text('Configured')
                        .css({'background': '#ecfdf5', 'color': '#059669', 'border': '1px solid #a7f3d0'});
                    $('#sender_email_input').val(res.sender_email);
                    $('#sender_password_input').val('').attr('placeholder', 'Saved in .env (leave blank to keep)');
                } else {
                    $('#smtp_status_chip').text('Setup Needed')
                        .css({'background': '#fffbeb', 'color': '#d97706', 'border': '1px solid #fde68a'});
                    $('#sender_password_input').attr('placeholder', '16-digit Google App Password');
                    // Automatically open drawer if setup is needed
                    $('#smtp_inputs_drawer').slideDown(200);
                }
            }
        });

        if (modal) {
            modal.show();
        } else {
            // Fallback if bootstrap modal wasn't initialized
            $('#sendReportModal').show().addClass('show');
        }
    });

    // Toggle Sender credentials drawer
    $('#toggle_smtp_details').click(function() {
        $('#smtp_inputs_drawer').slideToggle(200);
        $(this).find('.toggle-icon').toggleClass('fa-chevron-down fa-chevron-up');
    });

    $('#btn_send_modal').click(function() {
        var btn = $(this);
        var recipientEmail = $('#recipient_email').val().trim();
        var senderEmail = $('#sender_email_input').val().trim();
        var senderPassword = $('#sender_password_input').val().trim();
        var saveCreds = $('#save_credentials_check').is(':checked');
        var alertBox = $('#modal_alert');

        if (!recipientEmail) {
            alertBox.removeClass('alert-success alert-warning').addClass('alert-danger')
                .html('<i class="fa-solid fa-triangle-exclamation"></i> Please enter the recipient email address.')
                .slideDown(200);
            return;
        }

        btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Sending...');
        alertBox.slideUp(100);

        $.ajax({
            url: '/send_email',
            type: 'POST',
            data: {
                email: recipientEmail,
                sender_email: senderEmail,
                sender_password: senderPassword,
                save_credentials: saveCreds
            },
            success: function(response) {
                btn.prop('disabled', false).html('<span class="btn-label"><i class="fa-solid fa-paper-plane"></i> SEND NOW</span>');

                if (response.status === 'success') {
                    alertBox.removeClass('alert-danger alert-warning').addClass('alert-success')
                        .html('<i class="fa-solid fa-circle-check"></i> ' + response.message)
                        .slideDown(200);
                    logTerminal(response.message, false);

                    setTimeout(function() {
                        var modal = getReportModal();
                        if (modal) modal.hide();
                    }, 2500);
                } else {
                    var alertClass = (response.status === 'needs_config' || response.status === 'auth_error') ? 'alert-warning' : 'alert-danger';
                    alertBox.removeClass('alert-success alert-danger alert-warning').addClass(alertClass)
                        .html('<i class="fa-solid fa-triangle-exclamation"></i> ' + response.message)
                        .slideDown(200);
                    logTerminal(response.message, true);

                    if (response.mailto_url) {
                        $('#btn_mailto_fallback').attr('href', response.mailto_url).fadeIn(200);
                    }
                }
            },
            error: function() {
                btn.prop('disabled', false).html('<span class="btn-label"><i class="fa-solid fa-paper-plane"></i> SEND NOW</span>');
                alertBox.removeClass('alert-success alert-warning').addClass('alert-danger')
                    .html('<i class="fa-solid fa-circle-xmark"></i> Network Error: Failed to reach server.')
                    .slideDown(200);
                logTerminal("Network error contacting email dispatch service.", true);
            }
        });
    });

    // ------------------------------------------------------------------
    // 7. Delete / Reset Data
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
                        $('#confirmation_card').slideUp(200);
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
