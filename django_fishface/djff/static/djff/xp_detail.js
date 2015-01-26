$(document).ready(function() {

    fabric.BuilderArrow = fabric.util.createClass({
        initialize: function(canvas) {
            var center = canvas.getCenter();

            this.line = new fabric.Line([0,0,0,0], {
                originX: 'center',
                originY: 'center',
                stroke: 'black',
                strokeWidth: 1
            });

            this.circle = new fabric.Circle({
                left:0,
                top:0,
                originX: 'center',
                originY: 'center',
                fill: '',
                stroke: 'black',
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
            var x = Math.round(Math.cos(angle)*7);
            var y = -Math.round(Math.sin(angle)*7);

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
                stroke: 'black',
                strokeWidth: 1,
                height: 20,
                width: 20,
                originX: 'center',
                originY: 'center'
            });

            this.arrow = new fabric.BuilderArrow(this);
        },
        png_with_angle: function(angle) {
            this.arrow.update_arrow_with_angle(angle)
            this.renderAll();
            return this.toDataURL({
                format: 'png'
            });
        }
    });

    window.ff.builder = new fabric.BuilderPane('builder_canvas', window.ff.ZOOM_BORDER_COLOR);

    $('.angle_bullet').each(function() {
        var bullet = $(this);
        if (bullet.attr('data-angle') != 'None') {
            angle = Number(bullet.attr('data-angle'));
            bullet.html('Y <img src="data:image/png;base64," + ' +
            window.ff.builder.png_with_angle(angle)+' /> Y');
        }
    });

});  // end $(document).ready()