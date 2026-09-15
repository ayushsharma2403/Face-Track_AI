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

        card.removeClass('animating-in');
        if (card[0]) {
            void card[0].offsetWidth; // trigger reflow for clean re-animation
        }
        card.addClass('animating-in').stop(true, true).slideDown(280);

        if (confirmationTimer) clearTimeout(confirmationTimer);
        confirmationTimer = setTimeout(function() {
            card.slideUp(350, function() {
                card.removeClass('animating-in');
            });
        }, 10000); // Keep visible for 10 seconds
    }

    $('#close_confirm').click(function() {
        if (confirmationTimer) clearTimeout(confirmationTimer);
        $('#confirmation_card').slideUp(200, function() {
            $(this).removeClass('animating-in');
        });
    });

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

        btn.addClass('pressed');
        logTerminal("Initiating burst scan & generating illumination-invariant profiles for: " + student_name + "...", false);

        $.ajax({
            url: '/train_image',
            type: 'POST',
            data: {
                student_name: student_name,
                roll_no: roll_no
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
        btn.addClass('pressed');
        logTerminal("Scanning optical feed for facial biometric recognition...", false);

        $.ajax({
            url: '/take_attendance',
            type: 'POST',
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

    // ------------------------------------------------------------------
    // 8. Role Switcher Modal Logic (Admin / User Toggle)
    // ------------------------------------------------------------------
    var switchRoleModal = null;
    function getSwitchRoleModal() {
        if (!switchRoleModal && window.bootstrap && bootstrap.Modal) {
            var el = document.getElementById('switchRoleModal');
            if (el) switchRoleModal = new bootstrap.Modal(el);
        }
        return switchRoleModal;
    }

    var selectedTargetRole = (window.CURRENT_USER_ROLE === 'admin') ? 'user' : 'admin';

    function updateSwitchModalUI(targetRole) {
        selectedTargetRole = targetRole;
        if (targetRole === 'admin') {
            $('#modal_tab_admin').addClass('active admin-active');
            $('#modal_tab_user').removeClass('active user-active');
            $('#modal_admin_password_area').slideDown(200);
            $('#target_role_text').text('Admin');
            $('#modal_admin_password').focus();
        } else {
            $('#modal_tab_user').addClass('active user-active');
            $('#modal_tab_admin').removeClass('active admin-active');
            $('#modal_admin_password_area').slideUp(200);
            $('#target_role_text').text('User');
        }
        $('#switch_modal_alert').hide().text('');
    }

    $('#btn_open_switch_role').click(function() {
        var modal = getSwitchRoleModal();
        var defaultTarget = (window.CURRENT_USER_ROLE === 'admin') ? 'user' : 'admin';
        $('#modal_admin_password').val('');
        $('#switch_modal_alert').hide().text('');
        updateSwitchModalUI(defaultTarget);
        if (modal) modal.show();
    });

    $('#modal_tab_admin').click(function() {
        updateSwitchModalUI('admin');
    });

    $('#modal_tab_user').click(function() {
        updateSwitchModalUI('user');
    });

    $('#btn_confirm_switch_role').click(function() {
        var btn = $(this);
        var password = $('#modal_admin_password').val().trim();
        var alertBox = $('#switch_modal_alert');

        if (selectedTargetRole === 'admin' && !password) {
            alertBox.removeClass('alert-success').addClass('alert-danger')
                .html('<i class="fa-solid fa-circle-exclamation me-1"></i> Please enter the administrator password.').show();
            $('#modal_admin_password').focus();
            return;
        }

        btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2" role="status"></span> Switching...');
        alertBox.hide();

        $.ajax({
            url: '/switch_role',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                target_role: selectedTargetRole,
                password: password
            }),
            success: function(res) {
                btn.prop('disabled', false).html('<span class="btn-label"><i class="fa-solid fa-check-circle me-1"></i> Switch to ' + (selectedTargetRole === 'admin' ? 'Admin' : 'User') + '</span>');
                if (res.status === 'success') {
                    alertBox.removeClass('alert-danger').addClass('alert-success')
                        .html('<i class="fa-solid fa-circle-check me-1"></i> ' + res.message).show();
                    setTimeout(function() {
                        window.location.reload();
                    }, 600);
                } else {
                    alertBox.removeClass('alert-success').addClass('alert-danger')
                        .html('<i class="fa-solid fa-triangle-exclamation me-1"></i> ' + res.message).show();
                }
            },
            error: function(xhr) {
                btn.prop('disabled', false).html('<span class="btn-label"><i class="fa-solid fa-check-circle me-1"></i> Switch to ' + (selectedTargetRole === 'admin' ? 'Admin' : 'User') + '</span>');
                var msg = 'Failed to switch role.';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg = xhr.responseJSON.message;
                }
                alertBox.removeClass('alert-success').addClass('alert-danger')
                    .html('<i class="fa-solid fa-triangle-exclamation me-1"></i> ' + msg).show();
            }
        });
    });

    // Enter key submits switch role modal
    $('#modal_admin_password').keypress(function(e) {
        if (e.which === 13) {
            $('#btn_confirm_switch_role').click();
        }
    });

    // ------------------------------------------------------------------
    // 9. Automatic Attendance Scanner (User Mode Only)
    // ------------------------------------------------------------------
    if (window.CURRENT_USER_ROLE === 'user') {
        var autoScanCooldown = false;
        var autoScanInterval = null;

        function runAutoScan() {
            if (autoScanCooldown) return;

            $.ajax({
                url: '/auto_attendance_scan',
                type: 'POST',
                timeout: 3000,
                success: function(res) {
                    if (res.status === 'success') {
                        logTerminal("[AUTO-ATTENDANCE] " + res.message + " (Confidence: " + res.confidence + "%)", false);
                        showConfirmationCard('verified', res.student_name, res.roll_number, res.timestamp, res.photo);

                        // Cooldown for 6 seconds to prevent duplicate spamming
                        autoScanCooldown = true;
                        setTimeout(function() {
                            autoScanCooldown = false;
                        }, 6000);
                    } else if (res.status === 'already_marked') {
                        // Already marked today, show info but enforce 8s cooldown
                        logTerminal("[AUTO-ATTENDANCE] " + res.message, false, true);
                        showConfirmationCard('already_marked', res.student_name, res.roll_number, res.timestamp, res.photo);

                        autoScanCooldown = true;
                        setTimeout(function() {
                            autoScanCooldown = false;
                        }, 8000);
                    }
                },
                error: function() {
                    // Silent fail during continuous scanning loop
                }
            });
        }

        // Start scan loop after camera stream stabilizes (2.5s initial delay)
        setTimeout(function() {
            autoScanInterval = setInterval(runAutoScan, 1500);
        }, 2500);
    }

    // ------------------------------------------------------------------
    // 10. Ambient Mouse Pointer Glow & Dynamic Click Interactions
    // ------------------------------------------------------------------
    var $ambientGlow = $('<div id="ambient-cursor-glow" class="ambient-cursor-glow"></div>');
    $('body').append($ambientGlow);

    var targetX = -999, targetY = -999;
    var currentX = -999, currentY = -999;
    var isGlowActive = false;

    // High performance 60fps lerp animation loop for organic ambient tracking
    function updateAmbientCursor() {
        if (isGlowActive) {
            currentX += (targetX - currentX) * 0.22;
            currentY += (targetY - currentY) * 0.22;
            $ambientGlow.css('transform', 'translate3d(' + currentX + 'px, ' + currentY + 'px, 0)');
        }
        requestAnimationFrame(updateAmbientCursor);
    }
    requestAnimationFrame(updateAmbientCursor);

    $(window).on('mousemove', function(e) {
        targetX = e.clientX;
        targetY = e.clientY;
        if (!isGlowActive) {
            currentX = targetX;
            currentY = targetY;
            $ambientGlow.css('opacity', '1');
            isGlowActive = true;
        }
    });

    $(window).on('mouseleave', function() {
        $ambientGlow.css('opacity', '0');
        isGlowActive = false;
    });

    // Ambient glow expansion when hovering over interactive elements
    $(document).on('mouseenter', '.neu-btn, .neu-input-wrapper, .neu-card, .status-badge, .clear-glass-close, .modal-content, a, button', function() {
        $ambientGlow.addClass('active-hover');
    });

    $(document).on('mouseleave', '.neu-btn, .neu-input-wrapper, .neu-card, .status-badge, .clear-glass-close, .modal-content, a, button', function() {
        $ambientGlow.removeClass('active-hover');
    });

    // Specular Glass Ripple inside Buttons on Click
    $(document).on('pointerdown', '.neu-btn', function(e) {
        if (e.which === 3) return;
        var btn = $(this);
        var offset = btn.offset();
        var relX = e.pageX - offset.left;
        var relY = e.pageY - offset.top;

        var $ripple = $('<span class="btn-ripple"></span>');
        $ripple.css({
            left: relX + 'px',
            top: relY + 'px'
        });
        btn.append($ripple);

        setTimeout(function() {
            $ripple.remove();
        }, 580);
    });
});
