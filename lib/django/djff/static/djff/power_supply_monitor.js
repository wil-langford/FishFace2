$(document).ready(function() {

    function refresh_psu_monitor() {
        window.ff.celery_async('psu.status_report', function (data, status, jqXHR) {
            console.log(data);
            $('#PSU').css('background-color', 'lightgreen');

            $("#psu_monitor_voltage").html(data.psu_voltage_meas);
            $("#psu_monitor_current").html(data.psu_current_meas);

        }, false, true, 2, function (jqXHR, status, error) {
            $('#PSU').css('background-color', 'red');
            if (status != 'timeout') {
                console.log('non-timeout error on hardware monitor request: ' + status);
                console.log(jqXHR);
                console.log(error);
            }
        });
    }

    window.setInterval(
        function() {
            refresh_psu_monitor();
        }, 2000);


});  // end $(document).ready()