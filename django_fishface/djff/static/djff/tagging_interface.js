/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {
    var project = new paper.Project('paper_canvas');
    var view = project.view;
    var tool = new paper.Tool();

    var bright_green = "#66FF66";
    var bright_yellow = "#FFFF66";

    var ZOOM_FACTOR = 3;
    var CIRCLE_RADIUS = 4;

    tag_bounds = {
        height: view.bounds.height / 2,
        width: view.bounds.width,
        x:0,
        y:view.center.y
    };

    over_bounds = {
        height: view.bounds.height / 2,
        width: view.bounds.width,
        x:0,
        y:0
    };

    tag_layer = project.activeLayer;

    var tag_raster = new paper.Raster('test_image');
    tag_raster.fitBounds(tag_bounds);
    tag_layer.scale(ZOOM_FACTOR, ZOOM_FACTOR, {
        x: tag_bounds.x + tag_bounds.width / 2,
        y: tag_bounds.y + tag_bounds.height / 2
    });

    over_layer = new paper.Layer();

    var over_raster = new paper.Raster('test_image');
    over_raster.position = over_bounds;
    over_raster.fitBounds(over_bounds);

    interface_layer = new paper.Layer();

    var zoom_rectangle = new paper.Path.Rectangle({
        point: [0, 0],
        size: [over_bounds.width / ZOOM_FACTOR, over_bounds.height / ZOOM_FACTOR],
        strokeColor: bright_yellow
    });

    var over_mouse_bounds = {
        height: over_bounds.height - zoom_rectangle.bounds.height,
        width: over_bounds.width - zoom_rectangle.bounds.width,
        x: over_bounds.x + zoom_rectangle.bounds.width / 2,
        y: over_bounds.y + zoom_rectangle.bounds.height / 2
    };

    var over_bord = new paper.Path.Rectangle(over_bounds);
    over_bord.strokeColor = 'black';

    var tag_bord = new paper.Path.Rectangle(tag_bounds);
    tag_bord.strokeColor = bright_yellow;

    var path = new paper.Path();
    path.strokeColor = bright_green;

    var circle = new paper.Path.Circle(new paper.Point(15, 15), CIRCLE_RADIUS);
    circle.strokeColor = bright_green;

    var arrow = new paper.Group();
    arrow.addChildren([path, circle]);
    arrow.remove();
    tag_layer.addChild(arrow);

    var echo_path = new paper.Path();
    echo_path.strokeColor = bright_green;

    var echo_circle = new paper.Path.Circle(new paper.Point(15, 15), CIRCLE_RADIUS / ZOOM_FACTOR);
    echo_circle.strokeColor = bright_green;

    var echo_arrow = new paper.Group();
    echo_arrow.addChildren([echo_path, echo_circle]);
    echo_arrow.remove();
    over_layer.addChild(echo_arrow);

    function update_tag_raster(point) {
        var zrp = zoom_rectangle.position;

        tag_layer.position = {
        x: - (zrp.x - over_bord.position.x) * ZOOM_FACTOR + over_bord.position.x,
        y: - (zrp.y - over_bord.position.y) * ZOOM_FACTOR + over_bord.position.y + tag_bord.bounds.y
        }
    };

    update_tag_raster(zoom_rectangle.center);

    function start_arrows(event) {
        var edp = event.downPoint
        circle.position = edp;
        if (path.segments.length > 0) {
            path.removeSegments(0,path.segments.length);
        }
        path.add(edp, edp);

        var echo_edp = new paper.Point(
            ((edp.x - tag_bord.bounds.x) / ZOOM_FACTOR) + zoom_rectangle.bounds.x,
            ((edp.y - tag_bord.bounds.y) / ZOOM_FACTOR) + zoom_rectangle.bounds.y
        )

        echo_circle.position = echo_edp;
        if (echo_path.segments.length > 0) {
            echo_path.removeSegments(0, echo_path.segments.length);
        }
        echo_path.add(echo_edp, echo_edp);
    }

    function finish_arrows(event) {
        var ep = event.point;
        path.lastSegment.point = ep;

        var echo_ep = new paper.Point(
            ((ep.x - tag_bord.bounds.x) / ZOOM_FACTOR) + zoom_rectangle.bounds.x,
            ((ep.y - tag_bord.bounds.y) / ZOOM_FACTOR) + zoom_rectangle.bounds.y
        )
        echo_path.lastSegment.point = echo_ep;

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

    view.draw();
});
