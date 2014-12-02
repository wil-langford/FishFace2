/**
 * Created by wil on 12/2/14.
 */

var raster = new Raster('test_image');
raster.position = view.center;
raster.scale(0.2);

var bord = new Path.Rectangle(view.bounds);
bord.strokeColor = 'black';

var path = new Path();
path.strokeColor = '#66FF66';
path.strokeWidth = 3;

function onMouseDown(event) {
    if (path.segments.length > 0) {
        path.removeSegments(0,path.segments.length);
    }
    path.add(event.point, event.point);
}

function onMouseDrag(event) {
    path.lastSegment.point = event.point;
}

