/**
 * Created by wil on 12/2/14.
 */

window.onload = function() {

    window.ff.ARROW_CIRCLE_RADIUS = 5;
    window.ff.ZOOM_FACTOR = 3;

    if (window.ff == undefined) { window.ff = {}; }

    $('#change_res').click(function (event) {
        window.location.reload();
    });

    /*
     * Paper.js code below
     */

    window.ff.Border = function(view, width, color) {
        this.path = new paper.Path.Rectangle(view.bounds);
        this.path.strokeWidth = width;
        this.path.strokeColor = color;
    };

    window.ff.Arrow = function(point, width, color, radius) {
        this.path = new paper.Path();
        this.circle = new paper.Path.Circle(point, window.ff.ARROW_CIRCLE_RADIUS);
        this.path.strokeWidth = width;
        this.path.strokeColor = color;
        this.circle.strokeWidth = width;
        this.circle.strokeColor = color;
        this.group = new paper.Group([this.path, this.circle]);

        this.start = function(point) {
            if (this.path.segments.length > 0) {
                this.path.removeSegments(0, this.path.segments.length);
            }

            this.circle.position = point;
            this.path.add(point, point);
            this.group.visible = true;
        };

        this.end = function(point) {
            this.path.lastSegment.point = point;
            this.group.visible = true;
        };

        this.hide = function() {
            this.group.visible = false;
        };
    };

    window.ff.Pane = function(canvas, border_width, border_color) {
        this.canvas = canvas;

        this.project = new paper.Project(this.canvas);
        this.view = this.project.view;
        this.image_layer = this.project.activeLayer;
        this.upper_layer = new paper.Layer();
        this.bounds = this.view.bounds;

        this.upper_layer.activate();
        this.border = new window.ff.Border(this.view, border_width, border_color);

        this.arrow = new window.ff.Arrow([0, 0], 1, 'lightgreen');
        this.arrow.group.remove();
        this.image_layer.addChild(this.arrow.group);
        this.arrow.hide();

        this.add_raster = function(raster_source) {
            this.raster_source = raster_source;
            this.image_layer.activate();
            this.raster = new paper.Raster(this.raster_source);
            this.raster.sendToBack();
            this.raster.fitBounds(this.bounds);
            this.view.draw();
        };

        this.add_zoom_border = function(zoom_factor, border_width, border_color, update_pane) {
            this.update_pane = update_pane;

            var bounds = {
                x: 0, y: 0,
                width: over_pane.bounds.width / window.ff.ZOOM_FACTOR,
                height: over_pane.bounds.height / window.ff.ZOOM_FACTOR
            };

            this.zoom_border = new paper.Path.Rectangle(bounds);
            this.zoom_border.remove();
            this.upper_layer.addChild(this.zoom_border);
            this.zoom_border.strokeWidth = border_width;
            this.zoom_border.strokeColor = border_color;

            this.zoom_click_bounds = {
                x: bounds.width / 2,
                y: bounds.height / 2,
                height: this.bounds.height - bounds.height,
                width: this.bounds.width - bounds.width
            };

            this.zoom_move = function(point) {
                this.zoom_border.position = {
                    x: Math.min(Math.max(point.x, this.zoom_click_bounds.x),
                        this.zoom_click_bounds.x + this.zoom_click_bounds.width),
                    y: Math.min(Math.max(point.y, this.zoom_click_bounds.y),
                        this.zoom_click_bounds.y + this.zoom_click_bounds.height)
                };

                this.update_pane.image_layer.position = this.zoom_border.bounds.topLeft.multiply(
                    -window.ff.ZOOM_FACTOR).add(this.update_pane.bounds.center.multiply(window.ff.ZOOM_FACTOR));
                this.update_pane.view.draw();
            };

            this.zoom_reset = function() {
                this.zoom_move({x: this.bounds.width/2, y: this.bounds.height/2});
            };

            this.zoom_reset();
        };

    };

    var scope = paper.PaperScope();
    var tool = new paper.Tool();

    var over_pane, tag_pane, tool, down_target;

    over_pane = new window.ff.Pane('over_canvas', 3, 'black');
    window.ff.over_pane = over_pane;
    over_pane.add_raster('current_image');

    over_pane.view.draw();

    tag_pane = new window.ff.Pane('tag_canvas', 3, 'yellow');
    window.ff.tag_pane = tag_pane;
    tag_pane.add_raster('current_image');
    tag_pane.raster.scale(window.ff.ZOOM_FACTOR, tag_pane.border.center);
    tag_pane.view.draw();

    over_pane.add_zoom_border(window.ff.ZOOM_FACTOR, 1, 'yellow', tag_pane);

    tool.onMouseDown = function(event) {
        down_target = event.event.target.id;
        var ep = event.point;

        if (down_target == 'over_canvas') {
            over_pane.zoom_move(ep);
        } else {
            tag_pane.arrow.start(ep);
            var echo_ep = new paper.Point(
                ep.x * (over_pane.zoom_border.bounds.width / tag_pane.bounds.width) + over_pane.zoom_border.bounds.x,
                ep.y * (over_pane.zoom_border.bounds.height / tag_pane.bounds.height) + over_pane.zoom_border.bounds.y
            );
            over_pane.arrow.start(echo_ep);
            over_pane.view.draw();
        }
    };

    tool.onMouseDrag = function(event) {
        var ep = event.point;

        if (down_target == 'over_canvas' && event.event.target.id == 'over_canvas') {
            over_pane.zoom_move(ep);
        }

        if (down_target == 'tag_canvas') {
            if (event.event.target.id == 'tag_canvas') {
                tag_pane.arrow.end(ep);
                var echo_ep = new paper.Point(
                    ep.x * (over_pane.zoom_border.bounds.width / tag_pane.bounds.width) + over_pane.zoom_border.bounds.x,
                    ep.y * (over_pane.zoom_border.bounds.height / tag_pane.bounds.height) + over_pane.zoom_border.bounds.y
                );
                over_pane.arrow.end(echo_ep);
                over_pane.view.draw();
            } else {
                tag_pane.arrow.hide();
                over_pane.arrow.hide();
                over_pane.view.draw();
            }
        }
    };

    tool.onMouseUp = function(event) {
        if (event.event.target.id == 'tag_canvas' && down_target == 'tag_canvas') {
            var real_start = new paper.Point(
                Math.round((event.downPoint.x / window.ff.ZOOM_FACTOR + over_pane.zoom_border.bounds.x) *
                (over_pane.raster.width / over_pane.bounds.width)),
                Math.round((event.downPoint.y / window.ff.ZOOM_FACTOR + over_pane.zoom_border.bounds.y) *
                (over_pane.raster.height / over_pane.bounds.height))
            );
            var real_end = new paper.Point(
                Math.round((event.point.x / window.ff.ZOOM_FACTOR + over_pane.zoom_border.bounds.x) *
                (over_pane.raster.width / over_pane.bounds.width)),
                Math.round((event.point.y / window.ff.ZOOM_FACTOR + over_pane.zoom_border.bounds.y) *
                (over_pane.raster.height / over_pane.bounds.height))
            );

            $('input#form_start').val('' + real_start.x + ',' + real_start.y);
            $('input#form_end').val('' + real_end.x + ',' + real_end.y);
            //console.log('start: ' + $('input#form_start').val() + ' end: ' + $('input#form_end').val());
        }
    }

    tool.onMouseOver = function(event) {
        tag_pane.view.draw();
        over_pane.view.draw();
    }

    function get_new_image(do_post) {
        if (do_post == false) {
            $('input#image_id').attr('value', 'DO_NOT_POST');
        }

        var form = $('#tag_form');
        var data = form.serialize();
        $.ajax({
            type: 'POST',
            url: window.ff.tag_submit_url,  // set by inline javascript on the main page
            data: data,
            success: function (data, status, jqXHR) {
                if (data != 0) {
                    $('input#image_id').attr('value', data.id);
                    $('img#current_image').attr('src', data.url);
                    over_pane.arrow.hide();

                    tag_pane.arrow.hide();

                    $('input#form_start').val('NONE');
                    $('input#form_end').val('NONE');
                }
            },
            dataType: 'json'
        });

        tag_pane.project.draw();
        over_pane.project.draw();
        $('canvas#tag_canvas').focus();
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

            get_new_image(false);
            over_pane.zoom_reset();
        }
    });

    /* TODO: remove below debugging */

    var eph_researcher_id = $('#researcher_dropdown').val();
    if (eph_researcher_id != 'NONE') {
        var eph_researcher_name = $('#researcher_dropdown option:selected').text();

        $('input#researcher_id').attr('value', eph_researcher_id);

        $('#res_name').html(eph_researcher_name);
        $('#res_name2').html(eph_researcher_name);

        $('#researcher_selection_wrapper').css('display', 'none');
        $('#select_researcher_text').css('display', 'none');
        $('#greet_researcher').css('display', 'block');
        $('#canvas_wrapper').css('display', 'block');
        $('#tag_form_wrapper').css('display', 'block');

        get_new_image(false);
        over_pane.zoom_reset();
    }

    /* TODO: remove above */

};    // end window.onload()




//$(document).oldReady(function() {
//
//
//
//
//    /*
//     *  Paper.js code below
//     */
//
//    var project = new paper.Project('paper_canvas');
//    var view = project.view;
//    var tool = new paper.Tool();
//
//    var bright_green = "#66FF66";
//    var bright_yellow = "#FFFF66";
//
//    var ZOOM_FACTOR = 3;
//    var ARROW_CIRCLE_RADIUS = 4;
//
//    var real_edp;
//
//    var tag_bounds = {
//        height: view.bounds.height / 2,
//        width: view.bounds.width,
//        x: 0,
//        y: view.center.y
//    };
//
//    var over_bounds = {
//        height: view.bounds.height / 2,
//        width: view.bounds.width,
//        x: 0,
//        y: 0
//    };
//
//    var over_mouse_bounds = {
//        height: over_bounds.height * ((ZOOM_FACTOR - 1) / ZOOM_FACTOR),
//        width: over_bounds.width * ((ZOOM_FACTOR - 1) / ZOOM_FACTOR),
//        x: over_bounds.x + over_bounds.width / ZOOM_FACTOR / 2,
//        y: over_bounds.y + over_bounds.height / ZOOM_FACTOR / 2
//    };
//
//    var tag_layer = project.activeLayer;
//    var over_layer = new paper.Layer();
//
//    var tag_raster;
//    var over_raster;
//
//    var zoom_rectangle;
//    var path;
//    var circle;
//    var arrow;
//    var echo_path;
//    var echo_circle;
//    var echo_arrow;
//
//    var tag_bord;
//    var over_bord;
//
//    function build_tag_layer() {
//        tag_layer.activate();
//
//        tag_raster = new paper.Raster('test_image');
//        tag_raster.fitBounds(tag_bounds);
//        tag_layer.scale(ZOOM_FACTOR, ZOOM_FACTOR, {
//            x: tag_bounds.x + tag_bounds.width / 2,
//            y: tag_bounds.y + tag_bounds.height / 2
//        });
//
//        path = new paper.Path();
//        path.strokeColor = bright_green;
//
//        circle = new paper.Path.Circle(new paper.Point(0, 0), ARROW_CIRCLE_RADIUS);
//        circle.strokeColor = bright_green;
//
//        arrow = new paper.Group();
//        arrow.addChildren([path, circle]);
//        arrow.visible = false;
//
//        tag_bord = new paper.Path.Rectangle(tag_bounds);
//        tag_bord.strokeColor = bright_yellow;
//    }
//
//    function build_over_layer() {
//        over_layer.activate()
//
//        over_raster = new paper.Raster('test_image');
//        over_raster.fitBounds(over_bounds);
//
//        over_bord = new paper.Path.Rectangle(over_bounds);
//        over_bord.strokeColor = 'black';
//
//        // Draw the borders of where the mouse can point for zooming in the overview pane
//        // (for debugging)
//        //var over_mouse_bord = new paper.Path.Rectangle(over_mouse_bounds);
//        //over_mouse_bord.strokeColor = 'white';
//
//        zoom_rectangle = new paper.Path.Rectangle({
//            point: [0, 0],
//            size: [over_bounds.width / ZOOM_FACTOR, over_bounds.height / ZOOM_FACTOR],
//            strokeColor: bright_yellow
//        });
//
//        echo_path = new paper.Path();
//        echo_path.strokeColor = bright_green;
//
//        echo_circle = new paper.Path.Circle(new paper.Point(0, 0), ARROW_CIRCLE_RADIUS / ZOOM_FACTOR);
//        echo_circle.strokeColor = bright_green;
//
//        echo_arrow = new paper.Group();
//        echo_arrow.addChildren([echo_path, echo_circle]);
//        echo_arrow.visible = false;
//    }
//
//    function update_tag_raster() {
//        var zrp = zoom_rectangle.position;
//
//        tag_layer.position = {
//        x: - (zrp.x - over_bord.position.x) * ZOOM_FACTOR + over_bord.position.x,
//        y: - (zrp.y - over_bord.position.y) * ZOOM_FACTOR + over_bord.position.y + tag_bord.bounds.y
//        }
//    }
//
//    function start_arrows(event) {
//        var edp = event.downPoint;
//        circle.position = edp;
//        if (path.segments.length > 0) {
//            path.removeSegments(0,path.segments.length);
//        }
//        path.add(edp, edp);
//
//        var echo_edp = new paper.Point(
//            ((edp.x - tag_bord.bounds.x) / ZOOM_FACTOR) + zoom_rectangle.bounds.x,
//            ((edp.y - tag_bord.bounds.y) / ZOOM_FACTOR) + zoom_rectangle.bounds.y
//        );
//
//        echo_circle.position = echo_edp;
//        if (echo_path.segments.length > 0) {
//            echo_path.removeSegments(0, echo_path.segments.length);
//        }
//        echo_path.add(echo_edp, echo_edp);
//
//        real_edp = new paper.Point(
//            Math.round((echo_edp.x) * tag_raster.width / over_bounds.width),
//            Math.round((echo_edp.y) * tag_raster.height / over_bounds.height)
//        );
//        $('input#form_start').val('' + real_edp.x + ',' + real_edp.y)
//    }
//
//    function finish_arrows(event) {
//        var ep = event.point;
//        path.lastSegment.point = ep;
//
//        var echo_ep = new paper.Point(
//            ((ep.x - tag_bord.bounds.x) / ZOOM_FACTOR) + zoom_rectangle.bounds.x,
//            ((ep.y - tag_bord.bounds.y) / ZOOM_FACTOR) + zoom_rectangle.bounds.y
//        );
//        echo_path.lastSegment.point = echo_ep;
//
//        var real_ep = new paper.Point(
//            Math.round((echo_ep.x) * tag_raster.width / over_bounds.width),
//            Math.round((echo_ep.y) * tag_raster.height / over_bounds.height)
//        );
//
//        var delta = real_edp.subtract(real_ep);
//
//        $('input#form_end').val('' + real_ep.x + ',' + real_ep.y);
//
//        if (delta.x != 0) {
//            $('#output_angle').html(Math.atan2(delta.y, delta.x));
//        } else{
//            if (delta.y>0) {
//                $('#output_angle').html('up')
//            } else {
//                $('#output_angle').html('down')
//            }
//        }
//    }
//
//    tool.onMouseDown = function(event) {
//        if (event.downPoint.isInside(tag_bounds)) {
//            arrow.visible = true;
//            echo_arrow.visible = true;
//            start_arrows(event);
//        } else {
//            zoom_rectangle.visible = true;
//            if (event.point.isInside(over_mouse_bounds)) {
//                zoom_rectangle.position = event.point;
//                update_tag_raster(event.point);
//            }
//
//        }
//    };
//
//    tool.onMouseDrag = function(event) {
//        if (event.downPoint.isInside(tag_bounds)) {
//            if (event.point.isInside(tag_bounds)) {
//                finish_arrows(event);
//                arrow.visible = true;
//                echo_arrow.visible = true;
//            } else {
//                arrow.visible = false;
//                echo_arrow.visible = false;
//            }
//        } else {
//            zoom_rectangle.visible = true;
//            if (event.point.isInside(over_mouse_bounds)) {
//                zoom_rectangle.position = event.point;
//                update_tag_raster(event.point);
//            }
//        }
//    };
//
//    function replace_rasters(url) {
//        arrow.visible = false;
//        echo_arrow.visible = false;
//    }
//
//    build_tag_layer();
//    build_over_layer();
//    update_tag_raster();
//    view.draw();
//});
