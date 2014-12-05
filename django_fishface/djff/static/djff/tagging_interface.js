/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {

    function get_new_image(do_post) {
        if (do_post == false) {
            $('input#image_id').attr('value', 'DO_NOT_POST');
        }

        var form = $('#tag_form');
        var data = form.serialize();
        $.ajax({
            type: 'POST',
            url: window.tag_submit_url,
            data: data,
            success: function (data, status, jqXHR) {
                if (data != 0) {
                    $('input#image_id').attr('value', data.id);
                    window.current_image_url = data.url;
                    replace_rasters(data.url);
                    $('div#eph_output').html('' + data.id + '<br />' + data.url)
                } else {
                    $('div#eph_output').html('Got zero back.')
                }
            },
            dataType: 'json'
        });
    }

    $('form#tag_form').submit(function (event) {
        event.preventDefault();
        get_new_image(true);
    });

    $('#researcher_dropdown').change(function (event) {
        var researcher_id = $(this).val();
        if (researcher_id != 'NONE') {
            var researcher_name = $('#researcher_dropdown option:selected').text();

            $('input#researcher_id').attr('value', researcher_id);

            $('#res_name').html(researcher_name);
            $('#res_name2').html(researcher_name);

            $('#researcher_selection_wrapper').css('display', 'none');
            $('#select_researcher_text').css('display', 'none');
            $('#greet_researcher').css('display', 'block');
            $('#canvas_wrapper').css('display', 'block');
            $('#tag_form_wrapper').css('display', 'block');
        }
    });

    $('#change_res').click(function (event) {
        window.location.reload();
    });


    /*
     *  Paper.js code below
     */

    var project = new paper.Project('paper_canvas');
    var view = project.view;
    var tool = new paper.Tool();

    var bright_green = "#66FF66";
    var bright_yellow = "#FFFF66";

    var ZOOM_FACTOR = 3;
    var CIRCLE_RADIUS = 4;

    var real_edp;

    var tag_bounds = {
        height: view.bounds.height / 2,
        width: view.bounds.width,
        x: 0,
        y: view.center.y
    };

    var over_bounds = {
        height: view.bounds.height / 2,
        width: view.bounds.width,
        x: 0,
        y: 0
    };

    var over_mouse_bounds = {
        height: over_bounds.height * ((ZOOM_FACTOR - 1) / ZOOM_FACTOR),
        width: over_bounds.width * ((ZOOM_FACTOR - 1) / ZOOM_FACTOR),
        x: over_bounds.x + over_bounds.width / ZOOM_FACTOR / 2,
        y: over_bounds.y + over_bounds.height / ZOOM_FACTOR / 2
    };

    var tag_layer = project.activeLayer;
    var over_layer = new paper.Layer();

    var tag_raster;
    var over_raster;

    var zoom_rectangle;
    var path;
    var circle;
    var arrow;
    var echo_path;
    var echo_circle;
    var echo_arrow;

    var tag_bord;
    var over_bord;

    function build_tag_layer() {
        tag_layer.activate();

        tag_raster = new paper.Raster('test_image');
        tag_raster.fitBounds(tag_bounds);
        tag_layer.scale(ZOOM_FACTOR, ZOOM_FACTOR, {
            x: tag_bounds.x + tag_bounds.width / 2,
            y: tag_bounds.y + tag_bounds.height / 2
        });

        path = new paper.Path();
        path.strokeColor = bright_green;

        circle = new paper.Path.Circle(new paper.Point(0, 0), CIRCLE_RADIUS);
        circle.strokeColor = bright_green;

        arrow = new paper.Group();
        arrow.addChildren([path, circle]);
        arrow.visible = false;

        tag_bord = new paper.Path.Rectangle(tag_bounds);
        tag_bord.strokeColor = bright_yellow;
    }

    function build_over_layer() {
        over_layer.activate()

        over_raster = new paper.Raster('test_image');
        over_raster.fitBounds(over_bounds);

        over_bord = new paper.Path.Rectangle(over_bounds);
        over_bord.strokeColor = 'black';

        // Draw the borders of where the mouse can point for zooming in the overview pane
        // (for debugging)
        //var over_mouse_bord = new paper.Path.Rectangle(over_mouse_bounds);
        //over_mouse_bord.strokeColor = 'white';

        zoom_rectangle = new paper.Path.Rectangle({
            point: [0, 0],
            size: [over_bounds.width / ZOOM_FACTOR, over_bounds.height / ZOOM_FACTOR],
            strokeColor: bright_yellow
        });

        echo_path = new paper.Path();
        echo_path.strokeColor = bright_green;

        echo_circle = new paper.Path.Circle(new paper.Point(0, 0), CIRCLE_RADIUS / ZOOM_FACTOR);
        echo_circle.strokeColor = bright_green;

        echo_arrow = new paper.Group();
        echo_arrow.addChildren([echo_path, echo_circle]);
        echo_arrow.visible = false;
    }

    function update_tag_raster() {
        var zrp = zoom_rectangle.position;

        tag_layer.position = {
        x: - (zrp.x - over_bord.position.x) * ZOOM_FACTOR + over_bord.position.x,
        y: - (zrp.y - over_bord.position.y) * ZOOM_FACTOR + over_bord.position.y + tag_bord.bounds.y
        }
    }

    function start_arrows(event) {
        var edp = event.downPoint;
        circle.position = edp;
        if (path.segments.length > 0) {
            path.removeSegments(0,path.segments.length);
        }
        path.add(edp, edp);

        var echo_edp = new paper.Point(
            ((edp.x - tag_bord.bounds.x) / ZOOM_FACTOR) + zoom_rectangle.bounds.x,
            ((edp.y - tag_bord.bounds.y) / ZOOM_FACTOR) + zoom_rectangle.bounds.y
        );

        echo_circle.position = echo_edp;
        if (echo_path.segments.length > 0) {
            echo_path.removeSegments(0, echo_path.segments.length);
        }
        echo_path.add(echo_edp, echo_edp);

        real_edp = new paper.Point(
            Math.round((echo_edp.x) * tag_raster.width / over_bounds.width),
            Math.round((echo_edp.y) * tag_raster.height / over_bounds.height)
        );
        $('input#form_start').val('' + real_edp.x + ',' + real_edp.y)
    }

    function finish_arrows(event) {
        var ep = event.point;
        path.lastSegment.point = ep;

        var echo_ep = new paper.Point(
            ((ep.x - tag_bord.bounds.x) / ZOOM_FACTOR) + zoom_rectangle.bounds.x,
            ((ep.y - tag_bord.bounds.y) / ZOOM_FACTOR) + zoom_rectangle.bounds.y
        );
        echo_path.lastSegment.point = echo_ep;

        var real_ep = new paper.Point(
            Math.round((echo_ep.x) * tag_raster.width / over_bounds.width),
            Math.round((echo_ep.y) * tag_raster.height / over_bounds.height)
        );

        var delta = real_edp.subtract(real_ep);

        $('input#form_end').val('' + real_ep.x + ',' + real_ep.y);

        if (delta.x != 0) {
            $('#output_angle').html(Math.atan2(delta.y, delta.x));
        } else{
            if (delta.y>0) {
                $('#output_angle').html('up')
            } else {
                $('#output_angle').html('down')
            }
        }
    }

    tool.onMouseDown = function(event) {
        if (event.downPoint.isInside(tag_bounds)) {
            arrow.visible = true;
            echo_arrow.visible = true;
            start_arrows(event);
        } else {
            zoom_rectangle.visible = true;
            if (event.point.isInside(over_mouse_bounds)) {
                zoom_rectangle.position = event.point;
                update_tag_raster(event.point);
            }

        }
    };

    tool.onMouseDrag = function(event) {
        if (event.downPoint.isInside(tag_bounds)) {
            if (event.point.isInside(tag_bounds)) {
                finish_arrows(event);
                arrow.visible = true;
                echo_arrow.visible = true;
            } else {
                arrow.visible = false;
                echo_arrow.visible = false;
            }
        } else {
            zoom_rectangle.visible = true;
            if (event.point.isInside(over_mouse_bounds)) {
                zoom_rectangle.position = event.point;
                update_tag_raster(event.point);
            }
        }
    };

    function replace_rasters(url) {
        arrow.visible = false;
        echo_arrow.visible = false;
    }

    build_tag_layer();
    build_over_layer();
    update_tag_raster();
    view.draw();
});
