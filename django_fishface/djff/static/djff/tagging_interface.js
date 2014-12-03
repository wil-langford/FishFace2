/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {
    var project = new paper.Project('paper_canvas')
    var view = project.view;
    var tool = new paper.Tool();

    bright_green = "#66FF66";
    bright_yellow = "#FFFF66";

    ZOOM_FACTOR = 3;

    tag_bounds = {
        height: view.bounds.height / 2,
        width: view.bounds.width,
        x:0,
        y:view.center.y
    }

    over_bounds = {
        height: view.bounds.height / 2,
        width: view.bounds.width,
        x:0,
        y:0
    }

    var tag_raster = new paper.Raster('test_image');
    tag_raster.visible = false;
    tag_raster.scale(ZOOM_FACTOR, {
        x: tag_bounds.x + tag_bounds.width / 2,
        y: tag_bounds.y + tag_bounds.height / 2
    });

    var over_raster = new paper.Raster('test_image');
    over_raster.position = over_bounds;
    over_raster.fitBounds(over_bounds);

    var zoom_rectangle = new paper.Path.Rectangle({
        visible: false,
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

    var circle = new paper.Path.Circle(new paper.Point(15, 15), 3);
    circle.visible = false;
    circle.strokeColor = bright_green;

    function update_tag_raster(point) {
        tag_raster.x = - (zoom_rectangle.bounds.x * ZOOM_FACTOR);
        tag_raster.y = - (zoom_rectangle.bounds.y * ZOOM_FACTOR) + tag_bounds.y;
    };

    update_tag_raster(zoom_rectangle.center);

    tool.onMouseDown = function(event) {
        if (event.downPoint.isInside(tag_bounds)) {
            circle.visible = true;
            circle.position = event.point;

            if (path.segments.length > 0) {
                path.removeSegments(0,path.segments.length);
            }
            path.add(event.point, event.point);
        } else {
            zoom_rectangle.visible = true;
            if (event.point.isInside(over_mouse_bounds)) {
                zoom_rectangle.position = event.point;
                update_tag_raster(event.point);
            }

        }
    }

    tool.onMouseDrag = function(event) {
        if (event.downPoint.isInside(tag_bounds)) {
            if (event.point.isInside(tag_bounds)) {
                path.lastSegment.point = event.point;

                path.visible = true;
                circle.visible = true;
            } else {
                path.visible = false;
                circle.visible = false;
            }
        } else {
            zoom_rectangle.visible = true;
            if (event.point.isInside(over_mouse_bounds)) {
                zoom_rectangle.position = event.point;
                update_tag_raster(event.point);
            }
        }
    }

    view.draw();
});
