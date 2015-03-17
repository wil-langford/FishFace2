$(document).ready(function() {

    function refresh_remote_hardware_monitor() {
        var payload = {
            command: 'raspi_monitor'
        };
        $.ajax({
            type: 'POST',
            url: window.ff.telemetry_proxy_url,  // set by inline javascript on the main page
            data: payload,
            timeout: 2000,
            error: function (jqXHR, status, error) {
                $('#RASPI').css('background-color', 'red');
                $('#CJC').css('background-color', 'gray');
                $('#DP').css('background-color', 'gray');
                if (status != 'timeout') {
                    console.log('non-timeout error on hardware monitor request: ' + status);
                    console.log(jqXHR);
                    console.log(error);
                }
            },
            success: function (data, status, jqXHR) {
                if (data.command=='raspi_monitor') {
                    $('#RASPI').css('background-color', 'lightgreen');
                } else {
                    $('#RASPI').css('background-color', 'red');
                }

                for (idx in data.threads) {
                    var thr = data.threads[idx];

                    var thr_status_element_id = {
                        capturejob_controller: 'CJC',
                        deathcry_publisher: 'DP'
                    }[thr.name];

                    var thr_status_element = $("#" + thr_status_element_id);

                    if (thr.delta < 2) {
                        thr_status_element.css('background-color', 'lightgreen');
                    } else {
                        thr_status_element.css('background-color', 'red');
                    }

                    $("#psu_monitor_voltage").html(data.psu_voltage_meas);
                    $("#psu_monitor_current").html(data.psu_current_meas);
                }
            },
            dataType: 'json'
        });
    }

    window.setInterval(
        function() {
            refresh_remote_hardware_monitor();
        }, 2000);


});  // end $(document).ready()