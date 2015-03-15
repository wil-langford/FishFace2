$(document).ready(function() {

    fabric.BuilderArrow = fabric.util.createClass({
        initialize: function(canvas) {
            var center = canvas.getCenter();

            this.line = new fabric.Line([0,0,0,0], {
                originX: 'center',
                originY: 'center',
                stroke: 'blue',
                strokeWidth: 1
            });

            this.circle = new fabric.Circle({
                left:0,
                top:0,
                originX: 'center',
                originY: 'center',
                fill: '',
                stroke: 'blue',
                radius: 1,
                strokeWidth: 2
            });

            canvas.add(this.circle);
            canvas.add(this.line);

            this.circle.setCoords();
            this.line.setCoords();
        },

        start_arrow: function(point) {
            this.line.set({
                x1: point.x,
                y1: point.y
            });
            this.line.setCoords();

            this.circle.set({
                left: point.x,
                top: point.y
            });
            this.circle.setCoords();
        },

        end_arrow: function(pointer) {
            this.line.set({
                x2: pointer.x,
                y2: pointer.y
            });

            this.line.setCoords();
        },

        update_arrow_with_angle: function (angle) {
            var x = Math.round(Math.cos(-angle)*7);
            var y = -Math.round(Math.sin(-angle)*7);

            this.start_arrow({
                x: 10-x,
                y: 10-y
            });

            this.end_arrow({
                x: 10+x,
                y: 10+y
            });
        }
    });

    fabric.BuilderPane = fabric.util.createClass(fabric.StaticCanvas, {
        initialize: function(canvas_id) {
            this.callSuper('initialize', canvas_id);

            this.border_rectangle = new fabric.Rect({
                top: 0,
                left: 0,
                fill: '',
                stroke: 'blue',
                strokeWidth: 1,
                height: 19,
                width: 19
            });
            this.add(this.border_rectangle);

            this.arrow = new fabric.BuilderArrow(this);
        },
        png_with_angle: function(angle) {
            this.arrow.update_arrow_with_angle(angle);
            this.renderAll();
            return this.toDataURL({
                format: 'png'
            });
        }
    });

    window.ff.builder = new fabric.BuilderPane('builder_canvas', window.ff.ZOOM_BORDER_COLOR);

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

            window.ff.celery_async('camera.push_capture_request',
                function(data, status, jqXHR) {
                    window.ff.refresh_cal_images();
                },
                {
                    requested_capture_timestamp: 0,
                    meta: {
                        species: $('#species').val(),
                        xp_id: $('#xp_id').val()
                    }
                },
                true
            );
        }
    });

    $('.angle_bullet').each(function() {
        var bullet = $(this);
        var angle_text = bullet.attr('data-angle');
        if (angle_text != 'None') {
            var angle = Number(angle_text);
            var data_url = window.ff.builder.png_with_angle(angle);
            bullet.html('<img src="' + data_url + '" />');
        }
    });


});  // end $(document).ready()