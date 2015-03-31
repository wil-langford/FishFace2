$(document).ready(function() {

    window.ff.refresh_cal_images = function() {
        $('#cal_images_wrapper').empty();
        $.ajax({
            type: 'POST',
            url: window.ff.xp_detail_cals_url,
            data: {},
            success: function(data, status, jqXHR) {
                $('#cal_images_wrapper').html(data.cal_images_chunk);
            },
            error: function(jqXHR, status, error) {
                console.log(error);
            },
            dataType: 'json'
        });
    };
    window.ff.refresh_cal_images();

    $('#cal_button').on('click', function(event) {
        event.preventDefault();
        if ($('#cal_ready').prop('checked')) {
            $('#cal_ready').prop('checked', false);

            window.ff.celery_async(
                'camera.queue_capture_request',
                function(data, status, jqXHR) {
                    window.setTimeout(window.ff.refresh_cal_images, 500)
                },
                {
                    requested_capture_timestamp: Math.floor(Date.now() / 1000),
                    meta: {
                        species: $('#species').val(),
                        xp_id: $('#xp_id').val(),
                        cjr_id: 0,
                        is_cal_image: true,
                        voltage: 0,
                        current: 0
                    }
                },
                true
            );
        }
    });

    $('.angle_bullet').each(function() {
        var bullet = $(this);
        // Indexed by the length of angle_text that requires the indexed level of padding.
        var zero_pads = ['','00','0'];
        var angle_text = bullet.attr('data-angle');
        if (angle_text != 'None') {
            var angle = Number(angle_text);
            angle = angle < 0 ? angle + 360 : angle;
            angle_text = angle + '';
            bullet.html('<img src="' + window.ff.angle_bullet_base_url +
                (angle_text.length >= 3 ? '' : zero_pads[angle_text.length]) +
                angle_text + '.png" />');
        } else {
            bullet.html('<img src="' + window.ff.angle_bullet_base_url + 'empty.png" />');
        }
    });


});  // end $(document).ready()