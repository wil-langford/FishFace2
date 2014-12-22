/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {

    if (window.ff == undefined) { window.ff = {}; }

    ff.HORIZONTAL_TILES = 2;
    ff.VERTICAL_TILES = 2 * ff.HORIZONTAL_TILES;

    ff.TILES = ff.HORIZONTAL_TILES * ff.VERTICAL_TILES;

    $('input#num_tiles').attr('value', ff.TILES);

    $('#change_res').click(function (event) {
        window.location.reload();
    });

    /*
     * Fabric.js code below
     */

    fabric.FFWindow = fabric.util.createClass(fabric.Canvas, {
        ffType: 'FFWindow',
        initialize: function(canvas_id, hor_tiles, vert_tiles) {
            this.callSuper('initialize', canvas_id);

            this.backgroundColor = 'white';

            this.tile = new Array(hor_tiles * vert_tiles);

            this.hor_tiles = hor_tiles;
            this.vert_tiles = vert_tiles;

            this.tile_width = this.width / this.hor_tiles;
            this.tile_height = this.height / this.vert_tiles;

            this.border = new Array(hor_tiles * vert_tiles);

            for (var i=0; i<hor_tiles*vert_tiles; i++) {
                var top_left = this.index_to_coords(i);
                this.border[i] = new fabric.Rect({
                    top: top_left.y,
                    left: top_left.x,
                    height: this.tile_height,
                    width: this.tile_width
                })
            }
        },
        index_to_coords: function(tile_index) {
            var idx = {
                x: tile_index % this.hor_tiles,
                y: (tile_index - (tile_index % this.hor_tiles)) / this.hor_tiles
            };

            return {
                x: this.tile_width * idx.x,
                y: this.tile_height * idx.y
            }
        },
        coords_to_index: function(point) {
            var idx = {
                x: (point.x - (point.x % this.tile_width)) / this.tile_width,
                y: (point.y - (point.y % this.tile_height)) / this.tile_height
            };

            return idx.y * this.hor_tiles + idx.x;
        },
        add_tile: function(tag, tile_index) {
            fabric.Image.fromURL(tag.url, this.image_added, {
                window: this,
                tag: tag,
                tile_index: tile_index
            });
        },
        image_added: function(img) {
            var wdw = img.window;
            var idx = img.tile_index;
            var tag = img.tag;

            wdw.add(img);
            wdw.tile[idx] = img;
            var orig = img.getOriginalSize();

            var tc = wdw.index_to_coords(idx);

            img.set({
                height: wdw.tile_height,
                width: wdw.tile_width,
                left: tc.x,
                top: tc.y,

                angle: img.tag.rotate_angle
            });

            //img.clipTo = function (ctx) {
            //    var r = wdw.border[idx];
            //    ctx.rect(r.left, r.top, r.width, r.height);
            //}

            img.rotate(img.tag.rotate_angle);

            wdw.renderAll();
            img.setCoords();
            wdw.calcOffset();
        },
        replace_tile: function(tag, tile_index) {
            console.log('replace_tile entered');
            fabric.Image.fromURL(tag.url, this.image_replaced, {
                window: this,
                tag: tag,
                tile_index: tile_index
            });
        },
        image_replaced: function(img) {
            console.log('image_replaced entered');
            console.log(img.tag);
            var wdw = img.window;
            var idx = img.tile_index;
            var tag = img.tag;

            img.set({
                angle: img.tag.rotate_angle
            });

            img.set({
                height: wdw.tile_height,
                width: wdw.tile_width,
                left: wdw.tile[idx].left,
                top: wdw.tile[idx].top
            });

            wdw.tile[idx].remove();
            wdw.tile[idx] = img;
            wdw.add(wdw.tile[idx]);

            wdw.tile[idx].sendToBack();
            wdw.tile[idx].setCoords();

            wdw.calcOffset();
        }
    });

    ff.window = new fabric.FFWindow(
        'verification_canvas',
        ff.HORIZONTAL_TILES,
        ff.VERTICAL_TILES
    );

    ff.window.on('mouse:down', function(options) {
        var pointer = ff.window.getPointer(options.e);
        var point = new fabric.Point(pointer.x, pointer.y);
        var tile_index = ff.window.coords_to_index(point);
        ff.DOWN_MOUSE_TILE_INDEX = tile_index;
    });

    ff.window.on('mouse:up', function(options) {
        var pointer = ff.window.getPointer(options.e);
        var point = new fabric.Point(pointer.x, pointer.y);
        var tile_index = ff.window.coords_to_index(point);
        if (tile_index == ff.DOWN_MOUSE_TILE_INDEX) {
            // TODO: implement the red flag toggling
            alert("Not yet implemented.")
        }
        ff.window.renderAll();
        ff.window.calcOffset();
    });


    function get_new_tags(do_post) {
        if (do_post == false) {
            $('input#tag_ids').attr('value', 'DO_NOT_POST');
            $('input#tags_verified').attr('value', 'DO_NOT_POST');
        }

        var form = $('#verification_form');
        var data = form.serialize();
        $.ajax({
            type: 'POST',
            url: ff.verification_submit_url,  // set by inline javascript on the main page
            data: data,
            dataType: 'json',
            success: function (data, status, jqXHR) {
                console.log(data)
                if (data.valid) {
                    $('input#tag_ids').attr('value', data.verify_ids_text);
                    $('input#tags_verified').attr('value', data.tags_verified_text);

                    console.log("got new tags: " + data.tag_ids_text);

                    for (var tile_index in data.verify_these) {
                        ff.window.replace_tile(
                            data.verify_these[tile_index],
                            tile_index
                        );
                    }
                }
            }
        });

        ff.window.renderAll();
    }

    $('form#tag_form').submit(function (event) {
        event.preventDefault();
        get_new_tags(true);
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
            $('#verification_form_wrapper').css('display', 'block');

            get_new_tags(false);

            ff.window.renderAll();
        }
    });

    for (var i = 0; i < (ff.TILES); i++) {
        ff.window.add_tile({
            id: 'NONE',
            url: '/static/djff/sample-CAL.jpg',
            rotate_angle: 0,
            start: '0,0',
            end: '0,0'
        }, i);
    }

    ff.window.calcOffset();
    ff.window.renderAll();

    var researcher_id = 1;
    var researcher_name = 'DEBUG_RESEARCHER_WIL';

    $('input#researcher_id').attr('value', researcher_id);

    $('#res_name').html(researcher_name);
    $('#res_name2').html(researcher_name);

    $('#researcher_selection_wrapper').css('display', 'none');
    $('#select_researcher_text').css('display', 'none');
    $('#greet_researcher').css('display', 'block');
    $('#canvas_wrapper').css('display', 'block');
    $('#verification_form_wrapper').css('display', 'block');

    get_new_tags(false);

    ff.window.calcOffset();
    ff.window.renderAll();



});  // end $(document).ready()