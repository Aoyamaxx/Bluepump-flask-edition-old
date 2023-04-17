$(function(){
  $("#header").load("header.html");
  $("#footer").load("footer.html");
  
  // Add event listener to Donate buttons
  $('body').on('click', '.donate', function() {
    $.get('/track_button_click/donate_button');
  });

  // Add event listener to Map button
  $('body').on('click', '.menu-item[href="map.html"]', function() {
    $.get('/track_button_click/map_button');
  });
});