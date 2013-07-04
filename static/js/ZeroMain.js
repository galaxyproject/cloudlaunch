var clip = new ZeroClipboard( document.getElementById("copy-ip"), {
  moviePath: "/static/ZeroClipboard.swf",
  hoverClass: "copy-ip-hover"
} );

clip.on( 'load', function(client) {
  // alert( "movie is loaded" );
} );

clip.on( 'complete', function(client, args) {
  // $('#copy-ip').slideUp();
  $('#copy-ip').text('Copied');
  // After several seconds, revert back to 'Copy IP'
  window.setTimeout(function(){$('#copy-ip').text('Copy IP');}, 5000);
} );

clip.on( 'mouseover', function(client) {
  //
} );

clip.on( 'mouseout', function(client) {
  // alert("mouse out");
} );

clip.on( 'mousedown', function(client) {

  // alert("mouse down");
} );

clip.on( 'mouseup', function(client) {
  // alert("mouse up");
} );
