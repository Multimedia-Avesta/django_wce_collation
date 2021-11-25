/*jshint esversion: 6 */
editorial = (function () {
    "use strict";

  var _addHandlers;

  $(document).ready(function () {
    _addHandlers();
  });


  _addHandlers = function () {
    $('.reading-text').on('click', function () {
      var inputId;
      inputId = this.getAttribute('data-inputid');
      document.getElementById(inputId).value = this.innerHTML.trim();
    });
    $('.lb-button').on('click', function (event) {
      var lineMarkerId, number, hidden;
      event.preventDefault();
      number = this.id.replace('lb_button_', '');
      if (document.getElementById('linebreak_after_' + number).value == 'false') {
        document.getElementById('linebreak_after_' + number).value = 'true';
        lineMarkerId = this.getAttribute('data-newlinemarkerid');
        $('#' + lineMarkerId).removeClass('lb-marker-hidden');
        $('#' + lineMarkerId).addClass('lb-marker-active');
        this.innerHTML = 'remove lb';
      } else {
        document.getElementById('linebreak_after_' + number).value = 'false';
        lineMarkerId = this.getAttribute('data-newlinemarkerid');
        $('#' + lineMarkerId).removeClass('lb-marker-active');
        $('#' + lineMarkerId).addClass('lb-marker-hidden');
        this.innerHTML = 'lb after';
      }
    });
    $('.type-select').on('change', function () {
      var inputId;
      inputId = this.getAttribute('data-inputid');
      if (this.value == 'translation') {
        $('#' + inputId).removeClass('commentary');
        $('#' + inputId).addClass('translation');
      } else if (this.value == 'commentary') {
        $('#' + inputId).removeClass('translation');
        $('#' + inputId).addClass('commentary');
      }
    });
    $('#show-lang-select-button').on('click', function () {
      $('.lang-select-row').toggle();
    });
    $('#show-subtype-select-button').on('click', function () {
      $('.type-select-row').toggle();
    });
  };


  return {};

} () );
