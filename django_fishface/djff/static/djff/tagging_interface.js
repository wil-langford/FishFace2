/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {

    if (window.ff == undefined) { window.ff = {}; }

    window.ff.ARROW_CIRCLE_RADIUS = 9;
    window.ff.SCALE_FACTOR = 3;
    window.ff.ARROW_COLOR = 'lightgreen';
    window.ff.ZOOM_BORDER_COLOR = 'yellow';

    $('#change_res').click(function (event) {
        window.location.reload();
    });

    function canvas_to_real(o, t, point) {
        var orig = o.image.getOriginalSize();
        return new fabric.Point(

            Math.round((point.x / (t.width / 2) * (o.zoom_border.width/2) +
                o.zoom_border.left - o.zoom_border.width/2) *
                orig.width / o.width),

            Math.round((point.y / (t.height / 2) * (o.zoom_border.height/2) +
            o.zoom_border.top - o.zoom_border.height/2) *
                orig.height / o.height)
        );
    }

    /*
     * Fabric.js code below
     */

    fabric.FFArrow = fabric.util.createClass({
        AAAffType: 'FFArrow',
        initialize: function(canvas) {
            var center = canvas.getCenter();

            this.line = new fabric.Line([0,0,0,0], {
                originX: 'center',
                originY: 'center',
                stroke: window.ff.ARROW_COLOR,
                strokeWidth: 1,
                selectable: false,
                visible: false
            });

            this.circle = new fabric.Circle({
                left:0,
                top:0,
                originX: 'center',
                originY: 'center',
                fill: '',
                stroke: window.ff.ARROW_COLOR,
                radius: window.ff.ARROW_CIRCLE_RADIUS,
                strokeWidth: 1,
                selectable: false,
                visible: false
            });

            canvas.add(this.circle);
            canvas.add(this.line);

            this.circle.setCoords();
            this.line.setCoords();
        },

        start_arrow: function(pointer) {
            this.line.set({
                x1: pointer.x,
                y1: pointer.y,
                x2: pointer.x,
                y2: pointer.y
            });
            this.line.setCoords();

            this.circle.set({
                left: pointer.x,
                top: pointer.y
            });
            this.circle.setCoords();


            this.vis(true);
        },

        end_arrow: function(pointer) {
            this.line.set({x2: pointer.x, y2: pointer.y});

            this.line.setCoords();

            this.vis(true);
        },

        vis: function(true_false) {
            this.line.set({visible: true_false});
            this.circle.set({visible: true_false});
        }
    });

    fabric.FFPane = fabric.util.createClass(fabric.Canvas, {
        AAAffType: 'FFPane',
        initialize: function(canvas_id) {
            this.callSuper('initialize', canvas_id);

            this.defaultCursor = 'crosshair';

            this.arrow = new fabric.FFArrow(this);
        },
        add_image: function(url) {
            fabric.Image.fromURL(url, this.image_added, {
                pane: this,
                selectable: false
            });
        },
        image_added: function(img) {
            img.pane.add(img);
            img.scaleToWidth(img.pane.width);
            img.sendToBack();
            img.pane.image = img;
            img.pane.image.setCoords();
            img.pane.base_scale = img.scaleX;

            img.pane.calcOffset();
        },
        replace_image: function(url) {
            fabric.Image.fromURL(url, this.image_replaced, {
                pane: this,
                selectable: false
            });
        },
        image_replaced: function(img) {
            img.scaleToWidth(img.pane.image.width);
            img.set({
                selectable: false,
                x: img.pane.image.x,
                y: img.pane.image.y
            });
            img.scale(img.pane.base_scale);

            img.pane.image.remove();
            img.pane.image = img;
            img.pane.add(img.pane.image);
            img.pane.image.sendToBack();
            img.pane.image.setCoords();

            img.pane.calcOffset();
        }
    });

    fabric.FFOverPane = fabric.util.createClass(fabric.FFPane, {
        AAAffType: 'FFOverPane',
        initialize: function(canvas_id, zoom_border_color) {
            this.callSuper('initialize', canvas_id);

            this.zoom_update_pane = undefined;

            this.arrow.circle.radius = window.ff.ARROW_CIRCLE_RADIUS / window.ff.SCALE_FACTOR;

            this.zoom_border = new fabric.Rect({
                fill: '',
                stroke: zoom_border_color,
                strokeWidth: 1,
                height: this.height / window.ff.SCALE_FACTOR,
                width: this.width / window.ff.SCALE_FACTOR,
                originX: 'center',
                originY: 'center',
                selectable: false
            });
            this.add(this.zoom_border);
            this.zoom_border.center();
            this.zoom_border.setCoords();

            this.mouse_zone = new fabric.Rect({
                fill: '',
                height: this.height - this.zoom_border.height,
                width: this.width - this.zoom_border.width,
                selectable: false
            });
            this.add(this.mouse_zone);
            this.mouse_zone.center();
            this.mouse_zone.setCoords();
            this.mouse_zone.bringToFront();

        },
        zoom_move: function(mouse_point) {

            var point = new fabric.Point(
                Math.min(Math.max(mouse_point.x, Math.round(over.mouse_zone.left)),
                    Math.round(over.mouse_zone.left + over.mouse_zone.width)),
                Math.min(Math.max(mouse_point.y, Math.round(over.mouse_zone.top)),
                    Math.round(over.mouse_zone.top + over.mouse_zone.height))
            );

            this.zoom_border.set({
                left: point.x,
                top: point.y
            });
            this.zoom_border.setCoords();

            if (this.zoom_update_pane) {
                this.zoom_update_pane.echo_zoom_move(this);
            }

            this.renderAll();
        },
        zoom_reset: function() {
            var reset = new fabric.Point(this.zoom_border.width/2 , this.zoom_border.height/2);
            this.zoom_move(reset);
        },
        echo_point: function(canvas, pointer) {
            return {
                x: pointer.x / (canvas.width / 2) * (this.zoom_border.width/2) +
                    this.zoom_border.left - this.zoom_border.width/2,
                y: pointer.y / (canvas.height / 2) * (this.zoom_border.height/2) +
                this.zoom_border.top - this.zoom_border.height/2
            };
        },
        echo_start_arrow: function(canvas, pointer) {
            this.arrow.start_arrow(this.echo_point(canvas, pointer));
            this.renderAll();
        },
        echo_end_arrow: function(canvas, pointer) {
            this.arrow.end_arrow(this.echo_point(canvas, pointer));
            this.renderAll();
        }
    });

    fabric.FFTagPane = fabric.util.createClass(fabric.FFPane, {
        AAAffType: 'FFTagPane',
        initialize: function(canvas_id, image_scale_factor) {
            this.callSuper('initialize', canvas_id);
            this.image_scale_factor = image_scale_factor;
            this.image = undefined;
        },
        image_added: function(img) {
            img.pane.callSuper('image_added', img);

            img.pane.actual_scale_factor = img.pane.base_scale * img.pane.image_scale_factor;

            img.scale(img.pane.actual_scale_factor);
            img.setCoords();
            img.pane.calcOffset();

            img.pane.renderAll();
        },

        image_replaced: function(img) {
            img.pane.callSuper('image_replaced', img);

            img.scale(img.pane.actual_scale_factor);
            img.setCoords();
            img.pane.calcOffset();

            img.pane.renderAll();
        },


        echo_zoom_move: function(canvas) {
            if (!this.image) { return; }

            var orig_left = this.image.left;
            var orig_top = this.image.top;

            this.image.left = - (canvas.zoom_border.left - canvas.zoom_border.width/2) * window.ff.SCALE_FACTOR;
            this.image.top = - (canvas.zoom_border.top - canvas.zoom_border.height/2) * window.ff.SCALE_FACTOR;

            this.arrow.circle.left = this.arrow.circle.left + (this.image.left - orig_left);
            this.arrow.circle.top = this.arrow.circle.top + (this.image.top - orig_top);
            this.arrow.line.left = this.arrow.line.left + (this.image.left - orig_left);
            this.arrow.line.top = this.arrow.line.top + (this.image.top - orig_top);

            this.image.setCoords();
            this.arrow.line.setCoords();
            this.arrow.circle.setCoords();

            this.renderAll();
        }
    });

    var over, tagger;

    over = new fabric.FFOverPane('over_canvas', window.ff.ZOOM_BORDER_COLOR);
    window.ff.over = over;
    over.add_image("/static/djff/sample-CAL.jpg");

    tagger = new fabric.FFTagPane('tag_canvas', window.ff.SCALE_FACTOR);
    window.ff.tagger = tagger;
    tagger.add_image("/static/djff/sample-CAL.jpg", window.ff.SCALE_FACTOR);

    over.on('mouse:down', function(options) {
        window.ff.OVER_MOUSE_IS_DOWN = true;
        var pointer = over.getPointer(options.e);
        var point = new fabric.Point(pointer.x, pointer.y);
        over.zoom_move(point);
        over.renderAll();
    });

    over.on('mouse:move', function(options) {
        if (!window.ff.OVER_MOUSE_IS_DOWN) { return ; }
        var pointer = over.getPointer(options.e);
        var point = new fabric.Point(pointer.x, pointer.y);
        over.zoom_move(point);
        over.renderAll();
    });

    over.on('mouse:up', function(options) {
        window.ff.OVER_MOUSE_IS_DOWN = false;
    });

    tagger.on('mouse:down', function(options) {
        window.ff.TAGGER_MOUSE_IS_DOWN = true;
        var pointer = tagger.getPointer(options.e);
        window.ff.TAGGER_DOWN_POINT = pointer;
        tagger.arrow.start_arrow(pointer);

        echo_pointer = new fabric.Point(
            pointer.x * over.zoom_border.width / tagger.width + over.zoom_border.left,
            pointer.y * over.zoom_border.height / tagger.height + over.zoom_border.top
        );
        over.echo_start_arrow(tagger, pointer);

        tagger.renderAll();
    });

    tagger.on('mouse:move', function(options) {
        if (!window.ff.TAGGER_MOUSE_IS_DOWN) { return ; }
        var pointer = tagger.getPointer(options.e);

        if (pointer.x <= tagger.width && pointer.x >= 0 &&
            pointer.y <= tagger.height && pointer.y >= 0) {
            tagger.arrow.end_arrow(pointer);
            over.echo_end_arrow(tagger, pointer);
            tagger.arrow.vis(true);
            over.arrow.vis(true);
        } else {
            tagger.arrow.vis(false);
            over.arrow.vis(false);
        }
        over.renderAll();
        tagger.renderAll();
    });

    tagger.on('mouse:up', function(options) {
        window.ff.TAGGER_MOUSE_IS_DOWN = false;
        var pointer = tagger.getPointer(options.e);
        if (pointer.x <= tagger.width && pointer.x >= 0 &&
            pointer.y <= tagger.height && pointer.y >= 0) {
            tagger.arrow.vis(true);
            over.arrow.vis(true);


            var real_start = canvas_to_real(over, tagger, window.ff.TAGGER_DOWN_POINT);
            var real_end = canvas_to_real(over, tagger, pointer);

            $('input#form_start').val(real_start.toString());
            $('input#form_end').val(real_end.toString());

        } else {
            tagger.arrow.vis(false);
            over.arrow.vis(false);
        }

    });

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
                console.log('data validity:');
                console.log(data.valid);
                if (data.valid) {
                    $('input#image_id').attr('value', data.id);

                    over.arrow.vis(false);
                    over.replace_image(data.url);
                    tagger.arrow.vis(false);
                    tagger.replace_image(data.url);

                    $('input#form_start').val('NONE');
                    $('input#form_end').val('NONE');

                    $('span#researcher_tag_score').html(data.researcher_score);
                    $('span#researcher_bad_tags').html(data.researcher_bad_tags);

                    if (data.untagged_images_count) {
                        $('span#researcher_tags_remaining').html(data.untagged_images_count);
                    }

                    console.log("got new image: " + data.url);
                }
            },
            dataType: 'json'
        });

        over.zoom_reset();

        tagger.renderAll();
        over.renderAll();
    }

    $('form#tag_form').submit(function (event) {
        event.preventDefault();
        get_new_image(true);
    });

    $('#researcher_dropdown').change(function (event) {
        var researcher_id = $(this).val();
        if (researcher_id != 'NONE') {
            var researcher = {
                id: '0',
                name: 'RESEARCHER NOT FOUND',
                tag_score: 0
            }

            for (var i in window.ff.researchers) {
                if (window.ff.researchers[i].id == researcher_id) {
                    researcher = window.ff.researchers[i];
                }
            }

            console.log('researcher:')
            console.log(researcher);

            $('input#researcher_id').attr('value', researcher_id);

            $('#res_name').html(researcher.name);
            $('#res_name2').html(researcher.name);

            $('#researcher_selection_wrapper').css('display', 'none');
            $('#select_researcher_text').css('display', 'none');
            $('#greet_researcher').css('display', 'block');
            $('#canvas_wrapper').css('display', 'block');
            $('#tag_form_wrapper').css('display', 'block');

            $('div#researcher_score').css('display', 'block');
            $('span#researcher_tag_score').html(researcher.tag_score);

            get_new_image(false);
            over.zoom_reset();

            over.renderAll();
            tagger.renderAll();
        }
    });

    over.zoom_update_pane = tagger;
    over.zoom_reset();
    over.renderAll();
    tagger.renderAll();


});  // end $(document).ready()