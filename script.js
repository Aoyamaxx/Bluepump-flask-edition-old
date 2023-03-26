$(document).ready(function () {
    const sliderTrack = $(".slider-track");
    const arrowLeft = $(".arrow-left");
    const arrowRight = $(".arrow-right");
    const scrollAmount = 200; // Adjust this value to control the scrolling amount
  
    function scrollSlider(direction) {
      const startPosition = sliderTrack.scrollLeft();
      const targetPosition = startPosition + scrollAmount * direction;
      const duration = 300;
  
      sliderTrack.animate({ scrollLeft: targetPosition }, duration);
    }
  
    arrowLeft.click(function () {
      scrollSlider(-1);
    });
  
    arrowRight.click(function () {
      scrollSlider(1);
    });
  });
  