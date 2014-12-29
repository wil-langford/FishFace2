/**
 * Created by wil on 12/2/14.
 */

$(document).ready(function() {

    if (window.ff == undefined) { window.ff = {}; }

    ff.HORIZONTAL_TILES = 6;
    ff.VERTICAL_TILES = 5;

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

            this.overlay = new Array(hor_tiles * vert_tiles);
            this.overlay_fill = 'rgba(200,50,50,0.5)';

            for (var i=0; i<hor_tiles*vert_tiles; i++) {
                var top_left = this.index_to_coords(i);
                this.overlay[i] = new fabric.Rect({
                    originX: 'center',
                    originY: 'center',
                    selectable: false,
                    height: this.tile_height,
                    width: this.tile_width,
                    fill: 'transparent'
                });
                this.overlay[i].set({
                    top: top_left.y,
                    left: top_left.x
                });

            }
        },
        index_to_coords: function(tile_index) {
            var idx = {
                x: tile_index % this.hor_tiles,
                y: (tile_index - (tile_index % this.hor_tiles)) / this.hor_tiles
            };

            return {
                x: this.tile_width * idx.x + (this.tile_width / 2),
                y: this.tile_height * idx.y + (this.tile_height / 2)
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

            img.set({
                originX: 'center',
                originY: 'center',
                selectable: false
            });

            wdw.add(img);
            wdw.tile[idx] = img;

            var tc = wdw.index_to_coords(idx);

            img.set({
                height: wdw.tile_height,
                width: wdw.tile_width,
                left: tc.x,
                top: tc.y
            });

            wdw.add(wdw.overlay[idx]);
            wdw.overlay[idx].bringToFront();

            wdw.renderAll();
            img.setCoords();
            wdw.calcOffset();
        },
        replace_tile: function(tag, tile_index) {
            fabric.Image.fromURL(tag.url, this.image_replaced, {
                window: this,
                tag: tag,
                tile_index: tile_index
            });
        },
        image_replaced: function(img) {
            var wdw = img.window;
            var idx = img.tile_index;

            img.set({
                originX: 'center',
                originY: 'center',
                selectable: false
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
            wdw.overlay[idx].bringToFront();
            wdw.tile[idx].setCoords();

            wdw.calcOffset();
        },
        get_verifications: function() {
            return $("input#tags_verified").attr('value').split(',');
        },
        set_verifications: function(verifications) {
            $("input#tags_verified").attr('value', verifications.join(','))
        },
        get_verification: function(idx) {
            var vers = this.get_verifications();
            return vers[idx];
        },
        set_verification: function(idx, zero_or_one) {
            var vers = this.get_verifications();
            vers[idx] = zero_or_one;
            this.set_verifications(vers);
        },
        toggle_tile: function(idx) {
            var current_state = this.get_verification(idx);
            if (ff.window.tile[idx].tag.id != 'NONE') {
                if (current_state == '0') {
                    this.set_tile(idx, 1);
                } else {
                    this.set_tile(idx, 0);
                }
            }
            this.renderAll();
        },
        set_tile: function(idx, state) {
            this.set_verification(idx, state.toString());
            if (state == 0) {
                this.overlay[idx].fill = this.overlay_fill;
            } else {
                this.overlay[idx].set({fill: 'transparent'})
            }
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
            ff.window.toggle_tile(tile_index);
        }
        ff.window.renderAll();
        ff.window.calcOffset();
    });


    ff.get_new_tags = function(do_post) {
        if (do_post == 0) {
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
                if (data.valid) {
                    $('#canvas_wrapper').css('display', 'block');
                    $('div#zero_unverified').css('display', 'none');
                    $('input#tag_ids').attr('value', data.verify_ids_text);
                    $('input#tags_verified').attr('value', data.tags_verified_text);

                    for (var tile_index in data.verify_these) {
                        ff.window.replace_tile(
                            data.verify_these[tile_index],
                            tile_index
                        );
                    }

                    for (var i = 0; i < (ff.TILES); i++) {
                        ff.window.set_tile(i, 1);
                    }

                } else {
                    if (data.reason == 'zero_unverified') {
                        $('div#zero_unverified').css('display', 'block');
                        $('#canvas_wrapper').css('display', 'none');
                    }
                }
            }
        });

        ff.window.renderAll();
    }

    $('#verification_form').on('submit', function (event) {
        event.preventDefault();
        ff.get_new_tags(1);
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

            ff.get_new_tags(0);

            ff.window.renderAll();
        }
    });

    for (var i = 0; i < (ff.TILES); i++) {
        ff.window.add_tile({
            id: 'NONE',
            url: '/static/djff/no_image.png'
        }, i);
    }

    ff.window.calcOffset();
    ff.window.renderAll();

});  // end $(document).ready()